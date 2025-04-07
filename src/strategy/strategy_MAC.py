from datetime import datetime
import pandas as pd
from utils.utils import tstamp_local_get
from strategy.strategy_utils import Trend_State, Signal_Type
from strategy.trader.trader_positions_MT5 import Position_Manager_MT5


class Strategy_MAC():
    # Parameters
    trading_period_enabled = False
    trading_period_start = 0
    trading_period_end = 0
    # Buffers
    trend_entry_curr = Trend_State.TREND_NONE
    trend_entry_prev = Trend_State.TREND_NONE
    signal_entry = Signal_Type.SIGNAL_NONE
    signal_exit = Signal_Type.SIGNAL_NONE

    def __init__(self, dict_config_arg: dict):
        self.params_update(dict_config_arg)

    def params_update(self, dict_config_arg: dict):
        self.obj_pos_manager = Position_Manager_MT5(dict_config_arg)
        self.trading_period_enabled = bool(dict_config_arg["strategy"]["filters"]["trading_period"]["enabled"])
        self.trading_period_start = pd.to_datetime(datetime.strptime(dict_config_arg["strategy"]["filters"]["trading_period"]["start"], "%H:%M:%S")).value
        self.trading_period_end = pd.to_datetime(datetime.strptime(dict_config_arg["strategy"]["filters"]["trading_period"]["end"], "%H:%M:%S")).value

    def strat_start(self, MA_001_arg, MA_002_arg):
        if(MA_001_arg > 0.0 and MA_002_arg > 0.0):
            if(MA_001_arg > MA_002_arg and self.trend_entry_curr != Trend_State.TREND_BULLISH):
                self.trend_entry_prev = self.trend_entry_curr
                self.trend_entry_curr = Trend_State.TREND_BULLISH
            elif(MA_001_arg < MA_002_arg and self.trend_entry_curr != Trend_State.TREND_BEARISH):
                self.trend_entry_prev = self.trend_entry_curr
                self.trend_entry_curr = Trend_State.TREND_BEARISH
        return(self.trend_entry_curr, self.trend_entry_prev)

    def strat_signals_CbC_update(self, time_fake_arg, time_real_arg, MA_001_arg, MA_002_arg):
        entry_updated = False
        list_msg_terminal = []
        if(MA_001_arg > 0.0 and MA_002_arg > 0.0):
            if(MA_001_arg > MA_002_arg and self.trend_entry_curr != Trend_State.TREND_BULLISH):
                self.trend_entry_prev = self.trend_entry_curr
                self.trend_entry_curr = Trend_State.TREND_BULLISH
            elif(MA_001_arg < MA_002_arg and self.trend_entry_curr != Trend_State.TREND_BEARISH):
                self.trend_entry_prev = self.trend_entry_curr
                self.trend_entry_curr = Trend_State.TREND_BEARISH
            if(self.trend_entry_prev == Trend_State.TREND_BEARISH and self.trend_entry_curr == Trend_State.TREND_BULLISH and self.signal_entry != Signal_Type.SIGNAL_BUY):
                self.signal_entry = Signal_Type.SIGNAL_BUY
                entry_updated = True
                list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] New entry signal (buy) at (fake tstamp = {datetime.strftime(time_fake_arg, "%H:%M:%S")}, " +
                                                                                                 f"real tstamp = {datetime.strftime(time_real_arg, "%H:%M:%S.%f")[:-3]}).")
            elif(self.trend_entry_prev == Trend_State.TREND_BULLISH and self.trend_entry_curr == Trend_State.TREND_BEARISH and self.signal_entry != Signal_Type.SIGNAL_SELL):
                self.signal_entry = Signal_Type.SIGNAL_SELL
                entry_updated = True
                list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] New entry signal (sell) at (fake tstamp = {datetime.strftime(time_fake_arg, "%H:%M:%S")}, " +
                                                                                                  f"real tstamp = {datetime.strftime(time_real_arg, "%H:%M:%S.%f")[:-3]}).")
        return(entry_updated, self.signal_entry, list_msg_terminal)

    def strat_entry_exit_CbC_process(self, signal_entry_arg: Signal_Type, tstamp_entry_arg):
        list_msg_terminal = []
        list_msg_terminal_pos_close = []
        str_terminal_pos_open = ""
        buy_count = self.obj_pos_manager.pos_count_buy_return()
        sell_count = self.obj_pos_manager.pos_count_sell_return()
        if(signal_entry_arg == Signal_Type.SIGNAL_BUY):
            if(buy_count == 0 and sell_count > 0):
                list_msg_terminal_pos_close = self.obj_pos_manager.pos_close_by_type(Signal_Type.SIGNAL_SELL)
            str_terminal_pos_open = self.obj_pos_manager.pos_open(Signal_Type.SIGNAL_BUY, tstamp_entry_arg)
        elif(signal_entry_arg == Signal_Type.SIGNAL_SELL):
            if(buy_count > 0 and sell_count == 0):
                list_msg_terminal_pos_close = self.obj_pos_manager.pos_close_by_type(Signal_Type.SIGNAL_BUY)
            str_terminal_pos_open = self.obj_pos_manager.pos_open(Signal_Type.SIGNAL_SELL, tstamp_entry_arg)
        if(len(list_msg_terminal_pos_close) > 0):
            list_msg_terminal += list_msg_terminal_pos_close
        if(str_terminal_pos_open is not None):
            list_msg_terminal += [str_terminal_pos_open]
        return(list_msg_terminal)

    def strat_filters_entry_auth(self, tstamp_real_arg):
        entry_auth = False
        if(self.trading_period_enabled is False):
            entry_auth = True
        elif(self.trading_period_enabled is True):
            tstamp_real_formatted = pd.to_datetime(datetime.strptime(datetime.strftime(tstamp_real_arg, "%H:%M:%S"), "%H:%M:%S")).value
            if(tstamp_real_formatted >= self.trading_period_start and tstamp_real_formatted < self.trading_period_end):
                entry_auth = True
        return(entry_auth)
    
    def strat_pos_count(self):
        pos_total = self.obj_pos_manager.pos_count_buy_return() + self.obj_pos_manager.pos_count_sell_return()
        return(pos_total)
    
    def strat_pos_close_all(self):
        list_str_terminal = []
        list_msg_terminal_pos_close_buy = self.obj_pos_manager.pos_close_by_type(Signal_Type.SIGNAL_BUY)
        list_msg_terminal_pos_close_sell = self.obj_pos_manager.pos_close_by_type(Signal_Type.SIGNAL_SELL)
        list_str_terminal += list_msg_terminal_pos_close_buy + list_msg_terminal_pos_close_sell
        return(list_str_terminal)
