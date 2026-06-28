# comm_connection_model.py
# Data model for the single EA connection in Renko Trader V2.

import socket
import time
from dataclasses import dataclass, field


@dataclass
class cl_EA_Connection:
    """
    Represents the active EA TCP connection.
    Mirrors the reference project model for consistency.
    """
    host: str
    port: int
    socket: socket.socket
    active: bool = True
    activity_last: float = field(default_factory=time.time)
    rx_buffer: bytes = b""