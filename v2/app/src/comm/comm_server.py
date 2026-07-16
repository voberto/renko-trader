# comm_server.py
# TCP server: binds, listens, and accepts a single EA connection at a time.
# Spawns a cl_CommHandler in a daemon thread for each accepted connection.

import socket
import threading
from typing import Callable, Optional

from .comm_constants import (
    RT_DEFAULT_HOST,
    RT_DEFAULT_PORT,
    RT_ACCEPT_BACKLOG,
    RT_LOG_MODULE,
)
from .comm_connection_model import cl_EA_Connection
from .comm_handler import cl_CommHandler


class cl_CommServer:
    """
    Manages the server socket lifecycle and spawns a handler thread per connection.
    Only one EA connection is expected at a time (RT_ACCEPT_BACKLOG = 1).
    """

    def __init__(
        self,
        host: str = RT_DEFAULT_HOST,
        port: int = RT_DEFAULT_PORT,
        logger_callback: Optional[Callable[[str], None]] = None,
        on_start_received: Optional[Callable] = None,
        on_history_received: Optional[Callable] = None,
        on_tick_received: Optional[Callable] = None,
        on_conn_state: Optional[Callable[[bool], None]] = None,
    ):
        self._host = host
        self._port = port
        self._log = logger_callback or (lambda msg: None)
        self._on_start_received = on_start_received
        self._on_history_received = on_history_received
        self._on_tick_received = on_tick_received
        self._on_conn_state = on_conn_state
        self.handler = None

        self._server_socket: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._handler_thread: Optional[threading.Thread] = None
        self._active_client_socket: Optional[socket.socket] = None
        self._running: bool = False
        self._ea_connected: bool = False
        self._lock = threading.Lock()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def start(self) -> bool:
        """
        Bind and start listening. Spawns the accept loop in a daemon thread.
        Returns True on success, False if already running or bind fails.
        """
        with self._lock:
            if self._running:
                self._log(f"[{RT_LOG_MODULE}] Server already running.")
                return False

            try:
                self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM,)
                self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,)
                self._server_socket.bind((self._host, self._port))
                self._server_socket.listen(RT_ACCEPT_BACKLOG)
                self._running = True
            except Exception as e:
                self._log(f"[{RT_LOG_MODULE}] Bind error on " f"{self._host}:{self._port}: {e}.")
                return False

        self._log(f"[{RT_LOG_MODULE}] Listening on " f"{self._host}:{self._port} — waiting for EA.")

        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True, name="CommServer-Accept",)
        self._accept_thread.start()
        return True

    def stop(self) -> None:
        """
        Stop the server: close the listening socket and any active EA connection.
        """
        with self._lock:
            if not self._running:
                self._log(f"[{RT_LOG_MODULE}] Server stop requested but not running.")
                return

            self._running = False
            client_socket = self._active_client_socket
            was_ea_connected = self._ea_connected
            self._active_client_socket = None
            self._ea_connected = False

        self._log(f"[{RT_LOG_MODULE}] Server stopping...")

        # Close the active EA connection first so the handler thread unblocks.
        try:
            if client_socket:
                client_socket.close()
        except Exception:
            pass

        # Close the listening socket to unblock accept().
        try:
            if self._server_socket:
                self._server_socket.close()
        except Exception:
            pass

        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2.0)

        self._log(f"[{RT_LOG_MODULE}] Server stopped.")
        self.handler = None

        if was_ea_connected and self._on_conn_state:
            self._on_conn_state(False)

    @property
    def is_running(self) -> bool:
        return self._running

    def handler_get(self):
        return(self.handler)

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------
    def _accept_loop(self) -> None:
        """
        Blocks on accept(). For each incoming connection, spawns a handler thread.
        """
        while self._running:
            try:
                client_socket, address = self._server_socket.accept()
            except socket.error:
                # Server socket was closed (stop() called).
                break

            host, port = address
            self._log(f"[{RT_LOG_MODULE}] EA connected from {host}:{port}.")

            # Store reference so stop() can close it if needed.
            with self._lock:
                self._active_client_socket = client_socket
                self._ea_connected = True

            connection = cl_EA_Connection(host=host, port=port, socket=client_socket,)

            self.handler = cl_CommHandler(connection=connection, logger_callback=self._log, on_start_received=self._on_start_received,
                                          on_history_received=self._on_history_received, on_tick_received=self._on_tick_received,
                                          on_conn_state=lambda connected: self._on_handler_conn_state(client_socket, connected),)

            if self._on_conn_state:
                self._on_conn_state(True)

            self._handler_thread = threading.Thread(target=self.handler.run, daemon=True, name=f"CommHandler-{host}:{port}",)
            self._handler_thread.start()

    def _on_handler_conn_state(self, client_socket: socket.socket, connected: bool) -> None:
        """
        Handles connection-state notifications from an EA handler.
        Ignores notifications from stale handlers after a newer connection
        has already become active.
        """
        if connected:
            return

        with self._lock:
            if self._active_client_socket is not client_socket:
                return

            self._active_client_socket = None
            self._ea_connected = False

        if self._on_conn_state:
            self._on_conn_state(False)