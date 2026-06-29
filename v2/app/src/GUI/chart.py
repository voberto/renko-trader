"""
Chart component.

Represents the chart area of the v2 GUI utilizing lightweight-charts (QtChart) 
to render candles and technical indicators with a styled dark theme.
"""

import pandas as pd
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
        
        # Track the active candle to allow correct real-time update logic
        self._current_candle = None # dict with 'time', 'open', 'high', 'low', 'close'
        
        # Configure dark theme styling on the TradingView chart widget
        self.apply_theme()

    def apply_theme(self) -> None:
        """
        Applies a consistent dark theme matching the TradingView style.
        """
        # Chart background and text
        self.layout(
            background_color=COLOR_CHART_BG,
            text_color="#8F9092",
        )
        
        # Grid lines using the correct color parameter
        self.grid(
            vert_enabled=True,
            horz_enabled=True,
            color=COLOR_CHART_GRID,
        )
        
        # Candlestick styling
        self.candle_style(
            up_color=COLOR_CANDLE_UP_BODY,
            down_color=COLOR_CANDLE_DOWN_BODY,
            border_up_color=COLOR_CANDLE_UP_BODY,
            border_down_color=COLOR_CANDLE_DOWN_BODY,
            wick_up_color=COLOR_CANDLE_UP_WICK,
            wick_down_color=COLOR_CANDLE_DOWN_WICK,
        )

    def ticks_to_candles(self, ticks: list, timeframe_secs: int = 60) -> pd.DataFrame:
        """
        Groups a list of raw tick dictionaries into conventional OHLC candles.
        
        Expected tick payload structure from MQL5:
        {
          "tstamp": 1719598201,
          "bid": 2330.15,
          "ask": 2330.25,
          "volume": 1
        }
        """
        if not ticks:
            return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close'])

        # Create pandas DataFrame
        df = pd.DataFrame(ticks)
        
        # Map timestamp and price columns if they have different names
        if 'time' not in df.columns and 'tstamp' in df.columns:
            df['time'] = df['tstamp']
        
        if 'price' not in df.columns:
            df['price'] = df['bid'] if 'bid' in df.columns else df['close']

        # Convert timestamp to datetime for resampling
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)

        # Resample to the requested timeframe (e.g., '60s')
        freq = f"{timeframe_secs}s"
        ohlc = df['price'].resample(freq).ohlc()
        
        # Drop intervals with no ticks
        ohlc.dropna(inplace=True)
        
        # Reset index to retrieve the timestamp column
        ohlc.reset_index(inplace=True)
        
        # Format the time for lightweight-charts
        ohlc['time'] = ohlc['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return ohlc[['time', 'open', 'high', 'low', 'close']]

    def load_historical_candles(self, candles: list) -> None:
        """
        Receives raw historical candles directly from MQL5 rates.
        Formats, sanitizes, sorts ascendingly, and removes duplicates to prevent
        lightweight-charts layout / null errors, preserving pandas.Timestamp type.
        """
        if not candles:
            return

        df = pd.DataFrame(candles)

        if 'time' not in df.columns and 'tstamp' in df.columns:
            df['time'] = df['tstamp']

        df['datetime'] = pd.to_datetime(df['time'], unit='s')

        df_candles = pd.DataFrame({
            'time': df['datetime'].to_list(),
            'open': df['open'].astype(float),
            'high': df['high'].astype(float),
            'low': df['low'].astype(float),
            'close': df['close'].astype(float)
        })

        df_candles = df_candles.sort_values(by='time', ascending=True)

        df_candles = df_candles.drop_duplicates(subset=['time'], keep='last')
        df_candles.reset_index(drop=True, inplace=True)

        self.set(df_candles)

        last_row = df_candles.iloc[-1]
        self._current_candle = {
            'time': last_row['time'],
            'open': float(last_row['open']),
            'high': float(last_row['high']),
            'low': float(last_row['low']),
            'close': float(last_row['close'])
        }
       

    def update_tick(self, tick: dict, timeframe_secs: int = 60) -> None:
        """
        Processes a single incoming tick and updates the active candlestick bar.
        Computes string timestamps matching the active timeframe block.
        """
        tstamp = tick.get("tstamp", tick.get("time"))
        price = tick.get("bid", tick.get("ask", tick.get("price")))

        if tstamp is None or price is None:
            return

        # Ensure correct numerical layouts
        tstamp = int(tstamp)
        price = float(price)

        # Round timestamp down to the nearest timeframe boundary
        rounded_tstamp = (tstamp // timeframe_secs) * timeframe_secs
        dt_rounded = pd.to_datetime(rounded_tstamp, unit='s', utc=True).tz_localize(None)

        if self._current_candle is not None and self._current_candle['time'] == dt_rounded:
            self._current_candle['high'] = max(self._current_candle['high'], price)
            self._current_candle['low'] = min(self._current_candle['low'], price)
            self._current_candle['close'] = price
        else:
            self._current_candle = {
                'time': dt_rounded,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }

        # Safely push the update to the lightweight-charts engine
        series = pd.Series(self._current_candle)
        self.update(series)

    def chart_clear(self) -> None:
        """
        Clears all series data from the chart screen.
        """
        self._current_candle = None
        self.set()