# comm_constants.py
# Protocol and network constants for the Renko Trader V2 comm layer.
# NOTE: This is the V2 active version (RT_* names). It replaces the reference
# project's COMM_* version that was accidentally present here and which was
# incompatible with comm_handler.py / comm_server.py / comm_manager.py.

# Network
RT_DEFAULT_HOST: str = "127.0.0.1"
RT_DEFAULT_PORT: int = 9005
RT_DEFAULT_BUFFER_SIZE: int = 16384
RT_ACCEPT_BACKLOG: int = 1
RT_POLL_INTERVAL_SECS: float = 0.05

# Newline-delimited JSON. MUST match the EA's COMM_MSG_DELIMITER = "\n".
# (The reference project used b"\n<FRAME_END>\n", which does NOT match this EA.)
RT_FRAME_DELIMITER: bytes = b"\n"

# Startup protocol message types (must match EA_vars.mqh TX_* defines exactly)
RT_MSG_TYPE_SYMBOL: str = "TX_SYMBOL"
RT_MSG_TYPE_HISTORY: str = "TX_HISTORY"
RT_MSG_TYPE_DATA: str = "TX_DATA"

# ACK messages sent back to the EA.
# The EA's RX parser (RX_funcs.mqh) only accepts frames that are valid JSON
# objects ({...}) and extracts the "type" field. Plain-text ACKs such as
# "RX_ACK_SYMBOL" are discarded as "Malformed frame", so each ACK must be a
# JSON object whose "type" matches the EA_vars.mqh RX_ACK_* defines.
RT_ACK_SYMBOL: str = '{"type": "RX_ACK_SYMBOL"}'
RT_ACK_HISTORY: str = '{"type": "RX_ACK_HISTORY"}'

# Logging
RT_LOG_MODULE: str = "COMM"
