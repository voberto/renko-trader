from enum import IntEnum


class Trend_State(IntEnum):
    TREND_BULLISH   = 1,
    TREND_BEARISH   = -1,
    TREND_NONE      = 0


class Signal_Type(IntEnum):
    SIGNAL_SELL = -1,
    SIGNAL_NONE = 0,
    SIGNAL_BUY = 1

