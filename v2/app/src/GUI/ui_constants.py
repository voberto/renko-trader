"""
GUI constants.

This module centralizes all GUI-related constants, including window
configuration, widget sizes, labels, colors and stylesheets.

Keeping these values in a dedicated module avoids magic numbers and
hardcoded strings spread throughout the GUI implementation.
"""

from PySide6.QtWidgets import QSizePolicy


# =============================================================================
# Window
# =============================================================================

GUI_VERSION = "2.0.0"

WINDOW_TITLE = f"Renko Trader v{GUI_VERSION}"

WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700

# =============================================================================
# Size Policies
# =============================================================================

TOP_FRAME_HORIZONTAL_POLICY = QSizePolicy.Policy.Expanding
TOP_FRAME_VERTICAL_POLICY = QSizePolicy.Policy.Fixed

# =============================================================================
# Labels
# =============================================================================

LABEL_SYMBOL = "Symbol (from EA):"
LABEL_BRICK_SIZE = "Brick Size:"


# =============================================================================
# Default Field Values
# =============================================================================

SYMBOL_WAITING_TEXT = "WAITING..."


# =============================================================================
# Button Text
# =============================================================================

BUTTON_CONNECT_TEXT = "CONNECT"
BUTTON_DISCONNECT_TEXT = "DISCONNECT"


# =============================================================================
# Widget Sizes
# =============================================================================

SYMBOL_FIELD_WIDTH = 110
BRICK_FIELD_WIDTH = 80

BUTTON_MIN_WIDTH = 110

TOP_PANEL_HEIGHT = 58

LAYOUT_MARGIN = 8
LAYOUT_SPACING = 8


# =============================================================================
# Colors
# =============================================================================

COLOR_BACKGROUND = "#252526"
COLOR_FRAME = "#2D2D30"

COLOR_TEXT = "#E6E6E6"

COLOR_BORDER = "#3F3F46"

COLOR_FIELD_BACKGROUND = "#1E1E1E"
COLOR_FIELD_READONLY = "#303030"

COLOR_CONNECT = "#2E7D32"
COLOR_CONNECT_HOVER = "#388E3C"

COLOR_DISCONNECT = "#B71C1C"
COLOR_DISCONNECT_HOVER = "#C62828"


# =============================================================================
# Stylesheets
# =============================================================================

STYLE_FRAME = f"""
QFrame {{
    background-color: {COLOR_FRAME};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
}}
"""


STYLE_LABEL = f"""
QLabel {{
    color: {COLOR_TEXT};
}}
"""


STYLE_LINE_EDIT = f"""
QLineEdit {{
    background-color: {COLOR_FIELD_BACKGROUND};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    padding: 4px;
}}

QLineEdit:read-only {{
    background-color: {COLOR_FIELD_READONLY};
}}
"""


STYLE_BUTTON_CONNECT = f"""
QPushButton {{
    background-color: {COLOR_CONNECT};
    color: white;
    border: none;
    border-radius: 4px;
    font-weight: bold;
    min-width: {BUTTON_MIN_WIDTH}px;
    padding: 6px 12px;
}}

QPushButton:hover {{
    background-color: {COLOR_CONNECT_HOVER};
}}

QPushButton:pressed {{
    background-color: {COLOR_CONNECT};
}}
"""


STYLE_BUTTON_DISCONNECT = f"""
QPushButton {{
    background-color: {COLOR_DISCONNECT};
    color: white;
    border: none;
    border-radius: 4px;
    font-weight: bold;
    min-width: {BUTTON_MIN_WIDTH}px;
    padding: 6px 12px;
}}

QPushButton:hover {{
    background-color: {COLOR_DISCONNECT_HOVER};
}}

QPushButton:pressed {{
    background-color: {COLOR_DISCONNECT};
}}
"""

# =============================================================================
# Chart Visual Styles (TradingView Palette)
# =============================================================================

COLOR_CHART_BG = "#1A1A1C"
COLOR_CHART_GRID = "#28282B"

# Candlestick colors
COLOR_CANDLE_UP_BODY = "#2E7D32"     # Dark Green
COLOR_CANDLE_UP_WICK = "#388E3C"     # Green Accent
COLOR_CANDLE_DOWN_BODY = "#B71C1C"   # Dark Red
COLOR_CANDLE_DOWN_WICK = "#C62828"   # Red Accent

# Volume or accessory lines
COLOR_CHART_VOLUME_UP = "rgba(46, 125, 50, 0.4)"
COLOR_CHART_VOLUME_DOWN = "rgba(183, 28, 28, 0.4)"

# Default timeframe (in seconds) used to group ticks
# 60 = M1, 300 = M5, 900 = M15, 3600 = H1
DEFAULT_TIMEFRAME_SECONDS = 60