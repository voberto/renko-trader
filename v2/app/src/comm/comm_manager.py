# comm_manager.py
# Public facade for the comm layer. Used by GUI and main to start/stop
# the server and register application-level callbacks.

from typing import Callable, Optional

from .comm_server import cl_CommServer
from .comm_handler import cl_CommHandler
from shared.constants import SIG_TYPE_LONG, SIG_TYPE_SHORT, CMD_TYPE_LONG, CMD_TYPE_SHORT


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
        on_conn_state: Optional[Callable[[bool], None]] = None,
    ):
        self._host = host
        self._port = port
        self._log = logger_callback
        self._on_start_received = on_start_received
        self._on_history_received = on_history_received
        self._on_tick_received = on_tick_received
        self._on_conn_state = on_conn_state

        self._server = cl_CommServer(host=host, port=port, logger_callback=logger_callback, on_start_received=on_start_received, on_history_received=on_history_received,
                                     on_tick_received=on_tick_received, on_conn_state=on_conn_state,)

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

    def cmd_send(self, str_cmd_arg: str) -> None:
        handler_curr = self._server.handler_get()
        if(isinstance(handler_curr, cl_CommHandler)):
            handler_curr.cmd_send(str_cmd_arg)

    def signal_process(self, sig_type_arg) -> None:
        if(sig_type_arg == SIG_TYPE_LONG):
            self.cmd_send(CMD_TYPE_LONG)
        elif(sig_type_arg == SIG_TYPE_SHORT):
            self.cmd_send(CMD_TYPE_SHORT)
        else:
            self._log.append_log(f"[DEBUG][SIGNAL_PROCESS] Invalid signal type = {sig_type_arg}.")
        
    @property
    def is_connected(self) -> bool:
        return self._server.is_running
