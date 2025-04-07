from time import sleep
from datetime import timedelta
import pandas as pd
import MetaTrader5 as mt5
from PySide6.QtCore import QThread, QObject, Signal

from utils.utils import tstamp_local_get


class Price_Feed_MT5_Worker(QObject):
    '''Price feed worker for the manager's thread.'''
    connected = False
    path = ""
    on_new_data = Signal(pd.DataFrame)
    dict_ticks = {
        "symbol": None, 
        "df_ticks": None, 
        "tstamp_start": 0,
        "tstamp_end": 0, 
        "tstamp_curr": 0,
        "tstamp_prev": 0,
        "tick_size": 0, 
        "digits": 0, 
        "lookback_hours": 1
        }
    
    def __init__(self) -> None:
        super().__init__()
        self.connected = False

    def params_update(self, path_arg, symbol_arg, lookback_hours_arg):
        self.path = path_arg
        self.dict_ticks['symbol'] = symbol_arg
        self.dict_ticks['lookback_hours'] = lookback_hours_arg

    def pf_connect(self):
        list_msg_terminal = []
        try:
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Connecting to the price feed (MT5) ...")
            self.connected = mt5.initialize(self.path)
        except Exception as e:
            list_msg_terminal.append(f"[{tstamp_local_get()}][ERROR] Error while trying to connect to the price feed (MT5)! {e}.")
        finally:
            if(self.connected is True):
                list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Connected to the price feed (MT5).")
        return(self.connected, list_msg_terminal)
    
    def pf_disconnect(self):
        list_msg_terminal = []
        try:
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Disconnecting from the price feed (MT5) ...")
            mt5.shutdown()
        except Exception as e:
            list_msg_terminal.append(f"[{tstamp_local_get()}][ERROR] Error while trying to disconnect from the price feed (MT5)! Error = {e}.")
        finally:
            list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] Disconnected from the price feed (MT5).")
            if(mt5.version() is None):
                self.connected = False
        return(self.connected, list_msg_terminal)

    def disconnect_at_exit(self):
        self.connected = False

    def symbol_get(self):
        return(self.dict_ticks['symbol'])

    def symbol_set(self, symbol):
        self.dict_ticks['symbol'] = symbol

    def list_symbols_get(self):
        list_symbols = []
        if(self.connected is True):
            tuple_symbols = mt5.symbols_get()
            for symbol in tuple_symbols:
                list_symbols.append(symbol.name)
        return(list_symbols)

    def spread_get(self):
        symbol_info = mt5.symbol_info(self.dict_ticks['symbol'])
        spread = symbol_info.spread
        return(spread)
    
    def ticks_startup_get(self):
        self.dict_ticks['tstamp_start'] = 0
        if(self.connected is True and self.dict_ticks['symbol'] is not None and self.dict_ticks['symbol'] != ""):
            symbol_info = mt5.symbol_info(self.dict_ticks['symbol'])
            self.dict_ticks['tick_size'] = symbol_info.trade_tick_size
            self.dict_ticks['digits'] = symbol_info.digits
            self.dict_ticks['tstamp_end'] = pd.to_datetime(symbol_info.time, utc = True, unit = 's')
            self.dict_ticks['tstamp_start'] = self.dict_ticks['tstamp_end'] - timedelta(hours = self.dict_ticks['lookback_hours'])
            np_tick_curr = mt5.copy_ticks_range(self.dict_ticks['symbol'], self.dict_ticks['tstamp_start'], self.dict_ticks['tstamp_end'], mt5.COPY_TICKS_ALL)
            self.dict_ticks['df_ticks'] = pd.DataFrame(np_tick_curr)
            columns_to_delete = ['bid', 'last', 'volume', 'time', 'flags', 'volume_real']
            self.dict_ticks['df_ticks'].drop(columns_to_delete, inplace = True, axis = 1)
            self.dict_ticks['df_ticks']['time'] = pd.to_datetime(self.dict_ticks['df_ticks']['time_msc'], unit = 'ms')
            self.dict_ticks['df_ticks'] = self.dict_ticks['df_ticks'].rename(columns = {'ask': 'price'})
        return(self.dict_ticks)
    
    def tick_update(self):
        while(True):
            if(self.connected is True):
                try:
                    tick_curr = mt5.symbol_info_tick(self.dict_ticks['symbol'])
                    if(tick_curr is not None):
                        self.dict_ticks['tstamp_curr'] = tick_curr.time_msc
                        if(self.dict_ticks['tstamp_curr'] is not None and self.dict_ticks['tstamp_prev'] is not None and self.dict_ticks['tstamp_curr'] > self.dict_ticks['tstamp_prev']):
                            symbol_info = mt5.symbol_info(self.dict_ticks['symbol'])
                            tick_tstamp_curr = pd.to_datetime(symbol_info.time, utc = True, unit = 's')
                            np_tick_curr = mt5.copy_ticks_from(self.dict_ticks['symbol'], tick_tstamp_curr, 1, mt5.COPY_TICKS_ALL)
                            self.dict_ticks['df_ticks'] = pd.DataFrame(np_tick_curr)
                            columns_to_delete = ['bid', 'last', 'volume', 'time', 'flags', 'volume_real']
                            self.dict_ticks['df_ticks'].drop(columns_to_delete, inplace = True, axis = 1)
                            self.dict_ticks['df_ticks']['time'] = pd.to_datetime(self.dict_ticks['df_ticks']['time_msc'], unit = 'ms')
                            self.dict_ticks['df_ticks'] = self.dict_ticks['df_ticks'].rename(columns = {'ask': 'price'})
                            self.on_new_data.emit(self.dict_ticks['df_ticks'])
                        self.dict_ticks['tstamp_prev'] = self.dict_ticks['tstamp_curr']
                except Exception as e:
                    print(f"[{tstamp_local_get()}][ERROR] Could not get price (MT5) [{self.dict_ticks['symbol']}]. Error = {e}.")
            elif(self.connected is False):
                # Delay to not overload the loop while inactive
                sleep(1)

            
class Price_Feed_MT5_Manager(QObject):
    '''Manages the worker and setup the thread for the real time updates.'''
    connected = False
    pf_worker = None
    pf_thread = None
    on_new_data = Signal(pd.DataFrame)

    def __init__(self, path_arg, symbol_arg, lookback_hours_arg) -> None:
        super().__init__()
        self.params_update(path_arg, symbol_arg, lookback_hours_arg)        

    def params_update(self, path_arg, symbol_arg, lookback_hours_arg):
        self.pf_worker = Price_Feed_MT5_Worker()
        pf_has_worker = isinstance(self.pf_worker, type(Price_Feed_MT5_Worker()))
        if(pf_has_worker is True):
            self.pf_worker.params_update(path_arg, symbol_arg, lookback_hours_arg)

    def thread_worker_setup(self):
        pf_is_thread = isinstance(self.pf_thread, type(QThread()))
        if(pf_is_thread is False):
            self.pf_thread = QThread(self)
            self.pf_worker.moveToThread(self.pf_thread)
            self.pf_thread.started.connect(self.pf_worker.tick_update)
            self.pf_worker.on_new_data.connect(self.on_new_data_transfer)

    def on_new_data_transfer(self, df_ticks: pd.DataFrame):
        self.on_new_data.emit(df_ticks)

    def pf_connect(self):
        list_msg_terminal = None
        pf_has_worker = isinstance(self.pf_worker, type(Price_Feed_MT5_Worker()))
        if(pf_has_worker is True):
            self.connected, list_msg_terminal = self.pf_worker.pf_connect()
        return(self.connected, list_msg_terminal)
    
    def pf_disconnect(self):
        list_msg_terminal = None
        pf_has_worker = isinstance(self.pf_worker, type(Price_Feed_MT5_Worker()))
        if(pf_has_worker is True):
            self.connected, list_msg_terminal = self.pf_worker.pf_disconnect()
        return(self.connected, list_msg_terminal)
    
    def thread_start(self):
        self.pf_thread.start()

    def thread_quit(self):
        self.pf_thread.isRunning = False
        self.pf_thread.quit()

    def price_feed_terminate(self):
        pf_has_worker = isinstance(self.pf_worker, type(Price_Feed_MT5_Worker()))
        if(pf_has_worker is True):
            self.pf_worker.disconnect_at_exit()
        pf_is_thread = isinstance(self.pf_thread, type(QThread()))
        if(pf_is_thread is True):
            self.thread_quit()

    def symbol_get(self):
        return(self.pf_worker.symbol_get())

    def symbol_set(self, symbol):
        self.pf_worker.symbol_set(symbol)

    def list_symbols_get(self):
        list_symbols = None
        pf_has_worker = isinstance(self.pf_worker, type(Price_Feed_MT5_Worker()))
        if(pf_has_worker is True):
            list_symbols = self.pf_worker.list_symbols_get()
        return(list_symbols)
    
    def spread_get(self):
        return(self.pf_worker.spread_get())

    def ticks_startup_get(self):
        dict_ticks = None 
        pf_has_worker = isinstance(self.pf_worker, type(Price_Feed_MT5_Worker()))
        if(pf_has_worker is True):
            dict_ticks = self.pf_worker.ticks_startup_get()
        return(dict_ticks)
