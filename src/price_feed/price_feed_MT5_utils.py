from enum import Enum
import MetaTrader5 as mt5


class MT5_Timeframes_Val(Enum):
    TF_M1 = mt5.TIMEFRAME_M1,
    TF_M2 = mt5.TIMEFRAME_M2,
    TF_M3 = mt5.TIMEFRAME_M3,
    TF_M4 = mt5.TIMEFRAME_M4,
    TF_M5 = mt5.TIMEFRAME_M5,
    TF_M6 = mt5.TIMEFRAME_M6,
    TF_M10 = mt5.TIMEFRAME_M10,
    TF_M12 = mt5.TIMEFRAME_M12,
    TF_M15 = mt5.TIMEFRAME_M15,
    TF_M20 = mt5.TIMEFRAME_M20,
    TF_M30 = mt5.TIMEFRAME_M30,
    TF_H1 = mt5.TIMEFRAME_H1,
    TF_H2 = mt5.TIMEFRAME_H2,
    TF_H3 = mt5.TIMEFRAME_H3,
    TF_H4 = mt5.TIMEFRAME_H4,
    TF_H6 = mt5.TIMEFRAME_H6,
    TF_H8 = mt5.TIMEFRAME_H8,
    TF_H12 = mt5.TIMEFRAME_H12,
    TF_D1 = mt5.TIMEFRAME_D1,
    TF_W1 = mt5.TIMEFRAME_W1,
    TF_MN1 = mt5.TIMEFRAME_MN1,


class MT5_Timeframes_Str(Enum):
    TF_M1 = "M1",
    TF_M2 = "M2",
    TF_M3 = "M3",
    TF_M4 = "M4",
    TF_M5 = "M5",
    TF_M6 = "M6",
    TF_M10 = "M10",
    TF_M12 = "M12",
    TF_M15 = "M15",
    TF_M20 = "M20",
    TF_M30 = "M30",
    TF_H1 = "H1",
    TF_H2 = "H2",
    TF_H3 = "H3",
    TF_H4 = "H4",
    TF_H6 = "H6",
    TF_H8 = "H8",
    TF_H12 = "H12",
    TF_D1 = "D1",
    TF_W1 = "W1",
    TF_MN1 = "MN1",


dict_timeframes = { 
    mt5.TIMEFRAME_M1: 1, 
    mt5.TIMEFRAME_M2: 2, 
    mt5.TIMEFRAME_M3: 3, 
    mt5.TIMEFRAME_M4: 4, 
    mt5.TIMEFRAME_M5: 5, 
    mt5.TIMEFRAME_M6: 6, 
    mt5.TIMEFRAME_M10: 10, 
    mt5.TIMEFRAME_M12: 12, 
    mt5.TIMEFRAME_M15: 15, 
    mt5.TIMEFRAME_M20: 20, 
    mt5.TIMEFRAME_M30: 30, 
    mt5.TIMEFRAME_H1: 60, 
    mt5.TIMEFRAME_H2: 120, 
    mt5.TIMEFRAME_H3: 180, 
    mt5.TIMEFRAME_H4: 240, 
    mt5.TIMEFRAME_H6: 360, 
    mt5.TIMEFRAME_H8: 480, 
    mt5.TIMEFRAME_H12: 720,
    mt5.TIMEFRAME_D1: 1440, 
    mt5.TIMEFRAME_W1: 10080, 
    mt5.TIMEFRAME_MN1: 43200, 
}
