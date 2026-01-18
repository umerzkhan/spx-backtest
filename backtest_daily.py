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


def backtest_unified_15m(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    days = df.groupby(df.index.date)

    for date, day_data in days:
        morning = day_data.between_time("09:30", "13:00")
        if len(morning) < 14:
            continue

        morning_oc = pd.concat([morning["Open"], morning["Close"]])
        res_level = morning_oc.max()
        sup_level = morning_oc.min()

        afternoon = day_data.between_time("13:00", "16:00")

        # Day's closing price (last bar of the day)
        day_close = day_data.iloc[-1]["Close"]

        pos = None
        entry = None
        entry_time = None
        for i in range(2, len(afternoon)):
            curr = afternoon.iloc[i]
            p1 = afternoon.iloc[i - 1]
            p2 = afternoon.iloc[i - 2]

            if pos is None and curr["Low"] <= sup_level:
                if curr["High"] > p1["High"] and p1["High"] > p2["High"]:
                    entry = curr["Close"]
                    entry_time = afternoon.index[i]
                    pos = "LONG"
            elif pos is None and curr["High"] >= res_level:
                if curr["Low"] < p1["Low"] and p1["Low"] < p2["Low"]:
                    entry = curr["Close"]
                    entry_time = afternoon.index[i]
                    pos = "SHORT"

            if pos is not None and i == len(afternoon) - 1:
                exit_price = curr["Close"]
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


def upsert_trade_log(output_path: Path, trade_log: pd.DataFrame) -> pd.DataFrame:
    if output_path.exists():
        existing = pd.read_excel(output_path)
        combined = pd.concat([existing, trade_log], ignore_index=True)
    else:
        combined = trade_log.copy()

    combined["Date"] = pd.to_datetime(combined["Date"]).dt.date
    combined = combined.drop_duplicates(subset=["Date"], keep="last")
    combined = combined.sort_values("Date")
    combined.to_excel(output_path, index=False)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="SPX 15m backtest (daily run)")
    parser.add_argument("--ticker", default="^SPX")
    parser.add_argument("--period", default="60d")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--output", default="trade_log.xlsx")
    args = parser.parse_args()

    data = download_data(args.ticker, args.period, args.interval)
    trade_log = backtest_unified_15m(data)

    output_path = Path(args.output).expanduser().resolve()
    if not trade_log.empty:
        trade_log = upsert_trade_log(output_path, trade_log)
    else:
        output_path = None

    metrics = compute_metrics(trade_log)

    print("Run time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Trades:", metrics["trades"])
    print("Win Rate:", f'{metrics["win_rate"] * 100:.2f}%')
    print("Max Drawdown:", metrics["max_drawdown"])
    print("Total PnL:", metrics["total_pnl"])
    if output_path:
        print("Saved:", str(output_path))


if __name__ == "__main__":
    main()
