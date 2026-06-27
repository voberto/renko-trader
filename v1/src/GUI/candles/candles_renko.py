from datetime import datetime, timedelta
import pandas as pd
from utils.utils import tstamp_local_get


class Candles_Renko():
    df_renko_start = None
    dict_renko_CbC = {'time': 0, 'time_real': 0, 'open': 0.0, 'high': 0.0, 'low': 0.0, 'close': 0.0, 'candle_size': 0.0, 'df_renko': None}
    
    def __init__(self, brick_size_arg, symbol_digits_arg) -> None:
        self.params_update(brick_size_arg, symbol_digits_arg)

    def params_update(self, brick_size_arg, symbol_digits_arg):
        self.brick_size_ticks = brick_size_arg * symbol_digits_arg
        self.symbol_digits = symbol_digits_arg

    def renko_start(self, df_ticks_arg: pd.DataFrame):
        renko_valid = False
        len_df_ticks = len(df_ticks_arg)
        if(df_ticks_arg is not None and len_df_ticks > 1):
            tick_curr = {'time': 0, 'open': 0.0, 'high': 0.0, 'low': 0.0, 'close': 0.0}
            tick_list = {'index': [], 'tstamp_fake': [], 'tstamp_real': [], 'open': [], 'high': [], 'low': [], 'close': []}
            for index, elem in df_ticks_arg.iterrows():
                tstamp = elem['time']
                price = elem['price']
                if(index == 0):
                    tick_curr['time'] = tstamp
                    tick_curr['open'] = price
                    tick_curr['high'] = price
                    tick_curr['low'] = price
                    tick_curr['close'] = price
                elif(index > 0):
                    tick_curr['close'] = price
                    if(price > tick_curr['high']):
                        tick_curr['high'] = price
                    if(price < tick_curr['low']):
                        tick_curr['low'] = price
                    candle_size_curr = abs(tick_curr['close'] - tick_curr['open'])
                    while(candle_size_curr >= self.brick_size_ticks):
                        if(tick_curr['open'] < tick_curr['close']):
                            tick_curr['close'] = tick_curr['open'] + self.brick_size_ticks
                        elif(tick_curr['open'] > tick_curr['close']):
                            tick_curr['close'] = tick_curr['open'] - self.brick_size_ticks
                        candle_size_curr = abs(tick_curr['close'] - tick_curr['open'])
                        if(tick_curr['close'] != tick_curr['open']):
                            tick_list['tstamp_real'].append(tick_curr['time'])
                            tick_list['open'].append(tick_curr['open'])
                            tick_list['high'].append(max(tick_curr['open'], tick_curr['close']))
                            tick_list['low'].append(min(tick_curr['open'], tick_curr['close']))
                            tick_list['close'].append(tick_curr['close'])
                            tick_curr['time'] = tstamp
                            tick_curr['open'] = tick_curr['close']
                            tick_curr['high'] = price
                            tick_curr['low'] = price
            len_tick_list = len(tick_list['open'])
            if(len_tick_list > 0):
                tick_list['index'] = list(range(0, len_tick_list, 1))
                # Create fake timestamp list for plotting purposes
                base = datetime(1970, 1, 1)
                tick_list['tstamp_fake'] = [base + timedelta(minutes = x) for x in range(len_tick_list)]
                list_open_formatted = [round(x, self.symbol_digits) for x in tick_list['open']]
                list_high_formatted = [round(x, self.symbol_digits) for x in tick_list['high']]
                list_low_formatted = [round(x, self.symbol_digits) for x in tick_list['low']]
                list_close_formatted = [round(x, self.symbol_digits) for x in tick_list['close']]
                self.df_renko_start = pd.DataFrame({'time': tick_list['tstamp_fake'], 'time_real': tick_list['tstamp_real'], 
                                                    'open': list_open_formatted, 'high': list_high_formatted, 'low': list_low_formatted, 'close': list_close_formatted})
                # Update CbC buffers
                self.dict_renko_CbC['time'] = tick_list['tstamp_fake'][-1]
                self.dict_renko_CbC['time_real'] = tick_list['tstamp_real'][-1]
                self.dict_renko_CbC['open'] = list_close_formatted[-1]
                renko_valid = True
        return(renko_valid, self.df_renko_start)
    
    def renko_CbC_update(self, df_ticks: pd.DataFrame):
        renko_updated = False
        list_msg_terminal = []
        if(len(df_ticks) > 0):
            price = df_ticks.iloc[0]['price']
            tstamp = df_ticks.iloc[0]['time']
            if(tstamp > self.dict_renko_CbC['time_real']):
                self.dict_renko_CbC['close'] = price
                if(self.dict_renko_CbC['open'] == 0.0):
                    self.dict_renko_CbC['open'] = price
                if(self.dict_renko_CbC['high'] == 0.0 or price > self.dict_renko_CbC['high']):
                    self.dict_renko_CbC['high'] = price
                if(self.dict_renko_CbC['low'] == 0.0 or price < self.dict_renko_CbC['low']):
                    self.dict_renko_CbC['low'] = price
                self.dict_renko_CbC['candle_size'] = abs(self.dict_renko_CbC['close'] - self.dict_renko_CbC['open'])
                list_time = []
                list_time_real = []
                list_open = []
                list_high = []
                list_low = []
                list_close = []
                while(self.dict_renko_CbC['candle_size'] >= self.brick_size_ticks):
                    self.dict_renko_CbC['time'] += timedelta(minutes = 1)
                    str_tstamp_fake = datetime.strftime(self.dict_renko_CbC['time'], "%H:%M:%S")
                    str_tstamp_real = datetime.strftime(tstamp, "%H:%M:%S.%f")[:-3]
                    if(self.dict_renko_CbC['open'] < self.dict_renko_CbC['close']):
                        self.dict_renko_CbC['close'] = self.dict_renko_CbC['open'] + self.brick_size_ticks
                        list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] New bullish renko candle at {str_tstamp_real} (fake tstamp = {str_tstamp_fake}).")
                    elif(self.dict_renko_CbC['open'] > self.dict_renko_CbC['close']):
                        self.dict_renko_CbC['close'] = self.dict_renko_CbC['open'] - self.brick_size_ticks
                        list_msg_terminal.append(f"[{tstamp_local_get()}][INFO] New bearish renko candle at {str_tstamp_real} (fake tstamp = {str_tstamp_fake}).")
                    list_time.append(self.dict_renko_CbC['time'])
                    list_time_real.append(tstamp)
                    list_open.append(self.dict_renko_CbC['open'])
                    list_high.append(max(self.dict_renko_CbC['open'], self.dict_renko_CbC['close']))
                    list_low.append(min(self.dict_renko_CbC['open'], self.dict_renko_CbC['close']))
                    list_close.append(self.dict_renko_CbC['close'])
                    self.dict_renko_CbC['open'] = self.dict_renko_CbC['close']
                    self.dict_renko_CbC['high'] = price
                    self.dict_renko_CbC['low'] = price
                    self.dict_renko_CbC['close'] = price
                    self.dict_renko_CbC['candle_size'] = abs(self.dict_renko_CbC['close'] - self.dict_renko_CbC['open'])
                if(len(list_open) > 0):
                    list_open_formatted = [round(x, self.symbol_digits) for x in list_open]
                    list_high_formatted = [round(x, self.symbol_digits) for x in list_high]
                    list_low_formatted = [round(x, self.symbol_digits) for x in list_low]
                    list_close_formatted = [round(x, self.symbol_digits) for x in list_close]
                    self.dict_renko_CbC['df_renko'] = pd.DataFrame({'time': list_time, 'time_real': list_time_real, 'open': list_open_formatted, 'high': list_high_formatted, 'low': list_low_formatted, 'close': list_close_formatted})
                    renko_updated = True
        return(renko_updated, self.dict_renko_CbC['df_renko'], list_msg_terminal)

    def df_renko_chart_setup(self, df_renko_arg: pd.DataFrame):
        df_renko_chart = pd.DataFrame({'time': df_renko_arg['time'].to_list(), 'open': df_renko_arg['open'].to_list(), 'high': df_renko_arg['high'].to_list(), 
                                       'low': df_renko_arg['low'].to_list(), 'close': df_renko_arg['close'].to_list()})
        return(df_renko_chart)
