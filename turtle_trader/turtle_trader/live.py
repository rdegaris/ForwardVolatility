from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional

from .config import TurtleConfig
from .indicators import atr, donchian_high, donchian_low
from .risk import calc_unit_qty, round_to_tick
from .types import Bar

Side = Literal["long", "short"]


@dataclass(frozen=True)
class SignalLevels:
    asof: date
    N: float
    long_entry: Optional[float]
    short_entry: Optional[float]
    long_exit: Optional[float]
    short_exit: Optional[float]


def compute_levels(cfg: TurtleConfig, bars: list[Bar]) -> SignalLevels:
    """Compute System 2 levels (55/20) as of the latest completed bar.

    The Donchian levels are computed on the PRIOR lookback bars (exclude the current bar),
    matching the classic Turtle definition and the backtest implementation.

    Returns levels to be used as stop orders for the *next* session.
    """
    if not bars:
        raise ValueError("No bars")

    s = cfg.strategy
    inst = cfg.instrument

    if s.system != "S2":
        # We can expand later, but keep live runner strict to your spec.
        raise ValueError("Live runner currently supports System 2 only")

    N_list = atr(bars, s.atr_period)
    N = N_list[-1]
    if N is None:
        raise ValueError("Not enough history for ATR")

    entry_high = donchian_high(bars, s.s2_entry_breakout)[-1]
    entry_low = donchian_low(bars, s.s2_entry_breakout)[-1]

    exit_low = donchian_low(bars, s.s2_exit_breakout)[-1]
    exit_high = donchian_high(bars, s.s2_exit_breakout)[-1]

    # Round levels to instrument tick.
    long_entry = round_to_tick(entry_high, inst.tick_size) if entry_high is not None else None
    short_entry = round_to_tick(entry_low, inst.tick_size) if entry_low is not None else None
    long_exit = round_to_tick(exit_low, inst.tick_size) if exit_low is not None else None
    short_exit = round_to_tick(exit_high, inst.tick_size) if exit_high is not None else None

    return SignalLevels(
        asof=bars[-1].dt,
        N=float(N),
        long_entry=long_entry,
        short_entry=short_entry,
        long_exit=long_exit,
        short_exit=short_exit,
    )


def compute_unit_qty(cfg: TurtleConfig, equity: float, N: float) -> int:
    a = cfg.account
    inst = cfg.instrument
    return calc_unit_qty(
        equity=float(equity),
        risk_per_unit_pct=float(a.risk_per_unit_pct),
        N=float(N),
        point_value=float(inst.point_value),
        stop_loss_N=float(a.stop_loss_N),
    )
