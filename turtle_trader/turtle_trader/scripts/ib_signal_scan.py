from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from turtle_trader.brokers.ib.client import IBClient, IBConfig
from turtle_trader.config import load_config
from turtle_trader.live import compute_levels
from turtle_trader.types import Bar


def _bars_from_ib_df(df) -> list[Bar]:
    bars: list[Bar] = []
    if df is None or len(df) == 0:
        return bars

    for row in df.itertuples(index=False):
        dt = getattr(row, "date")
        try:
            d = datetime.strptime(str(dt), "%Y-%m-%d").date()
        except Exception:
            continue
        bars.append(
            Bar(
                dt=d,
                open=float(getattr(row, "open")),
                high=float(getattr(row, "high")),
                low=float(getattr(row, "low")),
                close=float(getattr(row, "close")),
                volume=(float(getattr(row, "volume")) if getattr(row, "volume", None) is not None else None),
            )
        )
    return bars


def _load_configs(configs_dir: Path) -> list[Path]:
    if not configs_dir.exists():
        return []
    return sorted([p for p in configs_dir.glob("*.json") if p.is_file()])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Scan Turtle System 2 (55/20) entry signals from IB continuous futures. "
            "Skips any instruments where IB history is unavailable."
        )
    )
    ap.add_argument("--configs-dir", default="configs", help="Directory containing per-instrument config JSONs")
    ap.add_argument("--duration", default="3 Y", help="IB historical duration for continuous futures")
    ap.add_argument("--use-rth", action="store_true", help="Use regular trading hours only")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7498)
    ap.add_argument("--client-id", type=int, default=62)
    ap.add_argument("--out", default="", help="Optional JSON output path")

    args = ap.parse_args()

    cfg_paths = _load_configs(Path(args.configs_dir))
    if not cfg_paths:
        print(f"No configs found in: {args.configs_dir}")
        return 2

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    try:
        rows: list[dict[str, Any]] = []
        triggered: list[dict[str, Any]] = []

        for p in cfg_paths:
            cfg = load_config(p)
            inst = cfg.instrument

            print(f"[turtle_scan] {inst.symbol}: fetching continuous daily bars ({args.duration})")
            try:
                cont = client.cont_future(inst.symbol, exchange=inst.exchange, currency=inst.currency)
                cont = client.qualify(cont)
                df = client.fetch_daily_bars(cont, duration=args.duration, use_rth=args.use_rth)
            except Exception as e:
                print(f"[turtle_scan] {inst.symbol}: skip (history unavailable: {type(e).__name__}: {e})")
                continue

            bars = _bars_from_ib_df(df)
            if len(bars) < max(cfg.strategy.s2_entry_breakout, cfg.strategy.atr_period) + 5:
                print(f"[turtle_scan] {inst.symbol}: skip (not enough bars: {len(bars)})")
                continue

            levels = compute_levels(cfg, bars)
            last = bars[-1]

            long_triggered = levels.long_entry is not None and last.high >= float(levels.long_entry)
            short_triggered = levels.short_entry is not None and last.low <= float(levels.short_entry)

            row = {
                "symbol": inst.symbol,
                "exchange": inst.exchange,
                "currency": inst.currency,
                "asof": str(levels.asof),
                "N": float(levels.N),
                "last_open": float(last.open),
                "last_high": float(last.high),
                "last_low": float(last.low),
                "last_close": float(last.close),
                "long_entry": float(levels.long_entry) if levels.long_entry is not None else None,
                "short_entry": float(levels.short_entry) if levels.short_entry is not None else None,
                "long_triggered": bool(long_triggered),
                "short_triggered": bool(short_triggered),
            }
            rows.append(row)
            if long_triggered or short_triggered:
                triggered.append(row)

        triggered = sorted(
            triggered,
            key=lambda r: (
                r["symbol"],
                (0 if r.get("long_triggered") else 1),
                (0 if r.get("short_triggered") else 1),
            ),
        )

        print("\n=== Turtle S2: triggered today (based on last bar high/low vs prior Donchian) ===")
        if not triggered:
            print("(none)")
        else:
            for r in triggered:
                sides = "/".join(
                    [s for s, ok in (("LONG", r["long_triggered"]), ("SHORT", r["short_triggered"])) if ok]
                )
                print(
                    f"{r['symbol']:>4} {sides:<10} asof={r['asof']} close={r['last_close']:.6g} "
                    f"LE={r['long_entry'] if r['long_entry'] is not None else 'NA'} "
                    f"SE={r['short_entry'] if r['short_entry'] is not None else 'NA'}"
                )

        if args.out:
            payload = {
                "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "date": datetime.utcnow().date().isoformat(),
                "system": "S2",
                "configs_dir": str(args.configs_dir),
                "duration": str(args.duration),
                "signals": rows,
                "triggered": triggered,
            }
            Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"\nWrote: {args.out}")

        return 0
    finally:
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
