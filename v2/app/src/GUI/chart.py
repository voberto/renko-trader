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
        # Indicator line series — {name: line_object}
        self._indicator_lines: dict = {}
        # Configure dark theme styling on the TradingView chart widget
        self.apply_theme()

    def apply_theme(self) -> None:
        """
        Applies a consistent dark theme matching the TradingView style.
        """
        self.layout(background_color=COLOR_CHART_BG, text_color="#8F9092")
        self.grid(vert_enabled=True, horz_enabled=True, color=COLOR_CHART_GRID)
        self.candle_style(
            up_color=COLOR_CANDLE_UP_BODY,   down_color=COLOR_CANDLE_DOWN_BODY,
            border_up_color=COLOR_CANDLE_UP_BODY, border_down_color=COLOR_CANDLE_DOWN_BODY,
            wick_up_color=COLOR_CANDLE_UP_WICK,   wick_down_color=COLOR_CANDLE_DOWN_WICK,
        )

    # -----------------------------------------------------------------------
    # Candle rendering
    # -----------------------------------------------------------------------

    def load_historical_candles(self, df: pd.DataFrame) -> None:
        """
        Receives a formatted DataFrame from cl_CandleEngine.process_history()
        or cl_RenkoEngine.process_history() and renders it on the chart.
        No OHLC processing is performed here.
        """
        if df is None or df.empty:
            return

        self.set(df)
        self._current_candle = df.iloc[-1]

    def update_tick(self, series: pd.Series) -> None:
        """
        Receives a formatted pd.Series from cl_CandleEngine.process_tick()
        and updates the current bar on the chart.
        No OHLC processing is performed here.
        """
        if series is None:
            return

        self._current_candle = series
        self.update(series)

    def update_ticks(self, df: pd.DataFrame) -> None:
        """
        Receives a DataFrame of one or more new Renko bricks from
        cl_RenkoEngine.process_tick() and updates the chart for each brick.
        No OHLC processing is performed here.
        """
        if df is None or df.empty:
            return

        for _, row in df.iterrows():
            self._current_candle = row
            self.update(row)

    # -----------------------------------------------------------------------
    # Indicator line management
    # -----------------------------------------------------------------------

    def create_indicator_line(self, name: str, color: str) -> None:
        """
        Creates a named line series on the chart for the given indicator.
        Must be called once per indicator before load_indicator_history().

        Parameters
        ----------
        name  : str   Unique indicator name (used as key for subsequent calls).
        color : str   CSS color string (e.g. 'rgba(39, 183, 245, 0.8)').
        """
        if name in self._indicator_lines:
            return
        self._indicator_lines[name] = self.create_line(name, color=color)

    def load_indicator_history(self, name: str, df: pd.DataFrame) -> None:
        """
        Populates a named indicator line with historical data.

        Parameters
        ----
        name : str          Indicator name as registered via create_indicator_line().
        df   : pd.DataFrame Columns: 'time' and 'value'. May be empty (insufficient history).
        """
        line = self._indicator_lines.get(name)
        if line is None or df is None or df.empty:
            return

        # lightweight-charts expects a column named after the line (not 'value')
        df_chart = df.rename(columns={"value": name}).copy()

        # Keep the chart timestamp reference exactly as produced by the candle engine:
        # regular candles use real timestamps; Renko candles use fake chart timestamps.
        # Always pass datetime-like values to avoid int seconds being interpreted as ms.
        df_chart["time"] = pd.to_datetime(df_chart["time"])

        line.set(df_chart)

    def update_indicator(self, name: str, series: Optional[pd.Series]) -> None:
        """
        Updates a named indicator line with a single new point.

        Parameters
        ----
        name   : str              Indicator name as registered via create_indicator_line().
        series : pd.Series|None   Fields: 'time' and 'value'. Skipped if None.
        """
        if series is None:
            return

        line = self._indicator_lines.get(name)
        if line is None:
            return

        # lightweight-charts expects the value field named after the line (not 'value')
        series_chart = series.rename({"value": name}).copy()

        # Always pass datetime-like values to Line.update().
        # If an int Unix timestamp is passed, this lightweight-charts version treats it as ms.
        series_chart["time"] = pd.to_datetime(series_chart["time"])

        line.update(series_chart)

    # -----------------------------------------------------------------------
    # Reset
    # -----------------------------------------------------------------------

    def chart_clear(self) -> None:
        """
        Clears all candle and indicator series data from the chart.
        """
        self._current_candle = None
        self.set()

        for line in self._indicator_lines.values():
            line.set()