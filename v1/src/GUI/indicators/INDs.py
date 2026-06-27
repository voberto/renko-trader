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
        IND_mult = 2/(self.length + 1)
        IND_last = self.df_IND.iloc[-1]['IND']
        IND_curr = price * IND_mult + IND_last * (1 - IND_mult)
        self.df_price = pd.DataFrame({'time': [time], 'time_real': [time_real], 'price': [price]})
        if(IND_curr is not None and IND_curr > 0.0):
            self.df_IND = pd.DataFrame({'time': [time], 'IND': [IND_curr]})
            self.df_IND.reset_index(drop = True, inplace = True)
            CbC_updated = True
        return(CbC_updated, self.df_IND)
