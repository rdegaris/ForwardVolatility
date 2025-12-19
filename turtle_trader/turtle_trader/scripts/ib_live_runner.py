from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from ib_insync import MarketOrder, StopOrder

from turtle_trader.brokers.ib.client import IBClient, IBConfig
from turtle_trader.config import load_config
from turtle_trader.data import read_ohlcv_csv
from turtle_trader.live import compute_levels, compute_unit_qty
from turtle_trader.state import TurtleLiveState, load_state, save_state


def _net_liq(ib) -> Optional[float]:
    try:
        rows = ib.accountSummary()
        for r in rows:
            if r.tag == "NetLiquidation" and r.currency == "USD":
                return float(r.value)
    except Exception:
        return None
    return None


def _position_size_for_contract(ib, con_id: int) -> int:
    qty = 0
    try:
        for p in ib.positions():
            if getattr(p.contract, "conId", None) == con_id:
                qty += int(p.position)
    except Exception:
        return 0
    return qty


def main() -> int:
    ap = argparse.ArgumentParser(description="Turtle System 2 live runner (signals on continuous, execute front-month)")
    ap.add_argument("--config", required=True, help="Config JSON")
    ap.add_argument("--signal-csv", required=True, help="CSV used for signals (continuous series)")
    ap.add_argument("--state", default="out_live/state.json", help="State file to track pyramids")

    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7498)
    ap.add_argument("--client-id", type=int, default=51)

    ap.add_argument("--dry-run", action="store_true", help="Print actions only (default)")
    ap.add_argument("--live", action="store_true", help="Actually place/cancel orders")

    args = ap.parse_args()

    cfg = load_config(args.config)
    inst = cfg.instrument

    if not args.dry_run and not args.live:
        # Safe default: dry-run.
        args.dry_run = True

    # Signals on continuous series.
    bars = read_ohlcv_csv(args.signal_csv)
    levels = compute_levels(cfg, bars)

    state_path = Path(args.state)
    state = load_state(state_path, inst.symbol)

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    try:
        # Execution contract: front-month.
        exec_contract = client.resolve_front_month(
            symbol=inst.symbol,
            exchange=inst.exchange,
            currency=inst.currency,
            min_days_to_expiry=inst.min_days_to_expiry,
        )

        equity = _net_liq(client.ib) or cfg.account.starting_equity
        qty_unit = compute_unit_qty(cfg, equity=equity, N=levels.N)

        pos_qty = _position_size_for_contract(client.ib, int(getattr(exec_contract, "conId", 0) or 0))

        print("Turtle Live Runner (System 2)")
        print(f"  asof: {levels.asof}")
        print(f"  symbol: {inst.symbol}  exchange: {inst.exchange}")
        print(f"  execution: {getattr(exec_contract, 'localSymbol', None)}  conId={getattr(exec_contract, 'conId', None)}")
        print(f"  N: {levels.N:.4f}  unit_qty: {qty_unit}  equity: {equity:,.2f}")
        print(f"  position_qty: {pos_qty}")
        print(f"  levels: {asdict(levels)}")

        if qty_unit <= 0:
            print("  No orders: unit_qty computed as 0")
            return 0

        # Simple state initialization if we currently have a position but no state.
        if pos_qty != 0 and state.units == 0:
            state.units = 1
            state.last_add_price = None

        if pos_qty == 0:
            # Place entry stop(s) for next session. For 'both', place OCA group.
            oca_group = f"TURTLE_{inst.symbol}_ENTRY"

            orders = []

            if cfg.strategy.direction in ("long", "both") and levels.long_entry is not None:
                entry = StopOrder("BUY", qty_unit, levels.long_entry, transmit=False)
                entry.ocaGroup = oca_group
                entry.ocaType = 1

                stop_px = levels.long_entry - (cfg.account.stop_loss_N * levels.N)
                stop_px = round(stop_px / inst.tick_size) * inst.tick_size
                stop = StopOrder("SELL", qty_unit, stop_px, transmit=True)

                orders.append((entry, stop, "enter_long"))

            if cfg.strategy.direction in ("short", "both") and levels.short_entry is not None:
                entry = StopOrder("SELL", qty_unit, levels.short_entry, transmit=False)
                entry.ocaGroup = oca_group
                entry.ocaType = 1

                stop_px = levels.short_entry + (cfg.account.stop_loss_N * levels.N)
                stop_px = round(stop_px / inst.tick_size) * inst.tick_size
                stop = StopOrder("BUY", qty_unit, stop_px, transmit=True)

                orders.append((entry, stop, "enter_short"))

            if not orders:
                print("  No entry orders: missing levels")
                return 0

            print("Planned entry orders:")
            for entry, stop, label in orders:
                print(f"  {label}: entry_stop={entry.auxPrice} stop_loss={stop.auxPrice} qty={qty_unit}")

            if args.live:
                # Attach stop-loss orders as children of the entry order.
                for entry, stop, _ in orders:
                    trade = client.ib.placeOrder(exec_contract, entry)
                    client.ib.sleep(0.2)
                    stop.parentId = trade.order.orderId
                    stop.transmit = True
                    client.ib.placeOrder(exec_contract, stop)

            # Reset state when flat.
            state.units = 0
            state.last_add_price = None
            save_state(state_path, state)
            return 0

        # In-position management (baseline): ensure we have a protective stop and an optional pyramid add.
        side = "long" if pos_qty > 0 else "short"
        abs_qty = abs(pos_qty)

        last_add = state.last_add_price
        if last_add is None:
            # Conservative default: treat current price as last add for stop placement.
            last_add = bars[-1].close

        if side == "long":
            stop_px = last_add - (cfg.account.stop_loss_N * levels.N)
            stop_px = round(stop_px / inst.tick_size) * inst.tick_size
            stop_order = StopOrder("SELL", abs_qty, stop_px, transmit=True)
            print(f"Planned protective stop (long): {stop_px} qty={abs_qty}")
        else:
            stop_px = last_add + (cfg.account.stop_loss_N * levels.N)
            stop_px = round(stop_px / inst.tick_size) * inst.tick_size
            stop_order = StopOrder("BUY", abs_qty, stop_px, transmit=True)
            print(f"Planned protective stop (short): {stop_px} qty={abs_qty}")

        add_order = None
        if state.units < cfg.account.max_units:
            add_trigger = last_add + (cfg.account.pyramid_add_every_N * levels.N) if side == "long" else last_add - (cfg.account.pyramid_add_every_N * levels.N)
            add_trigger = round(add_trigger / inst.tick_size) * inst.tick_size
            if side == "long":
                add_order = StopOrder("BUY", qty_unit, add_trigger, transmit=True)
                print(f"Planned pyramid add (long): {add_trigger} qty={qty_unit}")
            else:
                add_order = StopOrder("SELL", qty_unit, add_trigger, transmit=True)
                print(f"Planned pyramid add (short): {add_trigger} qty={qty_unit}")

        if args.live:
            # NOTE: For safety, we are not auto-canceling/replacing existing orders yet.
            # Tomorrow, run in dry-run first, then manually confirm/cancel old orders.
            client.ib.placeOrder(exec_contract, stop_order)
            if add_order is not None:
                client.ib.placeOrder(exec_contract, add_order)

        # Persist basic state.
        state.units = max(state.units, 1)
        state.last_add_price = float(last_add)
        save_state(state_path, state)

        return 0

    finally:
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
