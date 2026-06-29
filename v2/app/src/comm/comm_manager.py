# comm_manager.py
# Public facade for the comm layer. Used by GUI and main to start/stop
# the server and register application-level callbacks.

from typing import Callable, Optional

from .comm_server import cl_CommServer
from .comm_constants import RT_DEFAULT_HOST, RT_DEFAULT_PORT


class cl_CommManager:
    """
    Thin facade over cl_CommServer.
    Decouples the GUI/app layer from the socket implementation details.
    """

    def __init__(
        self,
        host: str,
        port: int,
        logger_callback: Callable[[str], None],
        on_start_received: Optional[Callable[[dict], None]] = None,
        on_history_received: Optional[Callable[[list, dict], None]] = None,
        on_tick_received: Optional[Callable[[dict], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ):
        self._host = host
        self._port = port
        self._log = logger_callback
        self._on_start_received = on_start_received
        self._on_history_received = on_history_received
        self._on_tick_received = on_tick_received
        self._on_disconnected = on_disconnected

        self._server = cl_CommServer(host=host, port=port, logger_callback=logger_callback, on_start_received=on_start_received, on_history_received=on_history_received,
                                     on_tick_received=on_tick_received, on_disconnected=on_disconnected,)

    def connect(self) -> bool:
        """
        Start the TCP server and begin waiting for the EA.
        Returns True if started successfully.
        """
        return self._server.start()

    def disconnect(self) -> None:
        """
        Stop the TCP server and close any active connection.
        """
        self._server.stop()

    @property
    def is_connected(self) -> bool:
        return self._server.is_running