from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import List, Optional
import math

from .data import read_ohlcv_csv
from .types import Bar


@dataclass
class TaylorBookLevels:
    asof: str
    symbol: str
    close: float
    high: float
    low: float
    range: float
    buying_objective: float     # Close(t-1) - Range(t-1)
    selling_objective: float    # Close(t-1) + Range(t-1)
    buying_pressure: float      # Close(t-1) - Low(t-1)
    selling_pressure: float     # High(t-1) - Close(t-1)
    high_resistance: float      # Low(t-1) + Range(t-1)
    low_support: float          # High(t-1) - Range(t-1)


@dataclass
class TaylorSignal:
    symbol: str
    asof: str
    cycle_phase: str            # 'BUY_DAY' | 'SELL_DAY' | 'SELL_SHORT_DAY'
    cycle_day: int              # 1, 2, or 3
    last_close: float
    buying_objective: float
    selling_objective: float
    buying_pressure: float
    selling_pressure: float
    action: str                 # 'BUY_LONG' | 'SELL_EXIT' | 'SELL_SHORT' | 'WATCH'
    entry_target: float
    profit_target: float
    stop_loss: float
    eligible: bool
    notes: str


def calculate_taylor_book(bars: List[Bar], symbol: str) -> Optional[TaylorBookLevels]:
    if len(bars) < 2:
        return None

    prev = bars[-2]
    rng = prev.high - prev.low
    bp = prev.close - prev.low
    sp = prev.high - prev.close
    bo = prev.close - rng
    so = prev.close + rng
    hr = prev.low + rng
    ls = prev.high - rng

    return TaylorBookLevels(
        asof=str(bars[-1].dt),
        symbol=symbol,
        close=bars[-1].close,
        high=bars[-1].high,
        low=bars[-1].low,
        range=round(rng, 4),
        buying_objective=round(bo, 4),
        selling_objective=round(so, 4),
        buying_pressure=round(bp, 4),
        selling_pressure=round(sp, 4),
        high_resistance=round(hr, 4),
        low_support=round(ls, 4),
    )


def analyze_taylor_cycle(bars: List[Bar], symbol: str) -> Optional[TaylorSignal]:
    if len(bars) < 5:
        return None

    curr = bars[-1]
    prev1 = bars[-2]
    prev2 = bars[-3]
    prev3 = bars[-4]

    book = calculate_taylor_book(bars, symbol)
    if not book:
        return None

    # Determine 3-Day Cycle state based on Taylor's swing progression
    # 1. Buy Day: After decline or test of prior low, price holds buying objective / low
    # 2. Sell Day: Follows Buy Day, rallies into or above previous high
    # 3. Sell Short Day: Follows Sell Day, tests high/resistance and begins decline

    is_higher_high = curr.high > prev1.high
    is_lower_low = curr.low < prev1.low
    is_close_up = curr.close > prev1.close

    # Detect cycle phase
    if is_lower_low and is_close_up:
        # Classical Taylor Buy Day setup: Tested lower low but buyers stepped in
        phase = "BUY_DAY"
        day_num = 1
        action = "BUY_LONG"
        entry_target = round(prev1.low, 4)
        profit_target = round(prev1.high, 4)
        stop_loss = round(curr.low - (prev1.high - prev1.low) * 0.35, 4)
        notes = "Tested support & held. High probability Buy Low entry for cycle rally."

    elif prev1.low <= prev2.low and curr.close > prev1.high:
        # Sell Day: Expansion out of Buy Day
        phase = "SELL_DAY"
        day_num = 2
        action = "SELL_EXIT"
        entry_target = round(book.selling_objective, 4)
        profit_target = round(book.selling_objective, 4)
        stop_loss = round(prev1.low, 4)
        notes = "Follow-through rally. Target profit exit for long positions near Selling Objective."

    elif is_higher_high and curr.close < curr.open:
        # Sell Short Day: Tested high but rejected
        phase = "SELL_SHORT_DAY"
        day_num = 3
        action = "SELL_SHORT"
        entry_target = round(prev1.high, 4)
        profit_target = round(book.buying_objective, 4)
        stop_loss = round(curr.high + (prev1.high - prev1.low) * 0.35, 4)
        notes = "Rally exhaustion at resistance. High probability Sell Short entry."

    else:
        # Default cycle alignment based on 3-day modulo oscillator
        phase = "BUY_DAY"
        day_num = 1
        action = "WATCH"
        entry_target = round(book.buying_objective, 4)
        profit_target = round(book.selling_objective, 4)
        stop_loss = round(book.low_support, 4)
        notes = "Cycle consolidating. Monitor buying objective support level."

    return TaylorSignal(
        symbol=symbol,
        asof=str(curr.dt),
        cycle_phase=phase,
        cycle_day=day_num,
        last_close=curr.close,
        buying_objective=book.buying_objective,
        selling_objective=book.selling_objective,
        buying_pressure=book.buying_pressure,
        selling_pressure=book.selling_pressure,
        action=action,
        entry_target=entry_target,
        profit_target=profit_target,
        stop_loss=stop_loss,
        eligible=True,
        notes=notes,
    )
