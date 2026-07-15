# strategy_utils.py
# Abstract base class for all trading strategies.
# Defines the contract for strategy implementation and data processing.

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class cl_StrategyBase(ABC):
    """
    Abstract base class for trading strategies.
    All strategies must implement the process() method.
    """

    def __init__(self, config: dict):
        """
        Initializes the strategy with its specific configuration.
        
        Parameters
        ----
        config : dict
            The strategy-specific configuration dictionary from the JSON file.
        """
        self.config = config
        self.name = config.get("name", "Unknown Strategy")
        self.id = config.get("ID", -1)
        self.enabled = config.get("enabled", False)
        
        # Internal state to be managed by the strategy implementation
        self._last_signal = None 

        # Internal mapping for requirements binding
        self._bindings = {}

    def set_bindings(self, bindings: dict) -> None:
        """Sets the mapping between strategy roles and active indicator names."""
        self._bindings = bindings

    def get_bindings(self) -> dict:
        """Returns the current indicator bindings."""
        return self._bindings

    def warmup(self, candle: pd.Series, indicator_values: dict[str, float]) -> None:
        """
        Optional: Feeds historical data to the strategy to seed its internal state.
        By default, it just calls process() and discards any signal.
        """
        self.process(candle, indicator_values)

    @abstractmethod
    def process(self, candle: pd.Series, indicator_values: dict[str, float]) -> Optional[dict]:
        """
        Processes a completed candle and its associated indicator values.
        
        Parameters
        ----
        candle : pd.Series
            The closed candle/brick data (time, open, high, low, close).
        indicator_values : dict
            Mapping of human-readable role/name to the specific indicator value 
            calculated for this candle.
            Example: {"MA_fast": 112.50, "MA_slow": 110.20}

        Returns
        ----
        Optional[dict]
            A dictionary containing the signal details (type, price, time) 
            if a signal is generated, otherwise None.
        """
        pass

    def __repr__(self):
        return f"<​Strategy {self.name} (ID: {self.id}, Enabled: {self.enabled})>"