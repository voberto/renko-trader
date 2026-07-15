# comm_handler.py
# Per-connection handler: runs the startup state machine and dispatches DATA ticks.

import json
import time
from typing import Callable, Optional

from .comm_constants import (
    RT_POLL_INTERVAL_SECS,
    RT_MSG_TYPE_START,
    RT_MSG_TYPE_HISTORY,
    RT_MSG_TYPE_HISTORY_META,
    RT_MSG_TYPE_DATA,
    RT_ACK_START,
    RT_ACK_HISTORY,
    RT_ACK_HISTORY_BLOCK_BASE,
    RT_LOG_MODULE,
    TX_CMD_BASE,
)
from .comm_connection_model import cl_EA_Connection
from .comm_network_protocol import recv_messages_with_delimiter, send_raw_text


class cl_CommHandler:
    def __init__(
        self,
        connection: cl_EA_Connection,
        logger_callback: Callable[[str], None],
        on_start_received: Optional[Callable[[dict], None]] = None,
        on_history_received: Optional[Callable[[list, dict], None]] = None,
        on_tick_received: Optional[Callable[[dict], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        self._conn = connection
        self._log = logger_callback
        self._on_start_received = on_start_received
        self._on_history_received = on_history_received
        self._on_tick_received = on_tick_received
        self._on_disconnected = on_disconnected
        self._state: str = "WAIT_START"
        self._debug_log = False

        # Chunked history accumulator
        self._history_chunks_total: int = 0
        self._history_chunks_received: int = 0
        self._history_accumulator: list = []
        self._history_data_key: str = ""   # "ticks" or "candles"

    def run(self) -> None:
        self._log(f"[{RT_LOG_MODULE}] Handler started — state: {self._state}.")
        try:
            while self._conn.active:
                messages, closed = recv_messages_with_delimiter(self._conn, logger=self)
                if closed:
                    self._log(f"[{RT_LOG_MODULE}] Connection closed by EA.")
                    break
                if not messages:
                    time.sleep(RT_POLL_INTERVAL_SECS)
                    continue
                self._conn.activity_last = time.time()
                for raw in messages:
                    self._dispatch(raw)
        except Exception as e:
            self._log(f"[{RT_LOG_MODULE}] Handler error: {type(e).__name__}: {e}.")
        finally:
            self._cleanup()

    def _dispatch(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            self._log(f"[{RT_LOG_MODULE}] JSON parse error: {e} — raw (first 120): {raw[:120]}.")
            return

        msg_type = payload.get("type", "")
        if(self._debug_log): 
            self._log(f"[{RT_LOG_MODULE}] RX type = '{msg_type}' | state = {self._state}.")

        if self._state == "WAIT_START":
            self._handle_start(msg_type, payload)
        elif self._state == "WAIT_HISTORY":
            self._handle_history(msg_type, payload)
        elif self._state == "WAIT_HISTORY_CHUNKS":
            self._handle_history_chunk(msg_type, payload)
        elif self._state == "STREAMING":
            self._handle_data(msg_type, payload)
        else:
            self._log(f"[{RT_LOG_MODULE}] Unknown state '{self._state}' — discarded.")

    def _handle_start(self, msg_type: str, payload: dict) -> None:
        if msg_type != RT_MSG_TYPE_START:
            self._log(f"[{RT_LOG_MODULE}] Expected START, got '{msg_type}' — discarded.")
            return

        symbol = payload.get("symbol", "UNKNOWN")
        candles_type = payload.get("candles_type", 0)

        self._log(f"[{RT_LOG_MODULE}] START received: symbol = {symbol}, candles_type = {candles_type}.")

        if self._on_start_received:
            self._on_start_received(payload)

        ok = send_raw_text(self._conn.socket, RT_ACK_START)

        if ok:
            self._log(f"[{RT_LOG_MODULE}] ACK_START sent ({RT_ACK_START}) — WAIT_START -> WAIT_HISTORY.")
            self._state = "WAIT_HISTORY"
        else:
            self._log(f"[{RT_LOG_MODULE}] ACK_START send failed — closing.")
            self._conn.active = False

    def _handle_history(self, msg_type: str, payload: dict) -> None:
        # In the chunked protocol, WAIT_HISTORY state receives TX_HISTORY_META first,
        # then transitions to WAIT_HISTORY_CHUNKS for the actual data chunks.
        if msg_type != RT_MSG_TYPE_HISTORY_META:
            self._log(f"[{RT_LOG_MODULE}] Expected HISTORY_META, got '{msg_type}' — discarded.")
            return

        self._history_chunks_total = int(payload.get("chunks_total", 1))
        self._history_chunks_received = 0
        self._history_accumulator = []
        self._history_data_key = ""
        ticks_total = int(payload.get("ticks_total", 0))
        chunk_size  = int(payload.get("chunk_size", 0))

        self._log(
            f"[{RT_LOG_MODULE}] HISTORY_META received: "
            f"ticks_total = {ticks_total} | chunk_size = {chunk_size} | "
            f"chunks_total = {self._history_chunks_total}. "
            f"Transitioning to WAIT_HISTORY_CHUNKS."
        )
        self._state = "WAIT_HISTORY_CHUNKS"

    def _handle_history_chunk(self, msg_type: str, payload: dict) -> None:
        if msg_type != RT_MSG_TYPE_HISTORY:
            self._log(f"[{RT_LOG_MODULE}] Expected HISTORY chunk, got '{msg_type}' — discarded.")
            return

        seq = int(payload.get("seq", 0))

        # Detect data key on first chunk
        if not self._history_data_key:
            self._history_data_key = "ticks" if "ticks" in payload else "candles"

        chunk_data: list = payload.get(self._history_data_key, [])
        self._history_accumulator.extend(chunk_data)
        self._history_chunks_received += 1

        self._log(
            f"[{RT_LOG_MODULE}] HISTORY chunk {seq}/{self._history_chunks_total} received. "
            f"Items in chunk = {len(chunk_data)} | accumulated = {len(self._history_accumulator)}."
        )

        # ACK this block
        ack = RT_ACK_HISTORY_BLOCK_BASE % seq
        ok = send_raw_text(self._conn.socket, ack)
        if not ok:
            self._log(f"[{RT_LOG_MODULE}] ACK_HISTORY_BLOCK seq={seq} send failed — closing.")
            self._conn.active = False
            return

        # Check if all chunks received
        if seq >= self._history_chunks_total:
            self._finalise_history(payload)

    def _finalise_history(self, last_payload: dict) -> None:
        # Chunks arrived most-recent-first — reverse to restore chronological order
        self._history_accumulator.reverse()

        count = len(self._history_accumulator)
        self._log(
            f"[{RT_LOG_MODULE}] All {self._history_chunks_total} chunk(s) received. "
            f"Total items = {count}. Firing on_history_received callback."
        )

        if self._on_history_received:
            self._on_history_received(self._history_accumulator, last_payload)

        ok = send_raw_text(self._conn.socket, RT_ACK_HISTORY)
        if ok:
            self._log(f"[{RT_LOG_MODULE}] ACK_HISTORY sent — WAIT_HISTORY_CHUNKS -> STREAMING.")
            self._state = "STREAMING"
        else:
            self._log(f"[{RT_LOG_MODULE}] ACK_HISTORY send failed — closing.")
            self._conn.active = False

    def _handle_data(self, msg_type: str, payload: dict) -> None:
        if msg_type != RT_MSG_TYPE_DATA:
            self._log(f"[{RT_LOG_MODULE}] Expected DATA, got '{msg_type}' — discarded.")
            return
        if self._on_tick_received:
            self._on_tick_received(payload)

    def cmd_send(self, str_cmd_arg: str) -> None:
        dict_cmd = json.loads(TX_CMD_BASE)
        dict_cmd["value"] = str_cmd_arg
        send_raw_text(self._conn.socket, json.dumps(dict_cmd))
    
    def _cleanup(self) -> None:
        self._conn.active = False
        try:
            self._conn.socket.close()
        except Exception:
            pass
        self._log(f"[{RT_LOG_MODULE}] Handler finished — connection closed.")
        if self._on_disconnected:
            self._on_disconnected()

    def append_log(self, message: str) -> None:
        self._log(message)
