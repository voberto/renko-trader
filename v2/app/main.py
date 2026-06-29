import sys
from PySide6.QtWidgets import QApplication

from src.config.config import cl_Config
from src.GUI.GUI import cl_GUI
from src.GUI.logger import cl_Logger
from src.GUI.chart import cl_Chart
from src.GUI.signal_bridge import cl_SignalBridge
from src.comm.comm_manager import cl_CommManager


def main():
    app = QApplication(sys.argv)

    # 1. Create UI components
    log_widget = cl_Logger()
    config = cl_Config(logger_callback = log_widget.append_log)
    chart = cl_Chart()

    # 2. Initialize GUI
    window = cl_GUI(config, chart, log_widget)

    # 3. Create Signal Bridge (must be parented to main thread objects)
    bridge = cl_SignalBridge()

    # 4. Connect bridge signals to GUI slots (main thread execution guaranteed)
    bridge.sig_start_received.connect(window.on_start_received)
    bridge.sig_history_received.connect(window.on_history_received)
    bridge.sig_tick_received.connect(window.on_tick_received)
    bridge.sig_disconnected.connect(window.on_disconnected)
    bridge.sig_log_message.connect(log_widget.append_log)

    # 5. Create CommManager with callbacks that only EMIT signals
    # It is safe to emit Qt signals from any thread.
    host = config.get_val("network", "host", "127.0.0.1")
    port = config.get_val("network", "port", 9005)

    comm_manager = cl_CommManager(host = host, port = port,
                                  logger_callback = lambda msg: bridge.sig_log_message.emit(msg),
                                  on_start_received = lambda payload: bridge.sig_start_received.emit(payload),
                                  on_history_received = lambda ticks, payload: bridge.sig_history_received.emit(ticks, payload),
                                  on_tick_received = lambda payload: bridge.sig_tick_received.emit(payload),
                                  on_disconnected = lambda: bridge.sig_disconnected.emit(),)

    # 6. Inject CommManager into GUI and wire buttons
    window.set_comm_manager(comm_manager)

    # 7. Show
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
