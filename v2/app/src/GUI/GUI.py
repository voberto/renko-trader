from PySide6.QtWidgets import (QDialog, QGridLayout, QLabel, QLineEdit, 
                               QPushButton, QFrame)
from PySide6.QtCore import Qt, Slot

from src.comm.comm_manager import cl_CommManager


class cl_GUI(QDialog):
    def __init__(self, config_instance, chart_instance, logger_instance):
        super().__init__()
        self.cl_config = config_instance
        self.cl_chart = chart_instance
        self.cl_logger = logger_instance
        
        self.setWindowTitle("Renko Trader V2 - Robust Connection Mode")
        self.resize(1100, 700)

        # Comm layer (injected later to avoid circular dependency during __init__)
        self._comm_manager = None

        # Main Layout
        self.layout_main = QGridLayout()
        self.setLayout(self.layout_main)

        # Setup Sections
        self._init_ui_controls()
        self._init_ui_visualization()

    def set_comm_manager(self, comm_manager: cl_CommManager):
        """
        Injects the communication manager and wires button signals.
        Called by main.py after both GUI and CommManager are instantiated.
        """
        self._comm_manager = comm_manager
        self.btn_connect.clicked.connect(self._on_btn_connect_clicked)
        self.btn_disconnect.clicked.connect(self._on_btn_disconnect_clicked)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _init_ui_controls(self):
        """
        Initializes the top control panel with Symbol/Brick info and Buttons.
        """
        self.frame_top = QFrame()
        self.frame_top.setFrameShape(QFrame.StyledPanel)
        self.layout_top = QGridLayout(self.frame_top)

        # Symbol Field (Read-only, updated by EA Protocol)
        self.lbl_symbol = QLabel("Symbol (from EA):")
        self.edt_symbol = QLineEdit("WAITING...")
        self.edt_symbol.setReadOnly(True)
        self.edt_symbol.setFixedWidth(110)
        self.edt_symbol.setAlignment(Qt.AlignCenter)
        self.edt_symbol.setStyleSheet("background-color: #f0f0f0; font-weight: bold;")

        # Brick Size Field (Read-only, from config)
        brick_size_val = str(self.cl_config.get_val("renko", "brick_size", 100))
        self.lbl_brick = QLabel("Brick Size:")
        self.edt_brick = QLineEdit(brick_size_val)
        self.edt_brick.setReadOnly(True)
        self.edt_brick.setFixedWidth(80)
        self.edt_brick.setAlignment(Qt.AlignCenter)
        self.edt_brick.setStyleSheet("background-color: #f0f0f0;")

        # Buttons
        self.btn_connect = QPushButton("CONNECT")
        self.btn_connect.setStyleSheet(
            "background-color: #2E7D32; color: white; font-weight: bold; min-width: 100px;"
        )
        
        self.btn_disconnect = QPushButton("DISCONNECT")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.setStyleSheet("min-width: 100px;")

        # Assemble Top Layout
        self.layout_top.addWidget(self.lbl_symbol, 0, 0)
        self.layout_top.addWidget(self.edt_symbol, 0, 1)
        self.layout_top.addWidget(self.lbl_brick, 0, 2)
        self.layout_top.addWidget(self.edt_brick, 0, 3)
        self.layout_top.addWidget(self.btn_connect, 0, 4)
        self.layout_top.addWidget(self.btn_disconnect, 0, 5)

        self.layout_main.addWidget(self.frame_top, 0, 0)

    def _init_ui_visualization(self):
        """
        Adds Chart and Logger to the main layout.
        """
        # Logger
        self.layout_main.addWidget(self.cl_logger, 1, 0)

        # Chart
        self.layout_main.addWidget(self.cl_chart, 2, 0)

    # ------------------------------------------------------------------
    # Slot / Callback Methods (Invoked by Comm Layer on its thread)
    # ------------------------------------------------------------------

    @Slot(str, dict)
    def on_symbol_received(self, symbol: str, payload: dict):
        """
        Callback invoked when the EA sends the SYMBOL message during startup.
        """
        self.edt_symbol.setText(symbol)
        self.cl_logger.append_log(f"[APP] Symbol confirmed: {symbol}.")

    @Slot(list, dict)
    def on_history_received(self, ticks: list, payload: dict):
        """
        Callback invoked when the EA sends the HISTORY message during startup.
        """
        self.cl_logger.append_log(f"[APP] History received: {len(ticks)} ticks.")

    @Slot(dict)
    def on_tick_received(self, payload: dict):
        """
        Callback invoked on every DATA tick received from the EA.
        Logs a concise representation to avoid flooding.
        """
        tick_time = payload.get("time", "N/A")
        open_p = payload.get("open", "N/A")
        close_p = payload.get("close", "N/A")
        self.cl_logger.append_log(f"[TICK] {tick_time} | O:{open_p} C:{close_p}")

    @Slot()
    def on_disconnected(self):
        """
        Callback invoked when the EA closes the connection or an error occurs.
        Resets UI to the waiting state.
        """
        self.cl_logger.append_log("[APP] EA disconnected.")
        self.update_ui_on_disconnect()

    # ------------------------------------------------------------------
    # Button Handlers
    # ------------------------------------------------------------------

    def _on_btn_connect_clicked(self):
        """
        Starts the TCP server and waits for the EA to connect.
        """
        if not self._comm_manager:
            self.cl_logger.append_log("[APP] CommManager not injected — cannot start.")
            return

        self.cl_logger.append_log("[APP] Starting server...")
        ok = self._comm_manager.connect()

        if ok:
            self.update_ui_on_connect()
            self.cl_logger.append_log("[APP] Server started. Waiting for EA...")
        else:
            self.cl_logger.append_log("[APP] Failed to start server (check if port is in use).")

    def _on_btn_disconnect_clicked(self):
        """
        Stops the TCP server and closes any active EA connection.
        """
        if not self._comm_manager:
            return

        self.cl_logger.append_log("[APP] Stopping server...")
        self._comm_manager.disconnect()
        self.update_ui_on_disconnect()

    # ------------------------------------------------------------------
    # UI State Helpers
    # ------------------------------------------------------------------

    def update_ui_on_connect(self):
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def update_ui_on_disconnect(self):
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.edt_symbol.setText("WAITING...")