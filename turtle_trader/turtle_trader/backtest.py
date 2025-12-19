from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .config import TurtleConfig
from .indicators import atr, donchian_high, donchian_low
from .risk import calc_unit_qty, round_to_tick
from .types import Bar, Position, Trade


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.DataFrame  # columns: date,equity


def _commission_total(commission_per_contract: float, qty: int) -> float:
    return float(commission_per_contract) * abs(int(qty))


def run_backtest(cfg: TurtleConfig, bars: list[Bar]) -> BacktestResult:
    s = cfg.strategy
    a = cfg.account
    inst = cfg.instrument

    entry_lb = s.s1_entry_breakout if s.system == "S1" else s.s2_entry_breakout
    exit_lb = s.s1_exit_breakout if s.system == "S1" else s.s2_exit_breakout

    N_list = atr(bars, s.atr_period)
    hh = donchian_high(bars, entry_lb)
    ll = donchian_low(bars, entry_lb)
    exit_hh = donchian_high(bars, exit_lb)
    exit_ll = donchian_low(bars, exit_lb)

    equity = float(a.starting_equity)
    position: Optional[Position] = None
    trades: list[Trade] = []

    # For the classic S1 "skip winners" rule: if last breakout in a direction was profitable,
    # skip the next entry signal in that same direction.
    last_breakout_was_winner = {"long": False, "short": False}

    curve_rows: list[dict] = []

    def mark_to_market(bar: Bar) -> float:
        nonlocal equity
        if not position:
            return equity
        if position.side == "long":
            return equity + (bar.close - position.avg_price) * position.qty * inst.point_value
        return equity + (position.avg_price - bar.close) * position.qty * inst.point_value

    for i, bar in enumerate(bars):
        N = N_list[i]
        curve_rows.append({"date": bar.dt, "equity": mark_to_market(bar)})

        if N is None:
            continue

        # --- Manage open position (exits / stops / pyramids)
        if position is not None:
            # Stop loss is evaluated first (intraday)
            if position.side == "long" and bar.low <= position.stop_price:
                fill_price = round_to_tick(position.stop_price, inst.tick_size)
                pnl = (fill_price - position.avg_price) * position.qty * inst.point_value
                costs = _commission_total(a.commission_per_contract, position.qty) + _commission_total(
                    a.commission_per_contract, position.qty
                )
                equity += pnl - costs
                last_breakout_was_winner["long"] = (pnl - costs) > 0
                trades.append(
                    Trade(
                        symbol=inst.symbol,
                        entry_dt=position.entry_dt,
                        entry_price=position.avg_price,
                        exit_dt=bar.dt,
                        exit_price=fill_price,
                        side=position.side,
                        qty=position.qty,
                        pnl=float(pnl),
                        pnl_after_costs=float(pnl - costs),
                        reason="stop",
                    )
                )
                position = None
                continue

            if position.side == "short" and bar.high >= position.stop_price:
                fill_price = round_to_tick(position.stop_price, inst.tick_size)
                pnl = (position.avg_price - fill_price) * position.qty * inst.point_value
                costs = _commission_total(a.commission_per_contract, position.qty) + _commission_total(
                    a.commission_per_contract, position.qty
                )
                equity += pnl - costs
                last_breakout_was_winner["short"] = (pnl - costs) > 0
                trades.append(
                    Trade(
                        symbol=inst.symbol,
                        entry_dt=position.entry_dt,
                        entry_price=position.avg_price,
                        exit_dt=bar.dt,
                        exit_price=fill_price,
                        side=position.side,
                        qty=position.qty,
                        pnl=float(pnl),
                        pnl_after_costs=float(pnl - costs),
                        reason="stop",
                    )
                )
                position = None
                continue

            # Channel exit
            if position.side == "long" and exit_ll[i] is not None and bar.low <= exit_ll[i]:
                fill_price = round_to_tick(exit_ll[i], inst.tick_size)
                pnl = (fill_price - position.avg_price) * position.qty * inst.point_value
                costs = _commission_total(a.commission_per_contract, position.qty) + _commission_total(
                    a.commission_per_contract, position.qty
                )
                equity += pnl - costs
                last_breakout_was_winner["long"] = (pnl - costs) > 0
                trades.append(
                    Trade(
                        symbol=inst.symbol,
                        entry_dt=position.entry_dt,
                        entry_price=position.avg_price,
                        exit_dt=bar.dt,
                        exit_price=fill_price,
                        side=position.side,
                        qty=position.qty,
                        pnl=float(pnl),
                        pnl_after_costs=float(pnl - costs),
                        reason="channel_exit",
                    )
                )
                position = None
                continue

            if position.side == "short" and exit_hh[i] is not None and bar.high >= exit_hh[i]:
                fill_price = round_to_tick(exit_hh[i], inst.tick_size)
                pnl = (position.avg_price - fill_price) * position.qty * inst.point_value
                costs = _commission_total(a.commission_per_contract, position.qty) + _commission_total(
                    a.commission_per_contract, position.qty
                )
                equity += pnl - costs
                last_breakout_was_winner["short"] = (pnl - costs) > 0
                trades.append(
                    Trade(
                        symbol=inst.symbol,
                        entry_dt=position.entry_dt,
                        entry_price=position.avg_price,
                        exit_dt=bar.dt,
                        exit_price=fill_price,
                        side=position.side,
                        qty=position.qty,
                        pnl=float(pnl),
                        pnl_after_costs=float(pnl - costs),
                        reason="channel_exit",
                    )
                )
                position = None
                continue

            # Pyramiding (add every 0.5N)
            if position.units < a.max_units:
                add_trigger = position.last_add_price + (a.pyramid_add_every_N * N) if position.side == "long" else position.last_add_price - (a.pyramid_add_every_N * N)
                if position.side == "long" and bar.high >= add_trigger:
                    qty_unit = calc_unit_qty(equity, a.risk_per_unit_pct, N, inst.point_value, a.stop_loss_N)
                    if qty_unit > 0:
                        fill = round_to_tick(add_trigger, inst.tick_size)
                        new_qty = position.qty + qty_unit
                        position.avg_price = (position.avg_price * position.qty + fill * qty_unit) / new_qty
                        position.qty = new_qty
                        position.units += 1
                        position.last_add_price = fill
                        position.stop_price = round_to_tick(fill - (a.stop_loss_N * N), inst.tick_size)
                elif position.side == "short" and bar.low <= add_trigger:
                    qty_unit = calc_unit_qty(equity, a.risk_per_unit_pct, N, inst.point_value, a.stop_loss_N)
                    if qty_unit > 0:
                        fill = round_to_tick(add_trigger, inst.tick_size)
                        new_qty = position.qty + qty_unit
                        position.avg_price = (position.avg_price * position.qty + fill * qty_unit) / new_qty
                        position.qty = new_qty
                        position.units += 1
                        position.last_add_price = fill
                        position.stop_price = round_to_tick(fill + (a.stop_loss_N * N), inst.tick_size)

            continue

        # --- No position: check entries
        can_long = s.direction in ("long", "both")
        can_short = s.direction in ("short", "both")

        qty_unit = calc_unit_qty(equity, a.risk_per_unit_pct, N, inst.point_value, a.stop_loss_N)
        if qty_unit <= 0:
            continue

        skip_winners = bool(getattr(s, "skip_winner_s1", False)) and s.system == "S1"

        # Long breakout
        if can_long and hh[i] is not None and bar.high >= hh[i]:
            if skip_winners and last_breakout_was_winner["long"]:
                continue
            entry = round_to_tick(hh[i], inst.tick_size)
            stop = round_to_tick(entry - (a.stop_loss_N * N), inst.tick_size)
            position = Position(
                entry_dt=bar.dt,
                side="long",
                qty=qty_unit,
                avg_price=entry,
                last_add_price=entry,
                stop_price=stop,
                units=1,
            )
            continue

        # Short breakout
        if can_short and ll[i] is not None and bar.low <= ll[i]:
            if skip_winners and last_breakout_was_winner["short"]:
                continue
            entry = round_to_tick(ll[i], inst.tick_size)
            stop = round_to_tick(entry + (a.stop_loss_N * N), inst.tick_size)
            position = Position(
                entry_dt=bar.dt,
                side="short",
                qty=qty_unit,
                avg_price=entry,
                last_add_price=entry,
                stop_price=stop,
                units=1,
            )
            continue

    equity_curve = pd.DataFrame(curve_rows)
    return BacktestResult(trades=trades, equity_curve=equity_curve)
