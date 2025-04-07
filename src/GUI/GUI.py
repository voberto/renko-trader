from datetime import datetime
import pandas as pd

from PySide6.QtWidgets import QDialog, QWidget, QTextEdit, QGridLayout, QComboBox, QPushButton, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

# Custom modules
from utils.utils import tstamp_local_get
from price_feed.price_feed_MT5 import Price_Feed_MT5_Manager
from GUI.chart import Chart_Main
from strategy.strategy_MAC import Strategy_MAC
from strategy.strategy_utils import Trend_State
from GUI.logger import Logger


class Dialog_WinMain(QDialog):
    '''Main window.'''
    app_started = False
        
    def __init__(self, dict_config_arg: dict) -> None:
        super().__init__()
        # ------------------------------------------- #
        # 1 - Initialization
        # ------------------------------------------- #
        # 1.1 - GUI
        self.GUI_init(dict_config_arg)
        # 1.2 - Upper row (symbol, brick size and buttons)
        self.row_upper_init(dict_config_arg)
        # 1.3 - Chart 
        self.chart_init(dict_config_arg)
        # 1.4 - Terminal
        self.terminal_init(dict_config_arg)
        # 1.5 - Layout
        self.layout_init()
        # 1.6 - Price feed
        self.price_feed_init(dict_config_arg)
        # 1.7 - Strategy
        self.strategy_init(dict_config_arg)
        # 1.8 - Logger
        self.logger_init(dict_config_arg)
        # ------------------------------------------- #
        # 2 - Setup
        # ------------------------------------------- #
        # 2.1 - Brick size
        self.brick_size_setup()
        # 2.2 - Price feed
        self.price_feed_setup()
        # ------------------------------------------- #

    def GUI_init(self, dict_config_arg: dict):
        self.setWindowTitle(f"Renko Trader v{dict_config_arg['GUI']['version']} - Main Window")
        self.resize(dict_config_arg['GUI']['GUI_width'], dict_config_arg['GUI']['GUI_height'])
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

    def row_upper_init(self, dict_config_arg: dict):
        self.cb_symbol = QComboBox()
        self.le_brick_size = QLineEdit(parent = self)
        self.le_brick_size.setMaximumWidth(dict_config_arg['GUI']['text_field_width_max'])
        self.le_brick_size.setValidator(QDoubleValidator())
        self.brick_size = dict_config_arg['asset']['brick_size_points']
        self.brick_size_default = self.brick_size
        self.le_brick_size.setText(str(self.brick_size))
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clearFocus()
        self.btn_connect.clicked.connect(self.price_feed_toggle)
        self.btn_run = QPushButton("Run")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self.strat_toggle)

    def chart_init(self, dict_config_arg):
        self.wg_graph = QWidget()
        self.obj_chart = Chart_Main(self.wg_graph, self.brick_size, 0.0, dict_config_arg['chart']['INDs']['MA_001']['length'], dict_config_arg['chart']['INDs']['MA_002']['length'])

    def terminal_init(self, dict_config_arg: dict):
        self.tb_terminal = QTextEdit()
        self.tb_terminal.setMaximumHeight(dict_config_arg['GUI']['terminal_height'])

    def layout_init(self):
        self.column_span = 10
        self.layout_whole = QGridLayout()
        self.layout_whole.addWidget(self.cb_symbol, 1, 1, 1, 1)
        self.layout_whole.addWidget(self.le_brick_size, 1, 2, 1, 1)
        self.layout_whole.addWidget(self.btn_connect, 1, 3, 1, 1)
        self.layout_whole.addWidget(self.btn_run, 1, 4, 1, 1)
        self.layout_whole.addWidget(self.obj_chart.get_webview(), 2, 1, 1, self.column_span)
        self.layout_whole.addWidget(self.tb_terminal, 3, 1, 1, self.column_span)
        self.setLayout(self.layout_whole)
    
    def price_feed_init(self, dict_config_arg: dict):
        self.price_feed_connected = False
        self.price_feed_symbol = dict_config_arg['asset']['symbol']
        self.obj_price_feed = Price_Feed_MT5_Manager(dict_config_arg['price_feed']['MT5']['path'], self.price_feed_symbol, dict_config_arg['price_feed']['MT5']['lookback_hours'])

    def strategy_init(self, dict_config_arg: dict):
        self.obj_strat = Strategy_MAC(dict_config_arg)
        self.strat_running = False

    def logger_init(self, dict_config_arg: dict):
        self.obj_logger = Logger(dict_config_arg)
        str_terminal = f"[{tstamp_local_get()}][INFO] Opening application ..."
        self.tb_terminal.append(str_terminal)
        self.obj_logger.logfile_append(str_terminal)

    def brick_size_setup(self):
        self.le_brick_size.textChanged.connect(self.params_update)

    def price_feed_setup(self):
        self.obj_price_feed.thread_worker_setup()
        self.obj_price_feed.on_new_data.connect(self.cb_loop_OnTick)
        
    def price_feed_toggle(self):
        btn_connect_text = self.btn_connect.text()
        if('Connect' in btn_connect_text):
            self.update_on_connect()
            self.btn_connect.setText("Disconnect")
        elif('Disconnect' in btn_connect_text):
            self.update_on_disconnect()
            self.btn_run.setEnabled(False)
            self.btn_connect.setText("Connect")

    def price_feed_connect(self):
        self.price_feed_connected, list_msg_terminal = self.obj_price_feed.pf_connect()
        if(isinstance(list_msg_terminal, list) and len(list_msg_terminal) > 0):
            for index, msg in enumerate(list_msg_terminal):
                self.tb_terminal.append(msg)
                self.obj_logger.logfile_append(msg)
        return(self.price_feed_connected)

    def price_feed_disconnect(self):
        self.price_feed_connected, list_msg_terminal = self.obj_price_feed.pf_disconnect()
        if(isinstance(list_msg_terminal, list) and len(list_msg_terminal) > 0):
            for index, msg in enumerate(list_msg_terminal):
                self.tb_terminal.append(msg)
                self.obj_logger.logfile_append(msg)
        return(self.price_feed_connected)

    def trader_connect(self):
        trader_connected, list_msg_terminal = self.obj_strat.obj_pos_manager.connect()
        if(trader_connected is True):
            if(isinstance(list_msg_terminal, list) and len(list_msg_terminal) > 0):
                for msg in list_msg_terminal:
                    self.tb_terminal.append(msg)
                    self.obj_logger.logfile_append(msg)

    def trader_disconnect(self):
        trader_connected, list_msg_terminal = self.obj_strat.obj_pos_manager.disconnect()
        if(trader_connected is False):
            if(isinstance(list_msg_terminal, list) and len(list_msg_terminal) > 0):
                for msg in list_msg_terminal:
                    self.tb_terminal.append(msg)
                    self.obj_logger.logfile_append(msg)

    def symbols_update_on_connect(self, app_started_arg):
        symbols_updated = False
        if(app_started_arg is False):
            list_symbols = self.obj_price_feed.list_symbols_get()
            list_symbols_count = len(list_symbols)
            str_terminal = f"[{tstamp_local_get()}][INFO] Available symbols = {list_symbols_count}."
            self.tb_terminal.append(str_terminal)
            if(list_symbols_count > 0):
                self.cb_symbol.clear()
                for symbol in list_symbols:
                    self.cb_symbol.addItem(symbol)
                symbol_index = self.cb_symbol.findText(self.price_feed_symbol)
                if(symbol_index >= 0):
                    self.cb_symbol.setCurrentIndex(symbol_index)
                    self.cb_symbol.currentIndexChanged.connect(self.params_update)
                    symbols_updated = True
        elif(app_started_arg is True):
            symbol_index = self.cb_symbol.findText(self.price_feed_symbol)
            if(symbol_index >= 0):
                self.cb_symbol.setCurrentIndex(symbol_index)
            self.cb_symbol.currentIndexChanged.connect(self.params_update)
        return(symbols_updated)

    def update_on_connect(self):
        self.price_feed_connected = self.price_feed_connect()
        if(self.price_feed_connected is True):
            symbols_updated = self.symbols_update_on_connect(self.app_started)
            if(symbols_updated is True):
                params_updated, str_terminal = self.params_update()
                if(params_updated is True):
                    self.tb_terminal.append(str_terminal)
                    self.obj_logger.logfile_append(str_terminal)
            self.loop_OnInit()
            self.trader_connect()
            self.obj_price_feed.thread_start()
            self.btn_run.setEnabled(True)

    def update_on_disconnect(self):
        self.obj_price_feed.thread_quit()
        self.price_feed_connected = self.price_feed_disconnect()
        self.trader_disconnect()
        try:
            self.cb_symbol.currentIndexChanged.disconnect()
        except Exception:
            pass
        self.app_started = False
        self.obj_price_feed.pf_worker.connected = False
        if(isinstance(self.obj_chart, Chart_Main)):
            self.obj_chart.chart_clear()

    def symbol_update(self):
        symbol_updated = False
        cb_symbol_curr = self.cb_symbol.currentText()
        if(cb_symbol_curr != "" and cb_symbol_curr != self.obj_price_feed.symbol_get()):
            self.obj_price_feed.symbol_set(cb_symbol_curr)
            self.price_feed_symbol = cb_symbol_curr
            symbol_updated = True
        return(symbol_updated)

    def brick_size_update(self):
        brick_size_updated = False
        brick_size_curr = self.le_brick_size.text()
        if(brick_size_curr == ""):
            self.brick_size = self.brick_size_default
            self.le_brick_size.setText(str(self.brick_size))
            brick_size_updated = True
        elif(brick_size_curr != ""):
            if(float(brick_size_curr) != self.brick_size):
                self.brick_size = float(brick_size_curr)
                brick_size_updated = True
        return(brick_size_updated)

    def params_update(self):
        params_updated = False
        str_terminal = ""
        symbol_updated = self.symbol_update()
        brick_size_updated = self.brick_size_update()
        if(symbol_updated is True or brick_size_updated is True):
            params_updated = True
            if(self.app_started is True):
                self.update_on_disconnect()
                self.btn_run.setEnabled(False)
                self.btn_connect.setText("Connect")
                str_terminal = f"[{tstamp_local_get()}][INFO] Parameters updated: symbol = {self.obj_price_feed.symbol_get()}, brick size = {self.brick_size}. Price feed disconnected. Connect again to update the chart."
        return(params_updated, str_terminal)
    
    def price_feed_ticks_startup_get(self):
        ticks_updated = False
        str_terminal = f"[{tstamp_local_get()}][INFO] Updating ticks for symbol \'{self.obj_price_feed.symbol_get()}\' ..."
        self.tb_terminal.append(str_terminal)
        self.obj_logger.logfile_append(str_terminal)
        dict_ticks = self.obj_price_feed.ticks_startup_get()
        if(isinstance(dict_ticks, dict) and isinstance(dict_ticks['df_ticks'], pd.DataFrame) and len(dict_ticks['df_ticks']) > 1):
            str_terminal = f"[{tstamp_local_get()}][INFO] Ticks for symbol \'{self.obj_price_feed.symbol_get()}\' were successfully updated (start = {dict_ticks['tstamp_start']}, end = {dict_ticks['tstamp_end']})."
            self.tb_terminal.append(str_terminal)
            self.obj_logger.logfile_append(str_terminal)
            ticks_updated = True
        return(ticks_updated, dict_ticks)

    def loop_OnInit(self):
        ticks_updated, self.dict_ticks = self.price_feed_ticks_startup_get()
        if(ticks_updated):
            brick_size_ticks = self.dict_ticks['tick_size'] * self.brick_size
            self.app_started, time_real_curr, MA_001_curr, MA_002_curr = self.obj_chart.chart_start(self.dict_ticks, brick_size_ticks)
            if(self.app_started is True):
                self.obj_strat.trend_entry_curr, self.obj_strat.trend_entry_prev = self.obj_strat.strat_start(MA_001_curr, MA_002_curr)
                list_msg_terminal = self.strat_trend_startup_return(time_real_curr)
                if(isinstance(list_msg_terminal, list) and len(list_msg_terminal) > 0):
                    for msg in list_msg_terminal:
                        self.tb_terminal.append(msg)
                        self.obj_logger.logfile_append(msg)

    def cb_loop_OnTick(self, df_ticks_arg: pd.DataFrame):
        if(self.obj_price_feed.connected is True):
            list_msg_terminal = self.CbC_update(df_ticks_arg)
            if(isinstance(list_msg_terminal, list) and len(list_msg_terminal) > 0):
                for msg in list_msg_terminal:
                    self.tb_terminal.append(msg)

    def CbC_update(self, df_ticks_arg: pd.DataFrame):
        price_MAs_updated = False
        df_MA_001_CbC = None
        df_MA_002_CbC = None
        list_msg_terminal = []
        list_msg_terminal_entry_exit = []
        list_msg_terminal_adj = []
        renko_updated, df_renko_CbC, list_msg_terminal_renko = self.obj_chart.obj_candles.renko_CbC_update(df_ticks_arg)
        if(renko_updated and isinstance(df_renko_CbC, pd.DataFrame) and len(df_renko_CbC) > 0):
            if(isinstance(list_msg_terminal_renko, list) and len(list_msg_terminal_renko) > 0):
                list_msg_terminal = list_msg_terminal_renko
            for index_renko, elem_renko in df_renko_CbC.iterrows():
                price_MAs_updated = self.obj_chart.IND_price_CbC_update(elem_renko['time'], elem_renko['time_real'], elem_renko['close'])
                if(price_MAs_updated is True):
                    MAs_updated, df_MA_001_CbC, df_MA_002_CbC = self.obj_chart.INDs_CbC_update(elem_renko['time'], elem_renko['time_real'], elem_renko['close'])
                    if(MAs_updated is True and isinstance(df_MA_001_CbC, pd.DataFrame) and isinstance(df_MA_002_CbC, pd.DataFrame)):
                        time_fake_curr = elem_renko['time']
                        time_real_curr = elem_renko['time_real']
                        MA_001_curr = df_MA_001_CbC['IND'].to_list()[-1]
                        MA_002_curr = df_MA_002_CbC['IND'].to_list()[-1]
                        entry_updated, signal_entry, list_msg_terminal_strat = self.obj_strat.strat_signals_CbC_update(time_fake_curr, time_real_curr, MA_001_curr, MA_002_curr)
                        if(isinstance(list_msg_terminal_strat, list) and len(list_msg_terminal_strat) > 0):
                            list_msg_terminal += list_msg_terminal_strat
                            if(isinstance(list_msg_terminal_strat, list) and len(list_msg_terminal_strat) > 0):
                                for msg in list_msg_terminal_strat:
                                    self.obj_logger.logfile_append(msg)
                        entry_auth = self.obj_strat.strat_filters_entry_auth(time_real_curr)
                        if(entry_auth is True):
                            if(self.strat_running is True):
                                if(entry_updated is True):
                                    list_msg_terminal_entry_exit = self.obj_strat.strat_entry_exit_CbC_process(signal_entry, time_real_curr)
                            if(isinstance(list_msg_terminal_entry_exit, list) and len(list_msg_terminal_entry_exit) > 0):
                                list_msg_terminal += list_msg_terminal_entry_exit
                                for msg in list_msg_terminal_entry_exit:
                                    self.obj_logger.logfile_append(msg)
                            if(isinstance(list_msg_terminal_adj, list) and len(list_msg_terminal_adj) > 0):
                                list_msg_terminal += list_msg_terminal_adj
                                for msg in list_msg_terminal_adj:
                                    self.obj_logger.logfile_append(msg)
                        elif(entry_auth is False):
                            if(self.obj_strat.strat_pos_count() > 0):
                                list_msg_terminal_pos_close_all = self.obj_strat.strat_pos_close_all()
                                if(isinstance(list_msg_terminal_pos_close_all, list) and len(list_msg_terminal_pos_close_all) > 0):
                                    list_msg_terminal += list_msg_terminal_pos_close_all
                                    for msg in list_msg_terminal_pos_close_all:
                                        self.obj_logger.logfile_append(msg)
            self.obj_chart.chart_CbC_candles_update(df_renko_CbC)
            self.obj_chart.chart_CbC_INDs_update(price_MAs_updated, df_MA_001_CbC, df_MA_002_CbC)
        return(list_msg_terminal)

    def strat_trend_startup_return(self, time_real_arg):
        list_msg_terminal = []
        if(self.obj_strat.trend_entry_curr == Trend_State.TREND_BULLISH):
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Bullish trend (entry) at {datetime.strftime(time_real_arg, "%H:%M:%S.%f")[:-3]}.")
        elif(self.obj_strat.trend_entry_curr == Trend_State.TREND_BEARISH):
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Bearish trend (entry) at {datetime.strftime(time_real_arg, "%H:%M:%S.%f")[:-3]}.")
        return(list_msg_terminal)

    def strat_toggle(self):
        btn_run_text_curr = self.btn_run.text()
        if(btn_run_text_curr == "Run" and self.strat_running is False):
            str_terminal = f"[{tstamp_local_get()}][INFO] Starting trading strategy ..."
            self.tb_terminal.append(str_terminal)
            self.btn_run.setText("Stop")
            self.strat_running = True
            self.obj_logger.logfile_append(str_terminal)
        elif(btn_run_text_curr == "Stop" and self.strat_running is True):
            str_terminal = f"[{tstamp_local_get()}][INFO] Stopping trading strategy ..."
            self.tb_terminal.append(str_terminal)
            self.btn_run.setText("Run")
            self.strat_running = False
            self.obj_logger.logfile_append(str_terminal)

    def closeEvent(self, event):
        self.obj_price_feed.price_feed_terminate()
        str_terminal = f"[{tstamp_local_get()}][INFO] Closing application ..."
        self.obj_logger.logfile_append(str_terminal)
        super(Dialog_WinMain, self).closeEvent(event)
