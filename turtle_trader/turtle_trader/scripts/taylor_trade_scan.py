from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import sys
from pathlib import Path

# Fix paths: script is at turtle_trader/turtle_trader/scripts/taylor_trade_scan.py
script_path = Path(__file__).resolve()
calc_root = script_path.parents[3]       # forward-volatility-calculator
workspace_root = calc_root.parent         # Forward Volatility

if str(calc_root / "turtle_trader") not in sys.path:
    sys.path.insert(0, str(calc_root / "turtle_trader"))
if str(calc_root) not in sys.path:
    sys.path.insert(0, str(calc_root))

from turtle_trader.data import read_ohlcv_csv
from turtle_trader.taylor import analyze_taylor_cycle, calculate_taylor_book
from turtle_trader.scripts.fetch_futures_yfinance import fetch_futures_data, FUTURES_MAP


def run_taylor_scan(data_dir: Path | None = None, fetch_fresh: bool = True) -> dict:
    if data_dir is None:
        data_dir = calc_root / "turtle_trader" / "data"

    if fetch_fresh:
        print("--- Fetching Fresh Futures EOD Data via YFinance ---")
        fetch_futures_data()

    symbols = list(FUTURES_MAP.keys())
    signals = []
    buy_count = 0
    sell_count = 0
    short_count = 0

    latest_date = datetime.now().strftime("%Y-%m-%d")

    for sym in symbols:
        csv_path = data_dir / f"{sym}.csv"
        if not csv_path.exists():
            print(f"Skipping {sym}: CSV not found at {csv_path}")
            continue

        try:
            bars = read_ohlcv_csv(csv_path)
            if not bars:
                continue

            sig = analyze_taylor_cycle(bars, sym)
            if sig:
                signals.append(asdict(sig))
                latest_date = sig.asof
                if sig.cycle_phase == "BUY_DAY":
                    buy_count += 1
                elif sig.cycle_phase == "SELL_DAY":
                    sell_count += 1
                elif sig.cycle_phase == "SELL_SHORT_DAY":
                    short_count += 1
        except Exception as e:
            print(f"Error scanning {sym}: {e}")

    payload = {
        "date": latest_date,
        "timestamp": datetime.now().isoformat(),
        "total_scanned": len(signals),
        "summary": {
            "buy_day_count": buy_count,
            "sell_day_count": sell_count,
            "sell_short_day_count": short_count,
        },
        "signals": signals,
    }

    out_file = calc_root / "taylor_signals_latest.json"
    web_file = workspace_root / "forward-volatility-web" / "public" / "data" / "taylor_signals_latest.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    web_file.parent.mkdir(parents=True, exist_ok=True)
    with open(web_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"--- Exported Taylor signals to Web UI: {web_file} ---")

    print(f"--- Taylor Scan Complete: Wrote {len(signals)} signals to {out_file} ---")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Taylor Trading Technique scanner")
    ap.add_argument("--no-fetch", action="store_true", help="Skip fetching fresh yfinance data")
    args = ap.parse_args()

    run_taylor_scan(fetch_fresh=not args.no_fetch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
