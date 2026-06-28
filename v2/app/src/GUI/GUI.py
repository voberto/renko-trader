from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Slot

from src.comm.comm_manager import cl_CommManager

from src.GUI.ui_constants import (
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    LABEL_SYMBOL,
    LABEL_BRICK_SIZE,
    SYMBOL_WAITING_TEXT,
    BUTTON_CONNECT_TEXT,
    BUTTON_DISCONNECT_TEXT,
    SYMBOL_FIELD_WIDTH,
    BRICK_FIELD_WIDTH,
    TOP_PANEL_HEIGHT,
    LAYOUT_MARGIN,
    LAYOUT_SPACING,
    TOP_FRAME_HORIZONTAL_POLICY,
    TOP_FRAME_VERTICAL_POLICY,
    STYLE_FRAME,
    STYLE_LABEL,
    STYLE_LINE_EDIT,
    STYLE_BUTTON_CONNECT,
    STYLE_BUTTON_DISCONNECT,
)


class cl_GUI(QDialog):
    def __init__(self, config_instance, chart_instance, logger_instance):
        super().__init__()

        self.cl_config = config_instance
        self.cl_chart = chart_instance
        self.cl_logger = logger_instance

        # Communication layer (injected after construction)
        self._comm_manager = None

        # Connection state
        self._connected = False

        # GUI initialization
        self._init_window()
        self._init_ui_controls()
        self._init_chart()
        self._init_logger()
        self._init_layout()

    # -------------------------------------------------------------------------
    # Window Initialization
    # -------------------------------------------------------------------------

    def _init_window(self):
        """
        Initializes the main window properties.
        """
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

    # -------------------------------------------------------------------------
    # Communication
    # -------------------------------------------------------------------------

    def set_comm_manager(self, comm_manager: cl_CommManager):
        """
        Injects the communication manager and wires button signals.
        Called by main.py after both GUI and CommManager are instantiated.
        """
        self._comm_manager = comm_manager

        self.btn_connect.clicked.connect(self._on_btn_connect_clicked)

    # -------------------------------------------------------------------------
    # UI Initialization
    # -------------------------------------------------------------------------

    def _init_window(self):
        """
        Initializes the main window properties.
        """
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

    def _init_ui_controls(self):
        """
        Initializes the top control panel.
        """
        self.frame_top = QFrame()
        self.frame_top.setFrameShape(QFrame.StyledPanel)
        self.frame_top.setStyleSheet(STYLE_FRAME)
        self.frame_top.setFixedHeight(TOP_PANEL_HEIGHT)
        self.frame_top.setSizePolicy(
            QSizePolicy(
                TOP_FRAME_HORIZONTAL_POLICY,
                TOP_FRAME_VERTICAL_POLICY,
            )
        )

        self.layout_top = QGridLayout(self.frame_top)
        self.layout_top.setContentsMargins(
            LAYOUT_MARGIN,
            LAYOUT_MARGIN,
            LAYOUT_MARGIN,
            LAYOUT_MARGIN,
        )
        self.layout_top.setHorizontalSpacing(LAYOUT_SPACING)
        self.layout_top.setVerticalSpacing(LAYOUT_SPACING)

        # Symbol
        self.lbl_symbol = QLabel(LABEL_SYMBOL)
        self.lbl_symbol.setStyleSheet(STYLE_LABEL)

        self.edt_symbol = QLineEdit(SYMBOL_WAITING_TEXT)
        self.edt_symbol.setReadOnly(True)
        self.edt_symbol.setFixedWidth(SYMBOL_FIELD_WIDTH)
        self.edt_symbol.setAlignment(Qt.AlignCenter)
        self.edt_symbol.setStyleSheet(STYLE_LINE_EDIT)

        # Brick size
        brick_size_val = str(
            self.cl_config.get_val(
                "renko",
                "brick_size",
                100,
            )
        )

        self.lbl_brick = QLabel(LABEL_BRICK_SIZE)
        self.lbl_brick.setStyleSheet(STYLE_LABEL)

        self.edt_brick = QLineEdit(brick_size_val)
        self.edt_brick.setReadOnly(True)
        self.edt_brick.setFixedWidth(BRICK_FIELD_WIDTH)
        self.edt_brick.setAlignment(Qt.AlignCenter)
        self.edt_brick.setStyleSheet(STYLE_LINE_EDIT)

        # Connect/Disconnect toggle button
        self.btn_connect = QPushButton(BUTTON_CONNECT_TEXT)
        self.btn_connect.setStyleSheet(STYLE_BUTTON_CONNECT)

        # Layout assembly
        self.layout_top.addWidget(self.lbl_symbol, 0, 0)
        self.layout_top.addWidget(self.edt_symbol, 0, 1)
        self.layout_top.addWidget(self.lbl_brick,  0, 2)
        self.layout_top.addWidget(self.edt_brick,  0, 3)
        self.layout_top.addWidget(self.btn_connect, 0, 4)

    def _init_chart(self):
        """
        Initializes the chart section.
        """
        pass

    def _init_logger(self):
        """
        Initializes the logger section.
        """
        pass

    def _init_layout(self):
        """
        Builds the main window layout.

        Layout hierarchy:

            +-----------------------------------------+
            | Controls                                |
            +-----------------------------------------+
            | Chart                                   |
            +-----------------------------------------+
            | Logger                                  |
            +-----------------------------------------+
        """
        self.layout_main = QGridLayout()

        self.layout_main.setContentsMargins(
            LAYOUT_MARGIN,
            LAYOUT_MARGIN,
            LAYOUT_MARGIN,
            LAYOUT_MARGIN,
        )

        self.layout_main.setSpacing(LAYOUT_SPACING)

        # Top controls
        self.layout_main.addWidget(self.frame_top, 0, 0)

        # Chart
        self.layout_main.addWidget(self.cl_chart, 1, 0)

        # Logger
        self.layout_main.addWidget(self.cl_logger, 2, 0)

        #
        # Stretch factors.
        # The control panel keeps a fixed height.
        # The chart receives most of the available space.
        # The logger grows only slightly.
        #
        self.layout_main.setRowStretch(0, 0)
        self.layout_main.setRowStretch(1, 8)
        self.layout_main.setRowStretch(2, 2)

        self.setLayout(self.layout_main)

    # -------------------------------------------------------------------------
    # Slots
    # -------------------------------------------------------------------------

    @Slot(str, dict)
    def on_symbol_received(self, symbol: str, payload: dict):
        """
        Callback invoked when the EA sends the SYMBOL message.
        """
        self.edt_symbol.setText(symbol)
        self.cl_logger.append_log(f"[APP] Symbol confirmed: {symbol}.")

    @Slot(list, dict)
    def on_history_received(self, ticks: list, payload: dict):
        """
        Callback invoked when the EA sends the HISTORY message.
        """
        self.cl_logger.append_log(f"[APP] History received: {len(ticks)} ticks.")

    @Slot(dict)
    def on_tick_received(self, payload: dict):
        """
        Callback invoked when the EA sends a market tick.
        """
        tick_ask = payload.get("ask", "N/A")
        tick_bid = payload.get("bid", "N/A")

        self.cl_logger.append_log(
            f"[TICK] Ask: {tick_ask} | bid: {tick_bid}"
        )

    @Slot()
    def on_disconnected(self):
        """
        Callback invoked when the EA disconnects.
        """
        self.cl_logger.append_log("[APP] EA disconnected.")
        self._set_connection_state(connected=False)

    # -------------------------------------------------------------------------
    # Button Handler
    # -------------------------------------------------------------------------

    def _on_btn_connect_clicked(self):
        """
        Toggles the server connection state.

        When disconnected: starts the TCP server and waits for the EA.
        When connected:    stops the TCP server and closes any active connection.
        """
        if not self._comm_manager:
            self.cl_logger.append_log(
                "[APP] CommManager not injected — cannot start."
            )
            return

        if not self._connected:
            self.cl_logger.append_log("[APP] Starting server...")

            ok = self._comm_manager.connect()

            if ok:
                self._set_connection_state(connected=True)
                self.cl_logger.append_log(
                    "[APP] Server started. Waiting for EA..."
                )
            else:
                self.cl_logger.append_log(
                    "[APP] Failed to start server (check if port is in use)."
                )
        else:
            self.cl_logger.append_log("[APP] Stopping server...")

            self._comm_manager.disconnect()

            self._set_connection_state(connected=False)

    # -------------------------------------------------------------------------
    # UI State
    # -------------------------------------------------------------------------

    def _set_connection_state(self, connected: bool):
        """
        Updates all connection-related UI elements to reflect the current state.

        When connected:
            - Button label becomes DISCONNECT with a red background.

        When disconnected:
            - Button label becomes CONNECT with a green background.
            - Symbol field resets to the waiting placeholder.
        """
        self._connected = connected

        if connected:
            self.btn_connect.setText(BUTTON_DISCONNECT_TEXT)
            self.btn_connect.setStyleSheet(STYLE_BUTTON_DISCONNECT)
        else:
            self.btn_connect.setText(BUTTON_CONNECT_TEXT)
            self.btn_connect.setStyleSheet(STYLE_BUTTON_CONNECT)
            self.edt_symbol.setText(SYMBOL_WAITING_TEXT)