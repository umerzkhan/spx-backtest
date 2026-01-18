# SPX Backtest

A Python-based intraday backtest strategy for SPX using 15-minute bars.

## Strategy Overview

1. **Morning Range (9:30 AM – 1:00 PM ET)**: Compute support (min of Open/Close) and resistance (max of Open/Close).
2. **Afternoon Session (1:00 PM – 4:00 PM ET)**: Look for entry signals:
   - **LONG**: Price touches support + 2 consecutive higher highs.
   - **SHORT**: Price touches resistance + 2 consecutive lower lows.
3. **Exit**: At market close (last 15-min bar of the day).

## Files

- `backtest_daily.py` — Main backtest script (run daily).
- `trade_log.xlsx` — Trade log with Date, Type, Entry, Exit, Close, PnL, Result.

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

## Scheduled Run

A LaunchAgent is configured to run the backtest daily at 10:00 PM Pacific:

```
~/Library/LaunchAgents/com.spxbacktest.daily.plist
```

Logs:
- `~/Documents/SPX Backtest/backtest_daily.out.log`
- `~/Documents/SPX Backtest/backtest_daily.err.log`

## Requirements

```bash
pip install yfinance pandas openpyxl
```

## Results (60-day sample)

- **Trades**: 25
- **Win Rate**: 68%
- **Max Drawdown**: -25.96
- **Total PnL**: 173.60
