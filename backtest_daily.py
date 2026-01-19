import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


def download_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    data = yf.download(ticker, period=period, interval=interval)
    if isinstance(data.columns, pd.MultiIndex):
        data = data.xs(ticker, level="Ticker", axis=1)
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC").tz_convert("US/Eastern")
    else:
        data.index = data.index.tz_convert("US/Eastern")
    return data


def get_existing_dates(output_path: Path) -> set:
    """Get set of dates that already exist in the Excel file"""
    if not output_path.exists():
        return set()
    try:
        existing = pd.read_excel(output_path)
        if 'Date' in existing.columns:
            existing['Date'] = pd.to_datetime(existing['Date']).dt.date
            return set(existing['Date'].unique())
        return set()
    except Exception:
        return set()


def backtest_unified_15m(df: pd.DataFrame, existing_dates: set = None) -> pd.DataFrame:
    """Run backtest, skipping dates that already exist in Excel"""
    if existing_dates is None:
        existing_dates = set()
    
    results = []
    days = df.groupby(df.index.date)

    for date, day_data in days:
        # Skip dates that already exist in Excel
        if date in existing_dates:
            continue
        morning = day_data.between_time("09:30", "11:30")
        if len(morning) < 8:
            continue

        morning_oc = pd.concat([morning["Open"], morning["Close"]])
        res_level = morning_oc.max()
        sup_level = morning_oc.min()

        afternoon = day_data.between_time("11:30", "16:00")

        # Day's closing price (last bar of the day)
        day_close = day_data.iloc[-1]["Close"]

        pos = None
        entry = None
        entry_time = None
        entry_idx = None
        for i in range(len(afternoon)):
            # Entry logic: touch first, then confirm over the next 1 bar
            # Enter on the NEXT bar open after the confirmation
            if pos is None and i <= len(afternoon) - 3:
                curr = afternoon.iloc[i]

                # LONG: signal bar touches support and opens/closes above it,
                # then next bar makes a higher high
                if curr["Low"] <= sup_level and curr["Open"] > sup_level and curr["Close"] > sup_level:
                    c1 = afternoon.iloc[i + 1]
                    if c1["High"] > curr["High"]:
                        entry_idx = i + 2
                        entry = afternoon.iloc[entry_idx]["Open"]
                        entry_time = afternoon.index[entry_idx]
                        pos = "LONG"

                # SHORT: signal bar touches resistance and opens/closes below it,
                # then next bar makes a lower low
                elif curr["High"] >= res_level and curr["Open"] < res_level and curr["Close"] < res_level:
                    c1 = afternoon.iloc[i + 1]
                    if c1["Low"] < curr["Low"]:
                        entry_idx = i + 2
                        entry = afternoon.iloc[entry_idx]["Open"]
                        entry_time = afternoon.index[entry_idx]
                        pos = "SHORT"

            # Exit logic: Confirmed exit at support/resistance
            # LONG: price tests resistance AND next candle makes lower low → exit at next candle open
            # SHORT: price tests support AND next candle makes higher high → exit at next candle open
            if pos is not None and i < len(afternoon) - 1:  # Need at least one more bar for confirmation
                curr = afternoon.iloc[i]
                next_bar = afternoon.iloc[i + 1]

                # LONG: price tests resistance AND next candle makes lower low
                if pos == "LONG" and curr["High"] >= res_level:
                    if next_bar["Low"] < curr["Low"]:
                        exit_price = next_bar["Open"]  # Exit at open of next candle
                        pnl = exit_price - entry
                        results.append(
                            {
                                "Date": date,
                                "Type": pos,
                                "Entry": entry,
                                "Exit": exit_price,
                                "Close": day_close,
                                "PnL": pnl,
                                "Result": "Profit" if pnl > 0 else ("Loss" if pnl < 0 else "Flat"),
                                "Exit Reason": "Resistance Confirmed",
                            }
                        )
                        break

                # SHORT: price tests support AND next candle makes higher high
                elif pos == "SHORT" and curr["Low"] <= sup_level:
                    if next_bar["High"] > curr["High"]:
                        exit_price = next_bar["Open"]  # Exit at open of next candle
                        pnl = entry - exit_price
                        results.append(
                            {
                                "Date": date,
                                "Type": pos,
                                "Entry": entry,
                                "Exit": exit_price,
                                "Close": day_close,
                                "PnL": pnl,
                                "Result": "Profit" if pnl > 0 else ("Loss" if pnl < 0 else "Flat"),
                                "Exit Reason": "Support Confirmed",
                            }
                        )
                        break

            # Fallback exit at end of day
            if pos is not None and i == len(afternoon) - 1:
                exit_price = day_close
                pnl = (exit_price - entry) if pos == "LONG" else (entry - exit_price)
                results.append(
                    {
                        "Date": date,
                        "Type": pos,
                        "Entry": entry,
                        "Exit": exit_price,
                        "Close": day_close,
                        "PnL": pnl,
                        "Result": "Profit" if pnl > 0 else ("Loss" if pnl < 0 else "Flat"),
                        "Exit Reason": "Closing Price",
                    }
                )
                break

    return pd.DataFrame(results)


def compute_metrics(trade_log: pd.DataFrame) -> dict:
    if trade_log.empty:
        return {"trades": 0, "win_rate": 0.0, "max_drawdown": 0.0, "total_pnl": 0.0}

    trade_log = trade_log.copy()
    trade_log["Win"] = trade_log["PnL"] > 0
    win_rate = trade_log["Win"].mean()
    equity = trade_log["PnL"].cumsum()
    drawdown = equity - equity.cummax()
    max_drawdown = drawdown.min()
    total_pnl = trade_log["PnL"].sum()
    return {
        "trades": len(trade_log),
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "total_pnl": total_pnl,
    }


def append_trade_log(output_path: Path, trade_log: pd.DataFrame) -> pd.DataFrame:
    """Append new trades to existing Excel file, preserving all historical data"""
    if output_path.exists():
        existing = pd.read_excel(output_path)
        # Ensure Date column is in date format for comparison
        if 'Date' in existing.columns:
            existing['Date'] = pd.to_datetime(existing['Date']).dt.date
        if 'Date' in trade_log.columns:
            trade_log['Date'] = pd.to_datetime(trade_log['Date']).dt.date
        
        # Only append new dates (not already in existing)
        existing_dates = set(existing['Date'].unique()) if 'Date' in existing.columns else set()
        new_trades = trade_log[~trade_log['Date'].isin(existing_dates)] if 'Date' in trade_log.columns else trade_log
        
        if not new_trades.empty:
            combined = pd.concat([existing, new_trades], ignore_index=True)
        else:
            combined = existing.copy()
    else:
        combined = trade_log.copy()
        if 'Date' in combined.columns:
            combined['Date'] = pd.to_datetime(combined['Date']).dt.date

    # Sort by date and remove any duplicates (keep first occurrence for historical data integrity)
    if 'Date' in combined.columns:
        combined = combined.sort_values("Date")
        # Only remove duplicates if same date appears multiple times (shouldn't happen with incremental approach)
        combined = combined.drop_duplicates(subset=["Date"], keep="first")
    
    combined.to_excel(output_path, index=False)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="SPX 15m backtest (daily run - incremental)")
    parser.add_argument("--ticker", default="^SPX")
    parser.add_argument("--period", default="60d")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--output", default="trade_log.xlsx")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    
    # Get existing dates to skip processing
    existing_dates = get_existing_dates(output_path)
    if existing_dates:
        print(f"Found {len(existing_dates)} existing dates in Excel. Will skip these and only process new dates.")
    
    # Download data (always get last 60 days to ensure we have latest)
    data = download_data(args.ticker, args.period, args.interval)
    
    # Run backtest, skipping existing dates
    trade_log = backtest_unified_15m(data, existing_dates=existing_dates)

    if not trade_log.empty:
        print(f"Processing {len(trade_log)} new trade(s) for dates: {sorted(trade_log['Date'].unique())}")
        metrics = compute_metrics(trade_log)
        trade_log["Win Rate"] = f'{metrics["win_rate"] * 100:.2f}%'
        trade_log = trade_log[
            ["Date", "Entry", "Exit", "Close", "Exit Reason", "PnL", "Win Rate"]
        ]
        # Append new trades to existing Excel (preserves all historical data)
        combined_log = append_trade_log(output_path, trade_log)
    else:
        if existing_dates:
            print("No new trades found. All dates already processed.")
            # Load existing data for metrics
            combined_log = pd.read_excel(output_path)
        else:
            print("No trades found in the data.")
            combined_log = pd.DataFrame()

    # Compute metrics on all data (historical + new)
    metrics = compute_metrics(combined_log)

    print("\n" + "="*60)
    print("Run time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    print("Total Trades (all time):", metrics["trades"])
    print("Win Rate:", f'{metrics["win_rate"] * 100:.2f}%')
    print("Max Drawdown:", metrics["max_drawdown"])
    print("Total PnL:", metrics["total_pnl"])
    if output_path.exists():
        print(f"\nSaved: {str(output_path)}")
        print(f"Total dates in Excel: {len(combined_log) if not combined_log.empty else 0}")
        print("\n💡 To view the dashboard, run: streamlit run dashboard.py")


if __name__ == "__main__":
    main()
