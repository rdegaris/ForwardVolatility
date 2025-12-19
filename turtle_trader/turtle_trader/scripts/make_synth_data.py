from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def make_synth(start: date, days: int, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Regime-switching random walk to get occasional trends.
    prices = []
    px = 100.0
    drift = 0.0002
    vol = 0.012

    for i in range(days):
        if i % 120 == 0 and i > 0:
            drift = rng.normal(0.0002, 0.0008)
            vol = abs(rng.normal(0.012, 0.006))

        ret = drift + vol * rng.normal()
        px = max(1.0, px * (1.0 + ret))
        prices.append(px)

    closes = np.array(prices)
    # Build OHLC around close.
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    intraday = np.maximum(0.002, np.abs(rng.normal(0.004, 0.002, size=days)))
    highs = np.maximum(opens, closes) * (1.0 + intraday)
    lows = np.minimum(opens, closes) * (1.0 - intraday)

    dates = [start + timedelta(days=i) for i in range(days)]
    df = pd.DataFrame({
        "date": [d.isoformat() for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": rng.integers(1000, 5000, size=days),
    })

    # Keep only weekdays for a cleaner daily series.
    df["_dt"] = pd.to_datetime(df["date"])
    df = df[df["_dt"].dt.weekday < 5].drop(columns=["_dt"]).reset_index(drop=True)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    days = int(args.years * 365)
    df = make_synth(date(2015, 1, 1), days=days, seed=args.seed)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
