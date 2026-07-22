from __future__ import annotations

import argparse
import time
from pathlib import Path
import pandas as pd
import requests

# Mapping from internal symbol to yfinance futures ticker symbol
FUTURES_MAP = {
    "ES": "ES=F",    # E-mini S&P 500
    "NQ": "NQ=F",    # E-mini Nasdaq 100
    "RTY": "RTY=F",  # E-mini Russell 2000
    "YM": "YM=F",    # E-mini Dow Jones
    "GC": "GC=F",    # Gold Futures
    "SI": "SI=F",    # Silver Futures
    "CL": "CL=F",    # Crude Oil Futures
    "NG": "NG=F",    # Natural Gas Futures
    "6E": "6E=F",    # Euro FX Futures
    "6J": "6J=F",    # Japanese Yen Futures
    "6B": "6B=F",    # British Pound Futures
    "ZB": "ZB=F",    # 30-Year T-Bond Futures
    "ZN": "ZN=F",    # 10-Year T-Note Futures
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

def fetch_ticker_chart_v8(yf_ticker: str, range_str: str = "2y") -> pd.DataFrame:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_ticker}?range={range_str}&interval=1d"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        raise ValueError(f"HTTP {resp.status_code}: {resp.text[:100]}")

    data = resp.json()
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    if not timestamps:
        return pd.DataFrame()

    indicators = result["indicators"]["quote"][0]
    df = pd.DataFrame({
        "date": pd.to_datetime(timestamps, unit="s").strftime("%Y-%m-%d"),
        "open": indicators.get("open", []),
        "high": indicators.get("high", []),
        "low": indicators.get("low", []),
        "close": indicators.get("close", []),
        "volume": indicators.get("volume", []),
    })

    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("date").reset_index(drop=True)
    return df

def fetch_futures_data(symbols: list[str] | None = None, range_str: str = "2y", output_dirs: list[Path] | None = None) -> dict[str, pd.DataFrame]:
    if not symbols:
        symbols = list(FUTURES_MAP.keys())

    if not output_dirs:
        calc_root = Path(__file__).resolve().parents[3]
        output_dirs = [
            calc_root / "turtle_trader" / "data",
            calc_root / "turtle_trader" / "turtle_trader" / "data"
        ]

    for d in output_dirs:
        d.mkdir(parents=True, exist_ok=True)

    results = {}
    print(f"Fetching EOD futures history via Yahoo REST Chart API for {len(symbols)} tickers...")

    for sym in symbols:
        yf_ticker = FUTURES_MAP.get(sym, f"{sym}=F")
        try:
            df = fetch_ticker_chart_v8(yf_ticker, range_str=range_str)
            if df.empty:
                print(f"  [WARNING] No data for {sym} ({yf_ticker})")
                continue

            for out_dir in output_dirs:
                out_csv = out_dir / f"{sym}.csv"
                df.to_csv(out_csv, index=False)

            print(f"  [SUCCESS] {sym} ({yf_ticker}): Wrote {len(df)} daily bars")
            results[sym] = df
            time.sleep(0.15)
        except Exception as e:
            print(f"  [ERROR] Failed {sym} ({yf_ticker}): {e}")

    return results

def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch daily futures data via Yahoo REST API")
    ap.add_argument("--symbols", nargs="+", help="Symbols to fetch")
    ap.add_argument("--range", default="2y", help="Historical range (e.g. 1y, 2y, 5y)")
    args = ap.parse_args()

    fetch_futures_data(symbols=args.symbols, range_str=args.range)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
