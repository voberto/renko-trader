# comm_network_protocol.py
# Low-level TCP helpers for the Renko Trader V2 comm layer

import socket
from typing import List, Tuple, Optional, Any

from .comm_constants import RT_FRAME_DELIMITER, RT_DEFAULT_BUFFER_SIZE
from .comm_connection_model import cl_EA_Connection


def recv_messages_with_delimiter(connection: cl_EA_Connection, buffer_size: int = RT_DEFAULT_BUFFER_SIZE,
                                 delimiter: bytes = RT_FRAME_DELIMITER, logger: Optional[Any] = None,) -> Tuple[List[str], bool]:
    """
    Read from the socket, accumulate into rx_buffer, and extract complete frames
    split by the newline delimiter (NDJSON protocol matching the EA).

    Returns:
      - messages: list of complete message strings (UTF-8)
      - closed:   True if the connection was closed by peer or an error occurred
    """
    messages: List[str] = []

    try:
        chunk = connection.socket.recv(buffer_size)
        
        if chunk is None:
            return messages, False

        if not chunk:
            # Peer closed the connection (TCP FIN).
            return messages, True

        if not hasattr(connection, "rx_buffer") or connection.rx_buffer is None:
            connection.rx_buffer = b""

        connection.rx_buffer += chunk
        
        # Extract all complete frames currently in the buffer.
        while True:
            idx = connection.rx_buffer.find(delimiter)
            if idx == -1:
                break

            frame_bytes = connection.rx_buffer[:idx]
            connection.rx_buffer = connection.rx_buffer[idx + len(delimiter):]

            # Defensive: strip a trailing CR for cross-platform safety.
            if frame_bytes.endswith(b"\r"):
                frame_bytes = frame_bytes[:-1]

            if len(frame_bytes) == 0:
                continue

            try:
                messages.append(frame_bytes.decode("utf-8"))
            except UnicodeDecodeError:
                if logger is not None and hasattr(logger, "append_log"):
                    logger.append_log("[COMM] UTF-8 decode error — frame discarded.")
                continue

        return messages, False

    except Exception:
        return messages, True


def send_raw_text(sock: socket.socket, text: str, delimiter: bytes = RT_FRAME_DELIMITER, logger: Optional[Any] = None,) -> bool:
    """
    Send a UTF-8 encoded text message.
    Used for ACKs and any steady-state text the App sends back to the EA.
    """
    try:
        payload = text.encode("utf-8") + delimiter
        sock.sendall(payload)
        return True
    except Exception as e:
        if logger is not None and hasattr(logger, "append_log"):
            logger.append_log(f"[COMM] Send error: {type(e).__name__}: {e}.")
        return False
