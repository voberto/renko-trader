# signal_bridge.py
# Thread-safe signal bridge for cross-thread communication between
# the socket handler thread and the PySide6 main thread.
# All UI updates must go through this bridge.

from PySide6.QtCore import QObject, Signal


class cl_SignalBridge(QObject):
    """
    Lives in the main thread. Sockets emit these signals from worker threads;
    Qt's queued connection automatically marshals execution to the main thread.
    """
    sig_start_received = Signal(dict)
    sig_history_received = Signal(list, dict)
    sig_tick_received = Signal(dict)
    sig_conn_state = Signal(bool)
    sig_log_message = Signal(str)
    sig_strategy_signal = Signal(dict)
