# candles.py
# Engine for building conventional OHLC candles from historical data and real-time ticks.

import pandas as pd
from typing import Optional


class cl_CandleEngine:
    def __init__(self, timeframe_sec: int):
        self.timeframe_sec: int = timeframe_sec
        self._current_candle: Optional[dict] = None  # Internal OHLC state (time as pd.Timestamp)

    # -------------------------------------------------------------------------
    # Public — History
    # -------------------------------------------------------------------------
    def process_history(self, candles: list) -> pd.DataFrame:
        """
        Receives the raw candle list from MQL5 (TX_HISTORY payload).
        Formats, sorts, and deduplicates into a DataFrame ready for chart.set().
        Also seeds the internal current candle with the last bar.
        Returns an empty DataFrame if the input is empty.
        """
        if not candles:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close"])

        df = pd.DataFrame(candles)

        if "time" not in df.columns and "tstamp" in df.columns:
            df["time"] = df["tstamp"]

        df["time"] = pd.to_datetime(df["time"], unit="s")

        df_out = pd.DataFrame({
            "time":  df["time"].to_list(),
            "open":  df["open"].astype(float),
            "high":  df["high"].astype(float),
            "low":   df["low"].astype(float),
            "close": df["close"].astype(float),
        })

        df_out = df_out.sort_values(by="time", ascending=True)
        df_out = df_out.drop_duplicates(subset=["time"], keep="last")
        df_out.reset_index(drop=True, inplace=True)

        # Seed the current candle state from the last historical bar
        # Time stored as Unix int to guarantee unambiguous comparison in process_tick
        last = df_out.iloc[-1]
        self._current_candle = {
            "time":  int(last["time"].value) // 10**9,
            "open":  float(last["open"]),
            "high":  float(last["high"]),
            "low":   float(last["low"]),
            "close": float(last["close"]),
        }

        return df_out

    # -------------------------------------------------------------------------
    # Public — Real-time tick
    # -------------------------------------------------------------------------
    def process_tick(self, tick: dict) -> Optional[pd.Series]:
        """
        Receives a raw tick dict from the EA (TX_DATA payload).
        Updates the internal OHLC state and returns a pd.Series ready for chart.update().
        Returns None if the tick payload is invalid.
        """
        tstamp = tick.get("tstamp", tick.get("time"))
        price  = tick.get("bid", tick.get("ask", tick.get("price")))

        if tstamp is None or price is None:
            return None

        tstamp = int(tstamp)
        price  = float(price)

        # Align to timeframe boundary — compare as Unix int, unambiguous
        candle_time = (tstamp // self.timeframe_sec) * self.timeframe_sec

        if self._current_candle is not None and candle_time == self._current_candle["time"]:
            # Update existing candle — preserve open and existing wicks
            self._current_candle["high"]  = max(self._current_candle["high"], price)
            self._current_candle["low"]   = min(self._current_candle["low"],  price)
            self._current_candle["close"] = price
        else:
            # Open a new candle
            self._current_candle = {
                "time":  candle_time,
                "open":  price,
                "high":  price,
                "low":   price,
                "close": price,
            }

        # Convert time to pd.Timestamp only at the output boundary
        return pd.Series({
            "time":  pd.to_datetime(self._current_candle["time"], unit="s"),
            "open":  self._current_candle["open"],
            "high":  self._current_candle["high"],
            "low":   self._current_candle["low"],
            "close": self._current_candle["close"],
        })