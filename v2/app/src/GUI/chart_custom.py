import pandas as pd
from typing import Optional

from lightweight_charts.widgets import QtChart
from lightweight_charts.abstract import Line
from lightweight_charts.util import js_data
from lightweight_charts.util import LINE_STYLE


def _to_chart_timestamp(value) -> int:
    """
    Converts a Python/Pandas time value into Unix seconds for lightweight-charts.

    This function centralizes the timestamp workaround required by the
    lightweight-charts-python wrapper.

    Rules:
    - datetime-like values are converted through pandas and emitted as seconds.
    - numeric values are treated as Unix seconds if they look like seconds.
    - numeric values are treated as Unix milliseconds if they look like ms.
    - strings are parsed by pandas.
    """
    if isinstance(value, pd.Timestamp):
        return int(value.timestamp())

    if isinstance(value, (int, float)):
        # Unix milliseconds are normally 13 digits.
        # Unix seconds are normally 10 digits.
        if abs(value) > 10_000_000_000:
            return int(pd.to_datetime(value, unit="ms").timestamp())
        return int(pd.to_datetime(value, unit="s").timestamp())

    return int(pd.to_datetime(value).timestamp())


class CustomLine(Line):
    """
    Fixed Line series for indicator plotting.

    The original lightweight-charts-python Line implementation can interpret
    numeric timestamps inconsistently:
    - set() may treat integers as nanoseconds through pd.to_datetime().
    - update() may treat integers as milliseconds.

    This class normalizes all line timestamps to Unix seconds before data is
    sent to the JS chart.
    """

    def _df_datetime_format(self, df: pd.DataFrame, exclude_lowercase=None):
        df = df.copy()
        df.columns = self._format_labels(df, df.columns, df.index, exclude_lowercase)
        self._set_interval(df)

        df["time"] = df["time"].apply(_to_chart_timestamp)
        return df

    def _series_datetime_format(self, series: pd.Series, exclude_lowercase=None):
        series = series.copy()
        series.index = self._format_labels(series, series.index, series.name, exclude_lowercase)
        series["time"] = _to_chart_timestamp(series["time"])
        return series

    def _single_datetime_format(self, arg) -> int:
        return _to_chart_timestamp(arg)


class CustomChart(QtChart):
    """
    Fixed QtChart due to:
    https://github.com/louisnw01/lightweight-charts-python/issues/576#issuecomment-4205357008

    This custom chart also fixes Line series timestamp handling so indicators
    use the same chart-time reference as candles.
    """

    def _df_datetime_format(self, df: pd.DataFrame, exclude_lowercase=None):
        df = df.copy()
        df.columns = self._format_labels(df, df.columns, df.index, exclude_lowercase)
        self._set_interval(df)

        df["time"] = df["time"].apply(_to_chart_timestamp)
        return df

    def set(self, df: Optional[pd.DataFrame] = None, keep_drawings=False):
        if df is None or df.empty:
            self.run_script(f"{self.id}.series.setData([])")
            self.run_script(f"{self.id}.volumeSeries.setData([])")
            self.candle_data = pd.DataFrame()
            return

        df = self._df_datetime_format(df)
        self.candle_data = df.copy()
        self._last_bar = df.iloc[-1]
        self.run_script(f"{self.id}.series.setData({js_data(df)})")

        if "volume" not in df:
            return

        volume = df.drop(columns=["open", "high", "low", "close"]).rename(columns={"volume": "value"})
        volume["color"] = self._volume_down_color
        volume.loc[df["close"] > df["open"], "color"] = self._volume_up_color
        self.run_script(f"{self.id}.volumeSeries.setData({js_data(volume)})")

        for line in self._lines:
            if line.name not in df.columns:
                continue
            line.set(df[["time", line.name]], format_cols=False)

        self.run_script(f"""
            if (!{self.id}.chart.priceScale("right").options.autoScale)
                {self.id}.chart.priceScale("right").applyOptions({{autoScale: true}})
        """)

        if keep_drawings:
            self.run_script(f"{self._chart.id}.toolBox?._drawingTool.repositionOnTime()")
        else:
            self.run_script(f"{self._chart.id}.toolBox?.clearDrawings()")

    def create_line(
        self,
        name: str = "",
        color: str = "rgba(214, 237, 255, 0.6)",
        style: LINE_STYLE = "solid",
        width: int = 2,
        price_line: bool = True,
        price_label: bool = True,
        price_scale_id: Optional[str] = None,
    ) -> CustomLine:
        """
        Creates a fixed Line object.

        This overrides lightweight-charts-python AbstractChart.create_line()
        so indicator lines use CustomLine instead of the original Line class.
        """
        self._lines.append(
            CustomLine(
                self,
                name,
                color,
                style,
                width,
                price_line,
                price_label,
                price_scale_id,
            )
        )
        return self._lines[-1]