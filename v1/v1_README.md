# Renko Trader v1

A Python desktop trading application that connects to MetaTrader 5 (MT5), builds real-time Renko bricks from tick data, displays two exponential moving averages (EMAs), and can submit market-order requests based on EMA crossover signals.

> **Warning:** This project is a technical demonstration and educational prototype. It is not production-ready trading software. It is not investment advice and does not guarantee performance or profitability. Test thoroughly in a demo environment before considering any live use. You are responsible for validating all configuration values, broker-specific trading constraints, and order results.

![Renko Trader v1 Application](RT-v1-App.png)

## Features

- Desktop graphical interface built with **PySide6**.
- Connection to an installed and authenticated **MetaTrader 5** terminal.
- Historical tick loading and real-time tick monitoring.
- Tick-based Renko brick generation.
- Renko chart rendering through `lightweight-charts`.
- Two configurable **Exponential Moving Averages (EMAs)**:
  - `MA_001`: fast EMA.
  - `MA_002`: slow EMA.
- Demonstration trading strategy based on confirmed EMA crossovers.
- Configurable market-order parameters:
  - symbol;
  - trade volume;
  - stop-loss and take-profit distances;
  - deviation;
  - MT5 magic number.
- Optional trading-session filter.
- Interface-terminal messages and persistent log output.

## Architecture Overview

```text
v1/
├── src/
│   ├── config/                 # Configuration loader module
│   ├── GUI/                    # PySide6 UI, chart, Renko candles, and indicators
│   ├── price_feed/             # MetaTrader 5 tick feed
│   ├── strategy/               # EMA crossover strategy and MT5 position manager
│   ├── utils/                  # Shared utilities
│   ├── config.json             # Runtime configuration file
│   └── main.py                 # Application entry point
├── README.md
├── renko-trader-app.png
└── requirements.txt
```

## Requirements

Before running the application, ensure that you have:

1. Python and the dependencies listed in `requirements.txt`.
2. MetaTrader 5 installed on the local machine.
3. An MT5 terminal session logged in to a valid demo or live account.
4. **Algo Trading** enabled in MT5 if you intend to submit orders from the application.
5. A symbol available in the connected terminal that matches `asset.symbol` in `src/config.json`.

## Installation

From the `v1` directory, create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Windows Command Prompt:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

### `pandas_ta` Compatibility Workaround

The project uses `pandas_ta` to initialize EMAs. With the pinned dependency set, you may need to apply the following workaround for a NumPy import incompatibility:

1. Locate `pandas-ta/momentum/squeeze_pro.py` inside the active virtual environment.
2. Replace:

```python
from numpy import NaN as npNaN
```

with:

```python
from numpy import nan as npNaN
```

This workaround is based on the issue referenced by the original project documentation: [pandas-ta issue #799](https://github.com/twopirllc/pandas-ta/issues/799).

## Configuration

The runtime configuration is loaded by `config_return()` in `src/config/config.py`.

`config_return()` opens `config.json` relative to the current working directory. Run the application from `v1/src`; therefore, the active runtime configuration file is:

```text
v1/src/config.json
```

The configuration loader includes built-in defaults if `config.json` cannot be found. Keeping `src/config.json` present is recommended so that all operational values are explicit and reviewable.

### Main Configuration Fields

| Section | Field | Purpose |
|---|---|---|
| `asset` | `symbol` | MT5 symbol to monitor and trade. |
| `asset` | `brick_size_points` | Renko brick size, expressed in symbol tick-size units. |
| `price_feed.MT5` | `path` | Full path to the MT5 terminal executable. |
| `price_feed.MT5` | `lookback_hours` | Amount of tick history used to build the initial chart. |
| `chart.INDs.MA_001` | `length` | Fast EMA period. |
| `chart.INDs.MA_002` | `length` | Slow EMA period. |
| `strategy.positions` | `magic_number` | Identifier used to select this application's MT5 positions. |
| `strategy.positions` | `lot_size` | Requested volume for new market orders. |
| `strategy.positions` | `SL_points` | Stop-loss distance in points. |
| `strategy.positions` | `TP_points` | Take-profit distance in points. |
| `strategy.positions` | `deviation_points` | Allowed price deviation for order requests. |
| `strategy.filters.trading_period` | `enabled`, `start`, `end` | Optional time-of-day filter for new entries. |
| `strategy.risk_management.break_even` | `target_points`, `level_points` | Break-even settings retained in configuration; not active in the v1 main flow. |
| `logger` | `path` | Output path for the application log file. |

### Example Configuration

```json
{
  "asset": {
    "symbol": "XAUUSD",
    "brick_size_points": 10
  },
  "price_feed": {
    "MT5": {
      "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
      "lookback_hours": 6
    }
  },
  "chart": {
    "INDs": {
      "MA_001": { "length": 10 },
      "MA_002": { "length": 20 }
    }
  }
}
```

Review every trading-related parameter before use. Values such as symbol names, minimum volumes, tick sizes, stop distances, and filling policies are broker- and instrument-dependent.

## Running the Application

Run the application from `v1/src` so that `config.json` is resolved correctly:

```bash
cd src
python main.py
```

## Using the Interface

1. Click **Connect**.
   - The application connects to MT5.
   - Available MT5 symbols are loaded into the symbol selector.
   - Historical ticks are requested for the configured lookback period.
   - Renko bricks and the two EMAs are built and displayed.
   - A background Qt thread begins monitoring new ticks.
   - The **Run** button becomes available.

2. Select a symbol and set the brick size as needed.
   - Changing either value after initialization disconnects the price feed and clears the chart.
   - Click **Connect** again to rebuild the chart with the updated parameters.

3. Click **Run** to enable strategy order processing.
   - **Run** enables order requests after eligible crossover signals.
   - **Stop** disables new strategy-driven order requests.

4. Click **Disconnect** to stop the feed, disconnect from MT5, and clear the chart.

## Renko Processing

The application uses MT5 tick data and the tick `ask` price to build Renko bricks.

- The effective brick size is derived from `brick_size_points` and the symbol's `trade_tick_size`.
- A brick is confirmed when the absolute movement from the active brick open reaches or exceeds the effective brick size.
- A single tick can produce multiple Renko bricks if its price movement crosses multiple brick intervals.
- Each brick stores both:
  - a **real timestamp**, originating from the market tick; and
  - a **synthetic timestamp**, incremented by one minute per brick for chart rendering.

The synthetic timestamp exists because Renko bricks are price-driven rather than time-driven. The real timestamp is retained for strategy events and order-request messages.

## Indicators and Strategy

### Exponential Moving Averages

Two EMAs are calculated from Renko brick closing prices:

- `MA_001` is the fast EMA.
- `MA_002` is the slow EMA.

Historical EMA values are initialized with `pandas_ta`. New values are subsequently updated incrementally using:

$$
EMA_t = P_t \cdot \frac{2}{n+1} + EMA_{t-1} \cdot \left(1 - \frac{2}{n+1}\right)
$$

Where $P_t$ is the latest Renko close and $n$ is the EMA length.

### EMA Crossover Logic

The strategy evaluates confirmed Renko bricks:

- When the fast EMA transitions from below the slow EMA to above it, the strategy generates a **buy** signal.
- When the fast EMA transitions from above the slow EMA to below it, the strategy generates a **sell** signal.
- Signals only result in order-processing attempts when **Run** is enabled.

When processing a buy signal, the application can request closure of eligible short positions and then request a buy position. For a sell signal, it can request closure of eligible long positions and then request a sell position.

Only positions for the configured symbol and `magic_number` are selected by the position manager.

### Trading-Period Filter

When `strategy.filters.trading_period.enabled` is enabled, new entries are authorized only from `start` (inclusive) to `end` (exclusive), based on the real tick timestamp formatted as a time of day.

Outside the configured period, the strategy attempts to close positions it manages. When the filter is disabled, entries are permitted at any time.

## Order Requests

Orders are submitted through the MetaTrader 5 Python integration as market-deal requests:

- Buy requests use the symbol ask price.
- Sell requests use the symbol bid price.
- Stop-loss and take-profit prices are derived from their configured point distances and the symbol tick size.
- The requested filling mode is `ORDER_FILLING_IOC`.
- The requested time policy is `ORDER_TIME_GTC`.

> The application logs that an order or close request was sent. It does not currently perform comprehensive validation of the returned MT5 execution result. Always verify order status directly in MetaTrader 5.

## Logging

The application writes informational and error messages to:

- the terminal panel in the UI; and
- the file configured by `logger.path` (default: `log.txt`).

If the log file does not exist, it is created automatically. Log timestamps use the local time of the host machine and include milliseconds.

## Current Limitations

- The strategy is intentionally simple and is not a validated trading system.
- Break-even configuration and helper methods are present, but break-even processing is not connected to the active v1 application loop.
- Order-request log messages do not by themselves confirm fills, rejections, or final trade state.
- The application does not replace broker-specific validation of symbols, trade permissions, volume limits, stop levels, filling modes, or account conditions.
- Renko charts use synthetic timestamps for display and should not be interpreted as conventional time-based candles.

## Disclaimer

This repository is provided for development, learning, and experimentation. It does not provide investment advice, trading recommendations, or any guarantee of performance. Trading financial instruments involves substantial risk, including the possible loss of capital.

## License

This project is distributed under the repository's [LICENSE](../LICENSE).
