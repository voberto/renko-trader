# comm_handler.py
# Per-connection handler: runs the startup state machine and dispatches DATA ticks.

import json
import time
from typing import Callable, Optional

from .comm_constants import (
    RT_POLL_INTERVAL_SECS,
    RT_MSG_TYPE_SYMBOL,
    RT_MSG_TYPE_HISTORY,
    RT_MSG_TYPE_DATA,
    RT_ACK_SYMBOL,
    RT_ACK_HISTORY,
    RT_LOG_MODULE,
)
from .comm_connection_model import cl_EA_Connection
from .comm_network_protocol import recv_messages_with_delimiter, send_raw_text


class cl_CommHandler:
    def __init__(
        self,
        connection: cl_EA_Connection,
        logger_callback: Callable[[str], None],
        on_symbol_received: Optional[Callable[[str, dict], None]] = None,
        on_history_received: Optional[Callable[[list, dict], None]] = None,
        on_tick_received: Optional[Callable[[dict], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        self._conn = connection
        self._log = logger_callback
        self._on_symbol_received = on_symbol_received
        self._on_history_received = on_history_received
        self._on_tick_received = on_tick_received
        self._on_disconnected = on_disconnected
        self._state: str = "WAIT_SYMBOL"
        self._debug_log = False

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
            self._log(f"[{RT_LOG_MODULE}] RX type='{msg_type}' | state={self._state}.")

        if self._state == "WAIT_SYMBOL":
            self._handle_symbol(msg_type, payload)
        elif self._state == "WAIT_HISTORY":
            self._handle_history(msg_type, payload)
        elif self._state == "STREAMING":
            self._handle_data(msg_type, payload)
        else:
            self._log(f"[{RT_LOG_MODULE}] Unknown state '{self._state}' — discarded.")

    def _handle_symbol(self, msg_type: str, payload: dict) -> None:
        if msg_type != RT_MSG_TYPE_SYMBOL:
            self._log(f"[{RT_LOG_MODULE}] Expected SYMBOL, got '{msg_type}' — discarded.")
            return

        symbol = payload.get("symbol", "UNKNOWN")
        self._log(f"[{RT_LOG_MODULE}] SYMBOL received: {symbol}.")

        if self._on_symbol_received:
            self._on_symbol_received(symbol, payload)

        # Send the SYMBOL ACK. RT_ACK_SYMBOL is now a JSON object string
        ok = send_raw_text(self._conn.socket, RT_ACK_SYMBOL)
        if ok:
            self._log(f"[{RT_LOG_MODULE}] ACK_SYMBOL sent ({RT_ACK_SYMBOL}) — WAIT_SYMBOL -> WAIT_HISTORY.")
            self._state = "WAIT_HISTORY"
        else:
            self._log(f"[{RT_LOG_MODULE}] ACK_SYMBOL send failed — closing.")
            self._conn.active = False

    def _handle_history(self, msg_type: str, payload: dict) -> None:
        if msg_type != RT_MSG_TYPE_HISTORY:
            self._log(f"[{RT_LOG_MODULE}] Expected HISTORY, got '{msg_type}' — discarded.")
            return

        ticks = payload.get("ticks", [])
        self._log(f"[{RT_LOG_MODULE}] HISTORY received: {len(ticks)} ticks.")

        if self._on_history_received:
            self._on_history_received(ticks, payload)

        # Send the HISTORY ACK. RT_ACK_HISTORY is now a JSON object string
        ok = send_raw_text(self._conn.socket, RT_ACK_HISTORY)
        if ok:
            self._log(f"[{RT_LOG_MODULE}] ACK_HISTORY sent ({RT_ACK_HISTORY}) — WAIT_HISTORY -> STREAMING.")
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
