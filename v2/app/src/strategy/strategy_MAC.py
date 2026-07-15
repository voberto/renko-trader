# strategy_MAC.py
# Implementation of a Moving Average Crossover (MAC) strategy.
# Signals are generated when a fast MA crosses a slow MA.

import pandas as pd
from typing import Optional
from .strategy_utils import cl_StrategyBase
from shared.constants import SIG_TYPE_LONG, SIG_TYPE_SHORT


class cl_StrategyMAC(cl_StrategyBase):
    """
    Moving Average Crossover strategy implementation.
    Detects when the fast moving average crosses over or under the slow moving average.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        
        # State tracking for crossover detection
        self._prev_fast: Optional[float] = None
        self._prev_slow: Optional[float] = None
        self._bound_fast_name: Optional[str] = None
        self._bound_slow_name: Optional[str] = None

    def set_bindings(self, candidates: dict) -> None:
        """
        Arbitrates MA roles based on period:
        - MA_fast -> MA with the smallest period
        - MA_slow -> MA with the largest period
        Strategy is invalid if fewer than 2 MAs exist or periods are identical.
        """
        all_mas = candidates.get("IND_MA", [])

        if len(all_mas) < 2:
            raise ValueError(f"Requires at least 2 active MA indicators, found {len(all_mas)}.")

        sorted_mas = sorted(all_mas, key=lambda x: x["params"].get("period", 0))

        fast_period = sorted_mas[0]["params"].get("period")
        slow_period = sorted_mas[-1]["params"].get("period")

        if fast_period == slow_period:
            raise ValueError(f"Both MA indicators share the same period ({fast_period}). Cannot distinguish fast/slow.")

        self._bound_fast_name = sorted_mas[0]["name"]
        self._bound_slow_name = sorted_mas[-1]["name"]

    def process(self, candle: pd.Series, indicator_values: dict[str, float]) -> Optional[dict]:
        """
        Processes a closed candle and checks for a crossover signal.
        
        Logic:
        - LONG: Fast MA crosses ABOVE Slow MA.
        - SHORT: Fast MA crosses BELOW Slow MA.
        """
        # 1. Extract current values based on roles defined in config
        curr_fast = indicator_values.get(self._bound_fast_name)
        curr_slow = indicator_values.get(self._bound_slow_name)

        # 2. Safety check: ensure both indicators provided values
        if curr_fast is None or curr_slow is None:
            return None

        signal = None

        # 3. Detect Crossover (requires previous values)
        if self._prev_fast is not None and self._prev_slow is not None:
            
            # Check for Fast Crossing ABOVE Slow (LONG)
            if self._prev_fast <= self._prev_slow and curr_fast > curr_slow:
                signal = {
                    "type": SIG_TYPE_LONG,
                    "id": self.id,
                    "name": self.name,
                    "price": candle.get("close"),
                    "time": candle.get("time")
                }
            
            # Check for Fast Crossing BELOW Slow (SHORT)
            elif self._prev_fast >= self._prev_slow and curr_fast < curr_slow:
                signal = {
                    "type": SIG_TYPE_SHORT,
                    "id": self.id,
                    "name": self.name,
                    "price": candle.get("close"),
                    "time": candle.get("time")
                }

        # 4. Update state for the next call
        self._prev_fast = curr_fast
        self._prev_slow = curr_slow

        return signal