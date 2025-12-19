from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from turtle_trader.brokers.ib.client import IBClient, IBConfig
from turtle_trader.config import TurtleConfig, load_config
from turtle_trader.live import compute_levels, compute_unit_qty
from turtle_trader.state import load_state
from turtle_trader.types import Bar


def _net_liq(ib) -> Optional[float]:
    try:
        rows = ib.accountSummary()
        for r in rows:
            if r.tag == "NetLiquidation" and r.currency == "USD":
                return float(r.value)
    except Exception:
        return None
    return None


def _bars_from_ib_df(df) -> list[Bar]:
    bars: list[Bar] = []
    if df is None or len(df) == 0:
        return bars

    # df columns: date (YYYY-MM-DD), open, high, low, close, volume
    for row in df.itertuples(index=False):
        dt = getattr(row, "date")
        try:
            # date is string
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


def _round_to_tick(px: float, tick: float) -> float:
    if tick <= 0:
        return float(px)
    return round(px / tick) * tick


def _get_position_for_symbol(ib, symbol: str, preferred_conid: Optional[int]) -> tuple[int, Optional[float], Any]:
    """Return (qty, avg_cost, contract) for the best matching IB position."""
    best_qty = 0
    best_avg = None
    best_contract = None

    try:
        positions = ib.positions()
    except Exception:
        return 0, None, None

    # First pass: exact conId match if provided.
    if preferred_conid:
        for p in positions:
            con = getattr(p, "contract", None)
            if getattr(con, "conId", None) == preferred_conid:
                qty = int(getattr(p, "position", 0) or 0)
                if qty != 0:
                    return qty, float(getattr(p, "avgCost", 0.0) or 0.0), con

    # Fallback: any FUT with same symbol.
    for p in positions:
        con = getattr(p, "contract", None)
        if con is None:
            continue
        if getattr(con, "secType", None) != "FUT":
            continue
        if getattr(con, "symbol", None) != symbol:
            continue
        qty = int(getattr(p, "position", 0) or 0)
        if qty == 0:
            continue
        best_qty = qty
        best_avg = float(getattr(p, "avgCost", 0.0) or 0.0)
        best_contract = con
        break

    return best_qty, best_avg, best_contract


def _load_configs(configs_dir: Path) -> list[Path]:
    if not configs_dir.exists():
        return []
    return sorted([p for p in configs_dir.glob("*.json") if p.is_file()])


def _make_suggested_rows(cfg: TurtleConfig, levels, last_close: float, equity: float) -> list[dict[str, Any]]:
    inst = cfg.instrument
    qty_unit = compute_unit_qty(cfg, equity=equity, N=levels.N)

    rows: list[dict[str, Any]] = []

    def add_row(side: str, entry: float):
        if side == "long":
            stop_loss = entry - (cfg.account.stop_loss_N * levels.N)
        else:
            stop_loss = entry + (cfg.account.stop_loss_N * levels.N)

        stop_loss = _round_to_tick(stop_loss, inst.tick_size)

        dist = (entry - last_close) if side == "long" else (last_close - entry)
        dist_n = dist / levels.N if levels.N else None
        pct = (dist / last_close) * 100.0 if last_close else None

        rows.append(
            {
                "symbol": inst.symbol,
                "exchange": inst.exchange,
                "currency": inst.currency,
                "side": side,
                "asof": str(levels.asof),
                "last_close": float(last_close),
                "entry_stop": float(entry),
                "stop_loss": float(stop_loss),
                "unit_qty": int(qty_unit),
                "max_units": int(cfg.account.max_units),
                "N": float(levels.N),
                "distance_to_entry": float(dist),
                "distance_to_entry_N": float(dist_n) if dist_n is not None else None,
                "pct_to_entry": float(pct) if pct is not None else None,
                "notes": "OCA stop entry for next session",
            }
        )

    if qty_unit <= 0:
        return rows

    direction = cfg.strategy.direction
    if direction in ("long", "both") and levels.long_entry is not None:
        add_row("long", float(levels.long_entry))
    if direction in ("short", "both") and levels.short_entry is not None:
        add_row("short", float(levels.short_entry))

    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Export Turtle (S2) JSON payloads for the web app")
    ap.add_argument("--configs-dir", default="configs", help="Directory containing per-instrument config JSONs")
    ap.add_argument("--state", default="out_live/state.json", help="State file (units/last_add_price per symbol)")

    ap.add_argument("--out-suggested", default="turtle_suggested_latest.json")
    ap.add_argument("--out-open", default="turtle_open_trades_latest.json")
    ap.add_argument("--out-triggers", default="turtle_triggers_latest.json")

    ap.add_argument("--trigger-threshold-N", type=float, default=0.75, help="Include triggers with distance_N <= threshold")

    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7498)
    ap.add_argument("--client-id", type=int, default=61)

    ap.add_argument("--duration", default="3 Y", help="IB historical duration for continuous futures")
    ap.add_argument("--use-rth", action="store_true", help="Use regular trading hours only")

    args = ap.parse_args()

    configs_dir = Path(args.configs_dir)
    cfg_paths = _load_configs(configs_dir)
    if not cfg_paths:
        print(f"No configs found in: {configs_dir}")
        print("Create config files like turtle_trader/configs/ES.json")
        return 2

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    try:
        equity = _net_liq(client.ib) or None

        suggested_rows: list[dict[str, Any]] = []
        trigger_rows: list[dict[str, Any]] = []
        open_rows: list[dict[str, Any]] = []

        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        today = datetime.utcnow().date().isoformat()

        for p in cfg_paths:
            cfg = load_config(p)
            inst = cfg.instrument

            print(f"[turtle_export] {inst.symbol}: fetching continuous daily bars ({args.duration})")

            cont = client.cont_future(inst.symbol, exchange=inst.exchange, currency=inst.currency)
            cont = client.qualify(cont)

            try:
                df = client.fetch_daily_bars(cont, duration=args.duration, use_rth=args.use_rth)
            except Exception as e:
                print(f"[turtle_export] {inst.symbol}: failed to fetch history ({type(e).__name__}): {e}")
                continue

            bars = _bars_from_ib_df(df)
            if len(bars) < max(cfg.strategy.s2_entry_breakout, cfg.strategy.atr_period) + 5:
                print(f"Skipping {inst.symbol}: not enough bars ({len(bars)})")
                continue

            levels = compute_levels(cfg, bars)
            last_close = float(bars[-1].close)

            eq = float(equity) if equity is not None else float(cfg.account.starting_equity)
            suggested = _make_suggested_rows(cfg, levels, last_close=last_close, equity=eq)
            suggested_rows.extend(suggested)

            # Triggers soon: choose the closest suggested entry per symbol.
            if suggested:
                best = min(
                    suggested,
                    key=lambda r: float(r.get("distance_to_entry_N") if r.get("distance_to_entry_N") is not None else 999.0),
                )
                dist_n = best.get("distance_to_entry_N")
                if dist_n is not None and float(dist_n) <= float(args.trigger_threshold_N):
                    trigger_rows.append(
                        {
                            "symbol": inst.symbol,
                            "exchange": inst.exchange,
                            "side": best["side"],
                            "asof": str(levels.asof),
                            "last_close": float(last_close),
                            "trigger_price": float(best["entry_stop"]),
                            "distance": float(best.get("distance_to_entry") or 0.0),
                            "distance_N": float(dist_n),
                            "pct_away": float(best.get("pct_to_entry") or 0.0),
                            "notes": "Closest breakout side",
                        }
                    )

            # Open trades: look up front month position + state.
            exec_contract = client.resolve_front_month(
                symbol=inst.symbol,
                exchange=inst.exchange,
                currency=inst.currency,
                min_days_to_expiry=inst.min_days_to_expiry,
            )

            preferred_conid = int(getattr(exec_contract, "conId", 0) or 0) or None
            pos_qty, avg_cost, pos_contract = _get_position_for_symbol(client.ib, inst.symbol, preferred_conid)

            if pos_qty != 0:
                state = load_state(args.state, inst.symbol)
                if state.units == 0:
                    state.units = 1

                side = "long" if pos_qty > 0 else "short"
                abs_qty = abs(int(pos_qty))

                last_add = state.last_add_price if state.last_add_price is not None else last_close

                if side == "long":
                    stop_px = last_add - (cfg.account.stop_loss_N * levels.N)
                    next_add = last_add + (cfg.account.pyramid_add_every_N * levels.N)
                else:
                    stop_px = last_add + (cfg.account.stop_loss_N * levels.N)
                    next_add = last_add - (cfg.account.pyramid_add_every_N * levels.N)

                stop_px = _round_to_tick(stop_px, inst.tick_size)
                next_add = _round_to_tick(next_add, inst.tick_size)

                contract_used = pos_contract or exec_contract

                open_rows.append(
                    {
                        "symbol": inst.symbol,
                        "exchange": inst.exchange,
                        "currency": inst.currency,
                        "contract_local_symbol": getattr(contract_used, "localSymbol", None),
                        "contract_month": getattr(contract_used, "lastTradeDateOrContractMonth", None),
                        "side": side,
                        "qty": int(abs_qty),
                        "avg_price": float(avg_cost or 0.0),
                        "stop_price": float(stop_px),
                        "units": int(state.units),
                        "last_add_price": float(last_add),
                        "next_add_trigger": float(next_add) if state.units < cfg.account.max_units else None,
                        "unrealized_pnl": None,
                        "asof": str(levels.asof),
                    }
                )

        suggested_payload = {
            "timestamp": now,
            "date": today,
            "system": "S2",
            "universe": [load_config(p).instrument.symbol for p in cfg_paths],
            "suggested": suggested_rows,
        }

        open_payload = {
            "timestamp": now,
            "date": today,
            "system": "S2",
            "open_trades": open_rows,
        }

        triggers_payload = {
            "timestamp": now,
            "date": today,
            "system": "S2",
            "threshold_note": f"distance_N <= {args.trigger_threshold_N}",
            "triggers": trigger_rows,
        }

        Path(args.out_suggested).write_text(json.dumps(suggested_payload, indent=2), encoding="utf-8")
        Path(args.out_open).write_text(json.dumps(open_payload, indent=2), encoding="utf-8")
        Path(args.out_triggers).write_text(json.dumps(triggers_payload, indent=2), encoding="utf-8")

        print("Wrote:")
        print(f"  {args.out_suggested}")
        print(f"  {args.out_open}")
        print(f"  {args.out_triggers}")

        return 0

    finally:
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
