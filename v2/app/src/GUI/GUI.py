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

import os
import pandas as pd

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
    DEFAULT_TIMEFRAME_SECONDS,
)

from .candles import cl_CandleEngine
from .candles_renko import cl_RenkoEngine
from src.indicators import build_indicator_engine
from src.strategy.strategy import cl_StrategyManager


# Absolute path to src/indicators/ — computed once at import time.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_INDICATORS_DIR = os.path.join(_BASE_DIR, "indicators")
_STRATEGY_DIR = os.path.join(_BASE_DIR, "strategy")


class cl_GUI(QDialog):
    def __init__(self, config_instance, chart_instance, logger_instance):
        super().__init__()

        self.cl_config = config_instance
        self.cl_chart = chart_instance
        self.cl_logger = logger_instance

        # Communication layer (injected after construction)
        self._comm_manager = None

        # Strategy Layer
        self._strategy_manager = cl_StrategyManager(self.cl_logger.append_log)

        # Connection state
        self._connected = False
        self._ea_connected = False
        self._startup_config = {}
        self._candle_engine = None
        self._ind_engine = None
        self._last_regular_candle = None   # tracks last seen candle for close detection

        # GUI initialization
        self._init_window()
        self._init_ui_controls()
        self._init_chart()
        self._init_logger()
        self._init_layout()

    # ----
    # Window Initialization
    # ----

    def _init_window(self):
        """
        Initializes the main window properties.
        """
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

    # ----
    # Communication
    # ----

    def set_comm_manager(self, comm_manager: cl_CommManager):
        """
        Injects the communication manager and wires button signals.
        Called by main.py after both GUI and CommManager are instantiated.
        """
        self._comm_manager = comm_manager

        self.btn_connect.clicked.connect(self._on_btn_connect_clicked)

    def _init_ui_controls(self):
        """
        Initializes the top control panel.
        """
        self.frame_top = QFrame()
        self.frame_top.setFrameShape(QFrame.StyledPanel)
        self.frame_top.setStyleSheet(STYLE_FRAME)
        self.frame_top.setFixedHeight(TOP_PANEL_HEIGHT)
        self.frame_top.setSizePolicy(QSizePolicy(TOP_FRAME_HORIZONTAL_POLICY, TOP_FRAME_VERTICAL_POLICY,))

        self.layout_top = QGridLayout(self.frame_top)
        self.layout_top.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN,)
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
        brick_size_val = str(self.cl_config.get_val("renko", "brick_size", 100,))

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
        """
        self.layout_main = QGridLayout()

        self.layout_main.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN,)

        self.layout_main.setSpacing(LAYOUT_SPACING)
        # Top controls
        self.layout_main.addWidget(self.frame_top, 0, 0)
        # Chart
        self.layout_main.addWidget(self.cl_chart.get_webview(), 1, 0)
        # Logger
        self.layout_main.addWidget(self.cl_logger, 2, 0)
        # Stretch factors
        self.layout_main.setRowStretch(0, 0)
        self.layout_main.setRowStretch(1, 8)
        self.layout_main.setRowStretch(2, 2)
        self.setLayout(self.layout_main)

    # ----
    # Slots
    # ----

    @Slot(dict)
    def on_strategy_signal(self, payload: dict):
        """
        Callback invoked when a strategy generates a signal.
        """
        sig_type = payload.get("type", "N/A")
        name = payload.get("name", "N/A")
        price = payload.get("price", 0.0)
        time = payload.get("time", "N/A")
        
        log_msg = f"[STRAT][SIGNAL] {name} | {sig_type} @ {price} | Time: {time}"
        self.cl_logger.append_log(log_msg)

        self._comm_manager.signal_process(sig_type)

    @Slot(dict)
    def on_start_received(self, payload: dict):
        """
        Callback invoked when the EA sends the TX_START message.
        Stores the startup config, updates UI fields, instantiates the candle
        engine and the indicator engine.
        """
        self._startup_config = payload
        symbol = payload.get("symbol", "N/A")
        candles_type = payload.get("candles_type", 0)
        timeframe_sec = payload.get("timeframe_sec", DEFAULT_TIMEFRAME_SECONDS)

        # Update UI fields
        self.edt_symbol.setText(symbol)
        brick = payload.get("brick_size", "N/A")
        self.edt_brick.setText(str(brick))

        # Instantiate the correct candle engine
        if candles_type == 0: # Regular
            self._candle_engine = cl_CandleEngine(timeframe_sec)
            self.cl_logger.append_log(f"[APP] Startup: {symbol} | Regular | TF: {timeframe_sec}s.")
        else: # Renko
            brick_size = payload.get("brick_size", 0)
            tick_size  = float(payload.get("tick_size", 1))
            self._candle_engine = cl_RenkoEngine(brick_size, tick_size)
            self.cl_logger.append_log(f"[APP] Startup: {symbol} | Renko | Brick: {brick_size} pts | Tick size: {tick_size}.")

        # Instantiate and load the indicator engine
        self._ind_engine = build_indicator_engine(self.cl_logger.append_log)
        self._ind_engine.discover_and_load(_INDICATORS_DIR)
        
        # Instantiate and load strategies based on active indicators
        active_inds = self._ind_engine.get_active_configs()
        self._strategy_manager.discover_and_load(_STRATEGY_DIR, active_inds)

    @Slot(list, dict)
    def on_history_received(self, candles: list, payload: dict):
        """
        Callback invoked when the EA sends the HISTORY message.
        Routes raw candle list through the candle engine, renders the result,
        then initialises indicator lines and feeds them historical data.
        """
        if self._candle_engine is None:
            self.cl_logger.append_log("[APP] No candle engine available — history discarded.")
            return

        df = self._candle_engine.process_history(candles)
        self.cl_chart.load_historical_candles(df)
        self.cl_logger.append_log(f"[APP] Chart successfully populated with {self._candle_engine.candle_count_hist_get()} historical candles.")

        # Seed last regular candle for close detection on subsequent ticks
        if not isinstance(self._candle_engine, cl_RenkoEngine) and not df.empty:
            self._last_regular_candle = df.iloc[-1].copy()

        # Indicators — skip if no indicators loaded or history is empty
        if self._ind_engine is None or self._ind_engine.is_empty() or df.empty:
            return

        # Create a line series on the chart for each registered indicator
        for name in self._ind_engine.registered_names():
            color = self._ind_engine.get_color(name)
            self.cl_chart.create_indicator_line(name, color)

        # Compute and render historical indicator values
        ind_results = self._ind_engine.process_history(df)
        for name, df_ind in ind_results.items():
            count = len(df_ind) if df_ind is not None else 0
            self.cl_chart.load_indicator_history(name, df_ind)
            self.cl_logger.append_log(f"[APP] Indicator '{name}' history loaded: {count} point(s).")

        # Strategy warmup
        self._strategy_manager.warmup_all(df, ind_results)

    @Slot(dict)
    def on_tick_received(self, payload: dict):
        """
        Callback invoked when the EA sends a market tick.
        Routes the raw tick through the candle engine, then updates the chart
        and all indicator lines.
        """
        if self._candle_engine is None:
            return

        processed_candle = self._candle_engine.process_tick(payload)

        if isinstance(self._candle_engine, cl_RenkoEngine):
            self._handle_tick_renko(processed_candle)
        else:
            self._handle_tick_regular(processed_candle)

    def _handle_tick_regular(self, series: pd.Series) -> None:
        """
        Updates the chart for every tick, but updates indicators and strategies 
        only when the regular candle closes.

        For regular candles, cl_CandleEngine.process_tick() returns the
        currently open candle on every tick. A candle is considered closed
        only when the incoming tick belongs to a new candle timestamp.
        """
        self.cl_chart.update_tick(series)

        if series is None:
            return

        prev = self._last_regular_candle
        self._last_regular_candle = series.copy()

        if self._ind_engine is None or self._ind_engine.is_empty():
            return

        # Only feed indicators and strategy when the candle time advances.
        # The previous candle is now closed.
        if prev is not None and series["time"] != prev["time"]:
            # 1. Update indicators for the closed candle
            ind_results = self._ind_engine.process_tick(prev)
            for name, ind_series in ind_results.items():
                self.cl_chart.update_indicator(name, ind_series)
            
            # 2. Run strategies on the closed candle
            signals = self._strategy_manager.execute(prev, ind_results)
            for sig in signals:
                self.on_strategy_signal(sig)

    def _handle_tick_renko(self, df_bricks: pd.DataFrame) -> None:
        """Updates the chart and indicators for one or more completed Renko bricks."""
        self.cl_chart.update_ticks(df_bricks)

        if df_bricks is None or df_bricks.empty:
            return
        if self._ind_engine is None or self._ind_engine.is_empty():
            return

        # Update indicators and run strategies for each completed brick individually
        for _, brick in df_bricks.iterrows():
            # 1. Update indicators
            ind_results = self._ind_engine.process_tick(brick)
            for name, ind_series in ind_results.items():
                self.cl_chart.update_indicator(name, ind_series)
            
            # 2. Run strategies
            signals = self._strategy_manager.execute(brick, ind_results)
            for sig in signals:
                self.on_strategy_signal(sig)

    @Slot(bool)
    def on_conn_state(self, connected: bool):
        """
        Callback invoked when the EA connection state changes.
        """
        if connected:
            self._ea_connected = True
            return
        if not self._ea_connected:
            return

        self._ea_connected = False
        self.cl_logger.append_log("[APP] EA disconnected.")
        self._reset_ea_session()

    # ----
    # Button Handler
    # ----
    def _on_btn_connect_clicked(self):
        """
        Toggles the server connection state.
        """
        if not self._comm_manager:
            self.cl_logger.append_log("[APP] CommManager not injected — cannot start.")
            return

        if not self._connected:
            self.cl_logger.append_log("[APP] Starting server...")

            ok = self._comm_manager.connect()
            if ok:
                self._set_connection_state(connected=True)
                self.cl_logger.append_log("[APP] Server started. Waiting for EA...")
            else:
                self.cl_logger.append_log("[APP] Failed to start server (check if port is in use).")
        else:
            self.cl_logger.append_log("[APP] Stopping server...")
            self._comm_manager.disconnect()
            self._set_connection_state(connected=False)

    # ----
    # UI State
    # ----
    def _set_connection_state(self, connected: bool):
        """
        Updates all connection-related UI elements to reflect the current state.
        """
        self._connected = connected

        if connected:
            self.btn_connect.setText(BUTTON_DISCONNECT_TEXT)
            self.btn_connect.setStyleSheet(STYLE_BUTTON_DISCONNECT)
        else:
            self.btn_connect.setText(BUTTON_CONNECT_TEXT)
            self.btn_connect.setStyleSheet(STYLE_BUTTON_CONNECT)
            self._ea_connected = False
            self._reset_ea_session()

            # Reset chart on disconnection
            self.cl_chart.chart_clear()
            self.cl_logger.append_log("[APP] Chart cleared on disconnection.")

            self.edt_brick.setText("") # Clear brick size field
            self._startup_config = {}
            self._candle_engine = None
            self._ind_engine = None
            self._last_regular_candle = None

    def _reset_ea_session(self):
        """
        Clears data and UI state associated with the current EA session.
        """
        self.edt_symbol.setText(SYMBOL_WAITING_TEXT)
 
        self.cl_chart.chart_clear()
        self.cl_logger.append_log("[APP] Chart cleared on disconnection.")

        self.edt_brick.setText("")
        self._startup_config = {}
        self._candle_engine = None
        self._ind_engine = None
        self._last_regular_candle = None