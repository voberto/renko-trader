"""
Chart component.

Represents the chart area of the v2 GUI utilizing lightweight-charts (QtChart)
to render candles and technical indicators with a styled dark theme.
"""

import pandas as pd
from typing import Optional
from .chart_custom import CustomChart

from src.GUI.ui_constants import (
    COLOR_CHART_BG,
    COLOR_CHART_GRID,
    COLOR_CANDLE_UP_BODY,
    COLOR_CANDLE_UP_WICK,
    COLOR_CANDLE_DOWN_BODY,
    COLOR_CANDLE_DOWN_WICK,
)


class cl_Chart(CustomChart):
    def __init__(self):
        # QtChart manages its own QWebEngineView widget
        super().__init__()
        # Last rendered bar — kept for internal reference only
        self._current_candle: Optional[pd.Series] = None
        # Configure dark theme styling on the TradingView chart widget
        self.apply_theme()

    def apply_theme(self) -> None:
        """
        Applies a consistent dark theme matching the TradingView style.
        """
        self.layout(background_color=COLOR_CHART_BG, text_color="#8F9092")
        self.grid(vert_enabled=True, horz_enabled=True, color=COLOR_CHART_GRID)
        self.candle_style(up_color=COLOR_CANDLE_UP_BODY, down_color=COLOR_CANDLE_DOWN_BODY,
                          border_up_color=COLOR_CANDLE_UP_BODY, border_down_color=COLOR_CANDLE_DOWN_BODY,
                          wick_up_color=COLOR_CANDLE_UP_WICK, wick_down_color=COLOR_CANDLE_DOWN_WICK,)

    def load_historical_candles(self, df: pd.DataFrame) -> None:
        """
        Receives a formatted DataFrame from cl_CandleEngine.process_history()
        and renders it on the chart. No OHLC processing is performed here.
        """
        if df is None or df.empty:
            return

        self.set(df)
        self._current_candle = df.iloc[-1]

    def update_tick(self, series: pd.Series) -> None:
        """
        Receives a formatted pd.Series from cl_CandleEngine.process_tick()
        and updates the current bar on the chart. No OHLC processing is performed here.
        """
        if series is None:
            return

        self._current_candle = series
        self.update(series)

    def update_ticks(self, df: pd.DataFrame) -> None:
        """
        Receives a DataFrame of one or more new Renko bricks from cl_RenkoEngine.process_tick()
        and updates the chart for each brick. No OHLC processing is performed here.
        """
        if df is None or df.empty:
            return

        for _, row in df.iterrows():
            self._current_candle = row
            self.update(row)

    def chart_clear(self) -> None:
        """
        Clears all series data from the chart screen.
        """
        self._current_candle = None
        self.set()