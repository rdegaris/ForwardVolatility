from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from turtle_trader.brokers.ib.client import IBClient, IBConfig
from turtle_trader.config import load_config
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


def _is_outside(day: Bar, prev_day: Bar) -> bool:
    return day.high > prev_day.high and day.low < prev_day.low


def _is_inside(day: Bar, container_day: Bar) -> bool:
    return day.high < container_day.high and day.low > container_day.low


def _get_open_fut_positions(ib, universe: set[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        positions = ib.positions()
    except Exception:
        return out

    for p in positions:
        con = getattr(p, "contract", None)
        if con is None:
            continue
        if getattr(con, "secType", None) != "FUT":
            continue

        sym = (getattr(con, "symbol", "") or "").upper()
        if not sym or (universe and sym not in universe):
            continue

        qty = int(getattr(p, "position", 0) or 0)
        if qty == 0:
            continue

        out[sym] = {
            "symbol": sym,
            "exchange": getattr(con, "exchange", "") or "",
            "currency": getattr(con, "currency", "") or "",
            "contract_local_symbol": getattr(con, "localSymbol", None),
            "contract_month": getattr(con, "lastTradeDateOrContractMonth", None),
            "side": "long" if qty > 0 else "short",
            "qty": abs(qty),
            "net_qty": qty,
            "avg_price": float(getattr(p, "avgCost", 0.0) or 0.0),
        }
    return out


def _round(v: float | None, digits: int = 6) -> float | None:
    if v is None:
        return None
    return round(float(v), digits)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Scan OD/ID breakout setups from IB continuous futures. "
            "Pattern: outside day followed by inside day, then breakout close above/below OD range."
        )
    )
    ap.add_argument("--configs-dir", default="configs", help="Directory containing per-instrument config JSONs")
    ap.add_argument("--duration", default="1 Y", help="IB historical duration")
    ap.add_argument("--use-rth", action="store_true", help="Use regular trading hours only")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7498)
    ap.add_argument("--client-id", type=int, default=64)
    ap.add_argument("--arm-alert-pct", type=float, default=1.0, help="Alert when armed setup is within this percent of breakout level")
    ap.add_argument("--out-signals", default="", help="Optional OD/ID signals JSON output path")
    ap.add_argument("--out-alerts", default="", help="Optional OD/ID alerts JSON output path")
    ap.add_argument("--out-open", default="", help="Optional OD/ID open trades JSON output path")

    args = ap.parse_args()

    cfg_paths = _load_configs(Path(args.configs_dir))
    if not cfg_paths:
        print(f"No configs found in: {args.configs_dir}")
        return 2

    universe_symbols: set[str] = set()
    instrument_cfg: dict[str, dict[str, str]] = {}
    for p in cfg_paths:
        cfg = load_config(p)
        sym = cfg.instrument.symbol.upper()
        universe_symbols.add(sym)
        instrument_cfg[sym] = {
            "exchange": cfg.instrument.exchange,
            "currency": cfg.instrument.currency,
        }

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()

    try:
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        today = datetime.utcnow().date().isoformat()

        open_positions = _get_open_fut_positions(client.ib, universe_symbols)
        open_rows = sorted(open_positions.values(), key=lambda r: str(r.get("symbol", "")))

        rows: list[dict[str, Any]] = []
        triggered: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []

        for p in cfg_paths:
            cfg = load_config(p)
            inst = cfg.instrument

            print(f"[odid_scan] {inst.symbol}: fetching continuous daily bars ({args.duration})")
            try:
                cont = client.cont_future(inst.symbol, exchange=inst.exchange, currency=inst.currency)
                cont = client.qualify(cont)
                df = client.fetch_daily_bars(cont, duration=args.duration, use_rth=args.use_rth)
            except Exception as e:
                print(f"[odid_scan] {inst.symbol}: skip (history unavailable: {type(e).__name__}: {e})")
                continue

            bars = _bars_from_ib_df(df)
            if len(bars) < 5:
                print(f"[odid_scan] {inst.symbol}: skip (not enough bars: {len(bars)})")
                continue

            last = bars[-1]
            prev = bars[-2]
            prev2 = bars[-3]
            prev3 = bars[-4]

            odid_armed = _is_outside(prev, prev2) and _is_inside(last, prev)
            armed_up = prev.high if odid_armed else None
            armed_down = prev.low if odid_armed else None

            odid_breakout_window = _is_outside(prev2, prev3) and _is_inside(prev, prev2)
            breakout_side = None
            breakout_entry = None
            breakout_stop = None
            breakout_ref_od_date = None
            breakout_ref_id_date = None

            if odid_breakout_window:
                breakout_ref_od_date = str(prev2.dt)
                breakout_ref_id_date = str(prev.dt)
                if last.close > prev2.high:
                    breakout_side = "long"
                    breakout_entry = prev2.high
                    breakout_stop = prev2.low
                elif last.close < prev2.low:
                    breakout_side = "short"
                    breakout_entry = prev2.low
                    breakout_stop = prev2.high

            dist_up_pct = None
            dist_down_pct = None
            if armed_up and last.close:
                dist_up_pct = abs((armed_up - last.close) / last.close) * 100.0
            if armed_down and last.close:
                dist_down_pct = abs((last.close - armed_down) / last.close) * 100.0

            sym = inst.symbol.upper()
            open_pos = open_positions.get(sym)
            has_open_position = open_pos is not None

            row = {
                "symbol": sym,
                "exchange": inst.exchange,
                "currency": inst.currency,
                "cluster": _cluster_for_symbol(sym),
                "asof": str(last.dt),
                "last_open": _round(last.open),
                "last_high": _round(last.high),
                "last_low": _round(last.low),
                "last_close": _round(last.close),
                "odid_setup_armed": bool(odid_armed),
                "armed_od_date": str(prev.dt) if odid_armed else None,
                "armed_id_date": str(last.dt) if odid_armed else None,
                "armed_breakout_up": _round(armed_up),
                "armed_breakout_down": _round(armed_down),
                "distance_to_up_pct": _round(dist_up_pct, 3),
                "distance_to_down_pct": _round(dist_down_pct, 3),
                "breakout_window": bool(odid_breakout_window),
                "breakout_confirmed": breakout_side is not None,
                "breakout_side": breakout_side,
                "breakout_entry": _round(breakout_entry),
                "breakout_stop": _round(breakout_stop),
                "breakout_od_date": breakout_ref_od_date,
                "breakout_id_date": breakout_ref_id_date,
                "has_open_position": has_open_position,
                "open_position_qty": int(open_pos["net_qty"]) if open_pos else 0,
            }
            rows.append(row)

            if breakout_side is not None:
                eligible = not has_open_position
                blocked_reason = "already open position" if has_open_position else None

                trig = {
                    "symbol": sym,
                    "exchange": inst.exchange,
                    "currency": inst.currency,
                    "cluster": _cluster_for_symbol(sym),
                    "side": breakout_side,
                    "asof": str(last.dt),
                    "od_date": breakout_ref_od_date,
                    "id_date": breakout_ref_id_date,
                    "last_close": _round(last.close),
                    "entry_stop": _round(breakout_entry),
                    "stop_loss": _round(breakout_stop),
                    "eligible": eligible,
                    "blocked_reason": blocked_reason,
                    "notes": "Close confirmed outside day range after OD/ID setup",
                }
                triggered.append(trig)

                alerts.append(
                    {
                        "symbol": sym,
                        "severity": "high",
                        "type": "breakout_confirmed",
                        "side": breakout_side,
                        "asof": str(last.dt),
                        "message": (
                            f"OD/ID breakout confirmed {breakout_side.upper()}: close {last.close:.4f} "
                            f"vs level {breakout_entry:.4f}"
                        ),
                        "entry_stop": _round(breakout_entry),
                        "stop_loss": _round(breakout_stop),
                        "eligible": eligible,
                        "blocked_reason": blocked_reason,
                    }
                )

            if odid_armed and armed_up is not None and armed_down is not None:
                best_dist = min(x for x in [dist_up_pct, dist_down_pct] if x is not None)
                if best_dist <= float(args.arm_alert_pct):
                    side_hint = "long" if (dist_up_pct or 999.0) <= (dist_down_pct or 999.0) else "short"
                    target_level = armed_up if side_hint == "long" else armed_down
                    alerts.append(
                        {
                            "symbol": sym,
                            "severity": "medium",
                            "type": "setup_armed",
                            "side": side_hint,
                            "asof": str(last.dt),
                            "message": (
                                f"OD/ID setup armed, {best_dist:.2f}% from {side_hint.upper()} breakout "
                                f"level {target_level:.4f}"
                            ),
                            "entry_stop": _round(target_level),
                            "stop_loss": _round(armed_down if side_hint == "long" else armed_up),
                            "eligible": not has_open_position,
                            "blocked_reason": "already open position" if has_open_position else None,
                        }
                    )

        rows = sorted(rows, key=lambda r: str(r.get("symbol", "")))
        triggered = sorted(triggered, key=lambda r: (str(r.get("symbol", "")), str(r.get("side", ""))))
        alerts = sorted(alerts, key=lambda r: (0 if r.get("severity") == "high" else 1, str(r.get("symbol", ""))))

        print("\n=== OD/ID Breakout Summary ===")
        print(f"Total scanned: {len(rows)}")
        print(f"Setups armed: {sum(1 for r in rows if r.get('odid_setup_armed'))}")
        print(f"Breakouts confirmed: {len(triggered)}")
        print(f"Open futures positions: {len(open_rows)}")
        print(f"Alerts: {len(alerts)}")

        if triggered:
            print("\n--- BREAKOUTS CONFIRMED ---")
            for r in triggered:
                side = str(r.get("side", "")).upper()
                print(
                    f"{r['symbol']:>6} {side:<5} "
                    f"close={r['last_close']:.4f} entry={r['entry_stop']:.4f} stop={r['stop_loss']:.4f} "
                    f"eligible={'Y' if r.get('eligible') else 'N'}"
                )

        signals_payload = {
            "timestamp": now,
            "date": today,
            "system": "odid",
            "pattern": "outside-day-inside-day-breakout",
            "arm_alert_pct": float(args.arm_alert_pct),
            "total_scanned": len(rows),
            "total_armed": sum(1 for r in rows if r.get("odid_setup_armed")),
            "total_triggered": len(triggered),
            "signals": rows,
            "triggered": triggered,
        }

        alerts_payload = {
            "timestamp": now,
            "date": today,
            "system": "odid",
            "total_alerts": len(alerts),
            "alerts": alerts,
        }

        open_payload = {
            "timestamp": now,
            "date": today,
            "system": "odid",
            "open_trades": open_rows,
        }

        if args.out_signals:
            Path(args.out_signals).write_text(json.dumps(signals_payload, indent=2), encoding="utf-8")
            print(f"Wrote: {args.out_signals}")
        if args.out_alerts:
            Path(args.out_alerts).write_text(json.dumps(alerts_payload, indent=2), encoding="utf-8")
            print(f"Wrote: {args.out_alerts}")
        if args.out_open:
            Path(args.out_open).write_text(json.dumps(open_payload, indent=2), encoding="utf-8")
            print(f"Wrote: {args.out_open}")

        return 0
    finally:
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
