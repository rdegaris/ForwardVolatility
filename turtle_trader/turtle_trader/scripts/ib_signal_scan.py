from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from turtle_trader.brokers.ib.client import IBClient, IBConfig
from turtle_trader.config import load_config
from turtle_trader.live import compute_levels, compute_unit_qty
from turtle_trader.risk import round_to_tick
from turtle_trader.types import Bar


CLUSTERS: dict[str, set[str]] = {
    "equities": {"ES", "NQ", "RTY"},
    "energies": {"CL", "NG", "HO", "RB"},
    "rates": {"ZB", "ZN", "ZF", "ZT"},
    "metals": {"GC", "SI", "HG"},
    "grains": {"ZC", "ZW", "ZS", "ZL"},
    "softs": {"KC", "SB", "CT"},
    "livestock": {"HE", "LE"},
    "fx": {"EUR", "JPY", "GBP", "CAD", "AUD"},
}


def _cluster_for_symbol(symbol: str) -> str:
    s = (symbol or "").upper()
    for name, symbols in CLUSTERS.items():
        if s in symbols:
            return name
    return "other"


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
    ap.add_argument(
        "--cluster-cap",
        type=int,
        default=3,
        help="Max number of open positions allowed within a correlation cluster",
    )
    ap.add_argument(
        "--skip-positions",
        action="store_true",
        help="Do not query IB open positions (eligibility will be based on unit_qty only)",
    )

    args = ap.parse_args()

    cfg_paths = _load_configs(Path(args.configs_dir))
    if not cfg_paths:
        print(f"No configs found in: {args.configs_dir}")
        return 2

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    try:
        open_symbols: set[str] = set()
        cluster_open_counts: dict[str, int] = {}
        if not args.skip_positions:
            try:
                for pos in client.ib.positions():  # type: ignore[attr-defined]
                    qty = float(getattr(pos, "position", 0) or 0)
                    if qty == 0:
                        continue
                    contract = getattr(pos, "contract", None)
                    sym = (getattr(contract, "symbol", None) or "").upper()
                    if sym:
                        open_symbols.add(sym)
                for sym in open_symbols:
                    c = _cluster_for_symbol(sym)
                    cluster_open_counts[c] = cluster_open_counts.get(c, 0) + 1
            except Exception as e:
                print(f"[turtle_scan] positions: unavailable ({type(e).__name__}: {e}); eligibility will ignore open positions")

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

            # Unit sizing uses account starting equity (net liq not fetched in this scan).
            unit_qty = int(compute_unit_qty(cfg, equity=float(cfg.account.starting_equity), N=float(levels.N)))

            long_stop_loss = None
            short_stop_loss = None
            if levels.long_entry is not None:
                long_stop_loss = float(round_to_tick(float(levels.long_entry) - (cfg.account.stop_loss_N * float(levels.N)), cfg.instrument.tick_size))
            if levels.short_entry is not None:
                short_stop_loss = float(round_to_tick(float(levels.short_entry) + (cfg.account.stop_loss_N * float(levels.N)), cfg.instrument.tick_size))

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
                "long_stop_loss": float(long_stop_loss) if long_stop_loss is not None else None,
                "short_stop_loss": float(short_stop_loss) if short_stop_loss is not None else None,
                "unit_qty": int(unit_qty),
                "long_triggered": bool(long_triggered),
                "short_triggered": bool(short_triggered),
            }
            rows.append(row)

            # Triggered list is actionable and side-specific.
            if long_triggered and levels.long_entry is not None and long_stop_loss is not None:
                cluster = _cluster_for_symbol(inst.symbol)
                cluster_open = int(cluster_open_counts.get(cluster, 0))
                cap = int(args.cluster_cap)
                eligible = True
                blocked_reason = None
                if int(unit_qty) <= 0:
                    eligible = False
                    blocked_reason = "unit_qty=0 (risk sizing)"
                elif inst.symbol.upper() in open_symbols:
                    eligible = False
                    blocked_reason = "already open position"
                elif cluster_open >= cap:
                    eligible = False
                    blocked_reason = f"cluster cap reached ({cluster_open}/{cap})"

                triggered.append(
                    {
                        "symbol": inst.symbol,
                        "exchange": inst.exchange,
                        "currency": inst.currency,
                        "side": "long",
                        "asof": str(levels.asof),
                        "last_close": float(last.close),
                        "entry_stop": float(levels.long_entry),
                        "stop_loss": float(long_stop_loss),
                        "unit_qty": int(unit_qty),
                        "N": float(levels.N),
                        "cluster": cluster,
                        "cluster_open_count": cluster_open,
                        "cluster_cap": cap,
                        "eligible": bool(eligible),
                        "blocked_reason": blocked_reason,
                        "notes": "Breakout hit on latest bar; only an entry if flat + allowed by your rules",
                    }
                )
            if short_triggered and levels.short_entry is not None and short_stop_loss is not None:
                cluster = _cluster_for_symbol(inst.symbol)
                cluster_open = int(cluster_open_counts.get(cluster, 0))
                cap = int(args.cluster_cap)
                eligible = True
                blocked_reason = None
                if int(unit_qty) <= 0:
                    eligible = False
                    blocked_reason = "unit_qty=0 (risk sizing)"
                elif inst.symbol.upper() in open_symbols:
                    eligible = False
                    blocked_reason = "already open position"
                elif cluster_open >= cap:
                    eligible = False
                    blocked_reason = f"cluster cap reached ({cluster_open}/{cap})"

                triggered.append(
                    {
                        "symbol": inst.symbol,
                        "exchange": inst.exchange,
                        "currency": inst.currency,
                        "side": "short",
                        "asof": str(levels.asof),
                        "last_close": float(last.close),
                        "entry_stop": float(levels.short_entry),
                        "stop_loss": float(short_stop_loss),
                        "unit_qty": int(unit_qty),
                        "N": float(levels.N),
                        "cluster": cluster,
                        "cluster_open_count": cluster_open,
                        "cluster_cap": cap,
                        "eligible": bool(eligible),
                        "blocked_reason": blocked_reason,
                        "notes": "Breakout hit on latest bar; only an entry if flat + allowed by your rules",
                    }
                )

        triggered = sorted(triggered, key=lambda r: (r.get("symbol", ""), r.get("side", "")))

        print("\n=== Turtle S2: triggered today (based on last bar high/low vs prior Donchian) ===")
        if not triggered:
            print("(none)")
        else:
            for r in triggered:
                print(
                    f"{r['symbol']:>6} {str(r.get('side','')).upper():<6} asof={r['asof']} close={r['last_close']:.6g} "
                    f"ENTRY={r['entry_stop']:.6g} STOP={r['stop_loss']:.6g} QTY={r['unit_qty']}"
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
