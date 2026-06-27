import pandas as pd
from lightweight_charts.widgets import QtChart

# Custom modules
from GUI.candles.candles_renko import Candles_Renko
from GUI.indicators.INDs import IND_EMA


class Chart_Main(QtChart):
    MA_lines_color = {'MA_001': 'rgba(39, 183, 245, 0.8)', 'MA_002': 'rgba(0, 230, 0, 0.8)'}
    MA_001_line = None
    MA_002_line = None
    df_price = None
    
    def __init__(self, widget_arg, brick_size_arg, symbol_digits_arg, MA_001_length_arg, MA_002_length_arg):
        super().__init__(widget_arg)
        self.candles_init(brick_size_arg, symbol_digits_arg)
        self.INDs_init(MA_001_length_arg, MA_002_length_arg)

    def candles_init(self, brick_size_arg, symbol_digits_arg):
        self.obj_candles = Candles_Renko(brick_size_arg, symbol_digits_arg)

    def INDs_init(self, MA_001_length_arg, MA_002_length_arg):
        self.obj_MA_001 = IND_EMA(MA_001_length_arg)
        self.obj_MA_002 = IND_EMA(MA_002_length_arg)
        self.MA_001_line = self.create_line('IND', color = self.MA_lines_color['MA_001'])
        self.MA_002_line = self.create_line('IND', color = self.MA_lines_color['MA_002'])
        
    def params_update(self, brick_size_arg, symbol_digits_arg):
        if(isinstance(self.obj_candles, Candles_Renko)):
            self.obj_candles.params_update(brick_size_arg, symbol_digits_arg)

    def chart_clear(self):
        super().set()
        self.MA_001_line.set()
        self.MA_002_line.set()

    def chart_set(self, df_renko_arg: pd.DataFrame, df_MA_001_arg: pd.DataFrame, df_MA_002_arg: pd.DataFrame):
        super().set(df_renko_arg)
        self.MA_001_line.set(df_MA_001_arg)
        self.MA_002_line.set(df_MA_002_arg)

    def chart_candles_update(self, elem_renko_arg):
        super().update(elem_renko_arg)

    def chart_INDs_update(self, elem_MA_001_arg, elem_MA_002_arg):
        self.MA_001_line.update(elem_MA_001_arg)
        self.MA_002_line.update(elem_MA_002_arg)

    def INDs_start(self, df_renko_arg: pd.DataFrame):
        if(len(df_renko_arg) > 0):
            df_MA_001, df_MA_001_price = self.obj_MA_001.IND_startup_update(df_renko_arg)
            df_MA_002, df_MA_002_price = self.obj_MA_002.IND_startup_update(df_renko_arg)
            if(df_MA_001 is not None and df_MA_002 is not None):
                self.obj_MA_001.df_IND = pd.DataFrame({'time': df_MA_001_price['time'].to_list(), 'IND': df_MA_001['IND'].to_list()})
                self.obj_MA_002.df_IND = pd.DataFrame({'time': df_MA_002_price['time'].to_list(), 'IND': df_MA_002['IND'].to_list()})
                self.obj_MA_001.df_IND.reset_index(drop = True, inplace = True)
                self.obj_MA_002.df_IND.reset_index(drop = True, inplace = True)
                
    def IND_price_CbC_update(self, time_arg, time_real_arg, price_arg):
        price_updated = False
        list_price_old = None
        if(isinstance(self.df_price, pd.DataFrame)):
            if('close' in self.df_price):
                list_price_old = self.df_price['close'].to_list()
            if('price' in self.df_price):
                list_price_old = self.df_price['price'].to_list()
            list_time = self.df_price['time'].to_list() + [time_arg]
            list_time_real = self.df_price['time_real'].to_list() + [time_real_arg]
            list_price = list_price_old + [price_arg]
            self.df_price = pd.DataFrame({'time': list_time, 'time_real': list_time_real, 'price': list_price}).tail(len(self.df_price) - 1)
            self.df_price.reset_index(drop = True, inplace = True)
            if(len(self.df_price) > 0):
                price_updated = True
        return(price_updated)
    
    def INDs_CbC_update(self, time, time_real, price):
        MAs_updated = False
        df_MA_001_CbC = None
        df_MA_002_CbC = None
        if(isinstance(self.obj_MA_001, IND_EMA) and isinstance(self.obj_MA_002, IND_EMA) and time is not None and price is not None):
            MA_001_updated, df_MA_001_CbC = self.obj_MA_001.IND_CbC_update(time, time_real, price)
            MA_002_updated, df_MA_002_CbC = self.obj_MA_002.IND_CbC_update(time, time_real, price)
            if(MA_001_updated and MA_002_updated):
                MAs_updated = True
        return(MAs_updated, df_MA_001_CbC, df_MA_002_CbC)

    def INDs_CbC_chart_setup(self, df_MA_001_CbC_arg: pd.DataFrame, df_MA_002_CbC_arg: pd.DataFrame):
        df_MA_001_CbC_chart = pd.DataFrame({'time': df_MA_001_CbC_arg['time'].to_list(), 'IND': df_MA_001_CbC_arg['IND'].to_list()})
        df_MA_002_CbC_chart = pd.DataFrame({'time': df_MA_002_CbC_arg['time'].to_list(), 'IND': df_MA_002_CbC_arg['IND'].to_list()})
        df_MA_001_CbC_chart.reset_index(drop = True, inplace = True)
        df_MA_002_CbC_chart.reset_index(drop = True, inplace = True)
        return(df_MA_001_CbC_chart, df_MA_002_CbC_chart)

    def chart_start(self, dict_ticks_arg: dict, brick_size_ticks_arg):
        chart_started = False
        time_real_curr = 0
        MA_001_curr = 0.0
        MA_002_curr = 0.0
        if(isinstance(self.obj_candles, Candles_Renko)):
            self.params_update(brick_size_ticks_arg, dict_ticks_arg['digits'])
            renko_valid, df_renko = self.obj_candles.renko_start(dict_ticks_arg['df_ticks'])
            if(renko_valid is True):
                df_renko_chart = self.obj_candles.df_renko_chart_setup(df_renko)
                self.df_price = pd.DataFrame({'time': df_renko['time'].to_list(), 'time_real': df_renko['time_real'].to_list(), 'price': df_renko['close'].to_list()})
                self.df_price.reset_index(drop = True, inplace = True)
                self.INDs_start(df_renko)
                self.chart_set(df_renko_chart, self.obj_MA_001.df_IND, self.obj_MA_002.df_IND)
                chart_started = True
                time_real_curr = df_renko['time_real'].to_list()[-1]
                MA_001_curr = self.obj_MA_001.df_IND['IND'].to_list()[-1]
                MA_002_curr = self.obj_MA_002.df_IND['IND'].to_list()[-1]
        return(chart_started, time_real_curr, MA_001_curr, MA_002_curr)

    def chart_CbC_candles_update(self, df_candles_arg: pd.DataFrame):
        if(isinstance(df_candles_arg, pd.DataFrame) and len(df_candles_arg) > 0):
            df_renko_chart = self.obj_candles.df_renko_chart_setup(df_candles_arg)
            if(isinstance(df_renko_chart, pd.DataFrame) and len(df_renko_chart) > 0):
                for index_renko, elem_renko in df_renko_chart.iterrows():
                    self.chart_candles_update(elem_renko)

    def chart_CbC_INDs_update(self, price_MAs_updated_arg, df_MA_001_CbC_arg: pd.DataFrame, df_MA_002_CbC_arg: pd.DataFrame):
        if(price_MAs_updated_arg is True and isinstance(df_MA_001_CbC_arg, pd.DataFrame) and isinstance(df_MA_002_CbC_arg, pd.DataFrame)):
            for (index_MA_001, elem_MA_001), (index_MA_002, elem_MA_002), in zip(df_MA_001_CbC_arg.iterrows(), df_MA_002_CbC_arg.iterrows()):
                self.chart_INDs_update(elem_MA_001, elem_MA_002)
