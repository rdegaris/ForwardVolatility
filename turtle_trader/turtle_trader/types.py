from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional

Side = Literal["long", "short"]


@dataclass(frozen=True)
class Bar:
    dt: date
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


@dataclass
class Fill:
    dt: date
    price: float
    qty: int
    side: Side
    reason: str


@dataclass
class Position:
    entry_dt: date
    side: Side
    qty: int
    avg_price: float
    last_add_price: float
    stop_price: float
    units: int


@dataclass
class Trade:
    symbol: str
    entry_dt: date
    entry_price: float
    exit_dt: date
    exit_price: float
    side: Side
    qty: int
    pnl: float
    pnl_after_costs: float
    reason: str
