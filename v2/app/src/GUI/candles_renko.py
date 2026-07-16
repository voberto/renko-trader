# candles_renko.py
# Engine for building Renko candles from historical ticks and real-time ticks.

import math
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


_FAKE_TS_BASE: datetime  = datetime(1970, 1, 1)
_FAKE_TS_STEP: timedelta = timedelta(minutes=1)


class cl_RenkoEngine:
    def __init__(self, brick_size: int, tick_size: float):
        """
        brick_size : brick size in points (integer), as received in TX_START.
        tick_size  : symbol tick size in price units (float), as received in TX_START.
        brick_size_pts = brick_size * tick_size  (e.g. 1000 * 0.00001 = 0.01)
        """
        self._brick_size_pts: float = int(brick_size) * float(tick_size)
        self._digits: int           = max(0, round(-math.log10(float(tick_size))))

        # Fake timestamp counter — monotonically incremented for every emitted brick
        self._fake_ts_counter: int = 0
        self._candle_count_hist: int = 0

        # CbC (candle-by-candle) state buffer — seeded by process_history,
        # updated on every process_tick call
        self._cbc_open:        float = 0.0
        self._cbc_high:        float = 0.0
        self._cbc_low:         float = 0.0
        self._cbc_close:       float = 0.0
        self._cbc_tstamp_real: int   = 0    # last real tick timestamp processed, in milliseconds

    def candle_count_hist_get(self):
        return(self._candle_count_hist)

    # ----
    # Internal helpers
    # ----
    def _next_fake_ts(self) -> datetime:
        """Returns the next sequential fake timestamp and advances the counter."""
        ts = _FAKE_TS_BASE + _FAKE_TS_STEP * self._fake_ts_counter
        self._fake_ts_counter += 1
        return ts

    # ----
    # Public — History
    # ----
    def process_history(self, ticks: list) -> pd.DataFrame:
        """
        Receives the raw tick list from the EA (TX_HISTORY payload, Renko mode).
        Each element must be a dict with keys 'time' (Unix int) and 'price' (float).
        Builds the initial Renko brick series, assigns fake timestamps, and seeds
        the CbC state buffer from the last completed brick.
        Returns an empty DataFrame if the input is empty or no bricks are formed.
        """
        empty = pd.DataFrame(columns=["time", "time_real", "open", "high", "low", "close"])

        if not ticks or len(ticks) < 2:
            return empty

        # Reset fake timestamp counter so history always starts at base
        self._fake_ts_counter = 0

        curr = {"time": 0, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0}

        out_time_real: list = []
        out_open:      list = []
        out_high:      list = []
        out_low:       list = []
        out_close:     list = []

        for i, elem in enumerate(ticks):
            tstamp = int(elem["time"])
            price = float(elem["price"])

            # Historical ticks currently provide timestamps in seconds only.
            tstamp_msc = tstamp * 1000

            if i == 0:
                curr["time"]  = tstamp
                curr["open"]  = price
                curr["high"]  = price
                curr["low"]   = price
                curr["close"] = price
            else:
                curr["close"] = price
                if price > curr["high"]:
                    curr["high"] = price
                if price < curr["low"]:
                    curr["low"] = price

                candle_size = abs(curr["close"] - curr["open"])

                # While loop emits at most one brick per tick (history mode).
                # After emitting: open = close, close is not reset.
                # Next iteration: open == close → neither branch fires → candle_size = 0 → exits.
                while candle_size >= self._brick_size_pts:
                    if curr["open"] < curr["close"]:
                        curr["close"] = curr["open"] + self._brick_size_pts
                    elif curr["open"] > curr["close"]:
                        curr["close"] = curr["open"] - self._brick_size_pts
                    candle_size = abs(curr["close"] - curr["open"])

                    if curr["close"] != curr["open"]:
                        out_time_real.append(tstamp_msc)
                        out_open.append(curr["open"])
                        out_high.append(max(curr["open"], curr["close"]))
                        out_low.append(min(curr["open"], curr["close"]))
                        out_close.append(curr["close"])
                        curr["time"]  = tstamp
                        curr["open"]  = curr["close"]
                        curr["high"]  = price
                        curr["low"]   = price
                        # curr["close"] is intentionally NOT reset here —
                        # it equals new open, causing candle_size = 0 next iteration.

        if not out_open:
            return empty

        # Build fake timestamp list — one sequential entry per brick
        out_time_fake = [_FAKE_TS_BASE + _FAKE_TS_STEP * i for i in range(len(out_open))]
        # Advance counter to continue from here in steady state
        self._fake_ts_counter = len(out_open)
        self._candle_count_hist = self._fake_ts_counter

        df = pd.DataFrame({
            "time":      out_time_fake,
            "time_real": pd.to_datetime(out_time_real, unit="ms"),
            "open":      [round(x, self._digits) for x in out_open],
            "high":      [round(x, self._digits) for x in out_high],
            "low":       [round(x, self._digits) for x in out_low],
            "close":     [round(x, self._digits) for x in out_close],
        })

        # Seed CbC buffer: next brick opens where the last one closed
        self._cbc_open        = float(df.iloc[-1]["close"])
        self._cbc_high        = 0.0
        self._cbc_low         = 0.0
        self._cbc_close       = 0.0
        self._cbc_tstamp_real = out_time_real[-1]

        return df

    # ----
    # Public — Real-time tick
    # ----
    def process_tick(self, tick: dict) -> Optional[pd.DataFrame]:
        """
        Receives a raw tick dict from the EA (TX_DATA payload).
        Updates the CbC state buffer and returns a DataFrame of new completed bricks,
        or None if the tick did not complete any brick.
        Unlike history mode, a single tick can emit multiple bricks (gap scenario).
        """
        tstamp     = tick.get("tstamp", tick.get("time"))
        tstamp_msc = tick.get("tstamp_msc")
        price      = tick.get("bid", tick.get("ask", tick.get("price")))

        if tstamp is None or price is None:
            return None

        tstamp = int(tstamp)
        price  = float(price)

        # tstamp_msc is expected from the EA for real tick precision.
        # For compatibility with an EA that has not yet been updated, derive
        # the millisecond value explicitly from the seconds-based timestamp.
        if tstamp_msc is None:
            tstamp_msc = tstamp * 1000
        else:
            tstamp_msc = int(tstamp_msc)

        # Discard out-of-order ticks
        if tstamp_msc <= self._cbc_tstamp_real:
            return None

        self._cbc_tstamp_real = tstamp_msc
        self._cbc_close = price

        if self._cbc_open == 0.0:
            self._cbc_open = price
        if self._cbc_high == 0.0 or price > self._cbc_high:
            self._cbc_high = price
        if self._cbc_low == 0.0 or price < self._cbc_low:
            self._cbc_low = price

        candle_size = abs(self._cbc_close - self._cbc_open)

        if candle_size < self._brick_size_pts:
            return None

        out_time:       list = []
        out_time_real:  list = []
        out_open:       list = []
        out_high:       list = []
        out_low:        list = []
        out_close:      list = []

        # While loop can emit multiple bricks per tick (gap scenario).
        # After emitting: close is reset to price, so candle_size is re-evaluated
        # against the current price and the new open — may trigger further bricks.
        while candle_size >= self._brick_size_pts:
            if self._cbc_open < self._cbc_close:
                self._cbc_close = self._cbc_open + self._brick_size_pts
            elif self._cbc_open > self._cbc_close:
                self._cbc_close = self._cbc_open - self._brick_size_pts

            out_time.append(self._next_fake_ts())
            out_time_real.append(tstamp_msc)
            out_open.append(self._cbc_open)
            out_high.append(max(self._cbc_open, self._cbc_close))
            out_low.append(min(self._cbc_open, self._cbc_close))
            out_close.append(self._cbc_close)

            self._cbc_open  = self._cbc_close
            self._cbc_high  = price
            self._cbc_low   = price
            self._cbc_close = price   # reset to price — key difference from history mode
            candle_size = abs(self._cbc_close - self._cbc_open)

        if not out_open:
            return None

        return pd.DataFrame({
            "time":         out_time,
            "time_real":    pd.to_datetime(out_time_real, unit="ms"),
            "open":         [round(x, self._digits) for x in out_open],
            "high":         [round(x, self._digits) for x in out_high],
            "low":          [round(x, self._digits) for x in out_low],
            "close":        [round(x, self._digits) for x in out_close],
        })