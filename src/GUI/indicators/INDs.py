import pandas as pd
import pandas_ta as ta


class IND_EMA():
    # Parameters
    length = 0
    # Buffers
    df_IND = None
    df_price = None
    
    def __init__(self, length):
        self.params_update(length)

    def params_update(self, length):
        self.length = length

    def IND_startup_update(self, df_startup: pd.DataFrame):
        series_IND = ta.ema(df_startup['close'], length = self.length)
        if(series_IND is not None):
            self.df_price = pd.DataFrame({'time': df_startup['time'], 'time_real': df_startup['time_real'], 'price': df_startup['close']})
            self.df_IND = pd.DataFrame({'time': df_startup['time'], 'IND': series_IND.values})
            self.df_IND.reset_index(drop = True, inplace = True)
        return(self.df_IND, self.df_price)

    def IND_CbC_update(self, time, time_real, price):
        CbC_updated = False
        list_time = self.df_price['time'].to_list() + [time]
        list_time_real = self.df_price['time_real'].to_list() + [time_real]
        list_price = self.df_price['price'].to_list() + [price]
        self.df_price = pd.DataFrame({'time': list_time, 'time_real': list_time_real, 'price': list_price})
        series_IND = ta.ema(self.df_price['price'], length = self.length)
        if(series_IND is not None):
            self.df_IND = pd.DataFrame({'time': [list_time[-1]], 'IND': [series_IND.values[-1]]})
            self.df_IND.reset_index(drop = True, inplace = True)
            CbC_updated = True
        return(CbC_updated, self.df_IND)
