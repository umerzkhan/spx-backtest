# SPX Backtest

A Python-based intraday backtest strategy for SPX using 15-minute bars.

## Strategy Overview

1. **Morning Range (9:30 AM – 11:30 AM ET)**: Compute support (min of Open/Close) and resistance (max of Open/Close).
2. **Signal Session (11:30 AM – 4:00 PM ET)**: Look for entry signals:
   - **LONG**: Signal bar touches support and opens/closes above it, then the next bar makes a higher high.
   - **SHORT**: Signal bar touches resistance and opens/closes below it, then the next bar makes a lower low.
   - **Entry**: Open of the bar after the confirmation bar.
3. **Exit**: 
   - **LONG**: Price tests resistance AND next candle makes lower low → exit at next candle open (confirmed reversal).
   - **SHORT**: Price tests support AND next candle makes higher high → exit at next candle open (confirmed reversal).
   - **Fallback**: At market close if levels not reached or confirmation not met (last 15-min bar of the day).

## Files

- `backtest_daily.py` — Main backtest script (run daily).
- `dashboard.py` — Interactive Streamlit dashboard for visualizing results.
- `trade_log.xlsx` — Trade log with Date, Entry, Exit, Close, Exit Reason, PnL, Win Rate.

## Usage

```bash
python3 backtest_daily.py --output trade_log.xlsx
```

### Options

| Argument     | Default       | Description                     |
|--------------|---------------|---------------------------------|
| `--ticker`   | `^SPX`        | Ticker symbol                   |
| `--period`   | `60d`         | Data period (max ~60d for 15m)  |
| `--interval` | `15m`         | Bar interval                    |
| `--output`   | `trade_log.xlsx` | Output Excel file            |

## Dashboard

Launch the interactive dashboard to visualize backtest results:

```bash
streamlit run dashboard.py
```

The dashboard includes:
- **Performance Metrics**: Total trades, win rate, PnL, drawdown
- **Equity Curve**: Cumulative PnL over time
- **PnL Distribution**: Histogram of trade outcomes
- **Exit Reason Breakdown**: Pie chart of exit types
- **Drawdown Chart**: Visual representation of drawdown periods
- **Trade Log Table**: Filterable table with all trades
- **Auto-refresh**: Option to automatically refresh data every 30 seconds

The dashboard automatically reads from `trade_log.xlsx` and updates when the file changes.

## Requirements

Install all dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install yfinance pandas openpyxl streamlit plotly
```

## Results (60-day sample)

- **Trades**: 25
- **Win Rate**: 72.00%
- **Max Drawdown**: -52.70
- **Total PnL**: 229.60
- **Exit Distribution**: ~20% exit at confirmed support/resistance levels, ~80% exit at close
