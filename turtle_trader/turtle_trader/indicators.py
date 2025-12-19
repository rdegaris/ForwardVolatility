from __future__ import annotations

from typing import Optional

import numpy as np

from .types import Bar


def true_range(prev_close: float, high: float, low: float) -> float:
    return float(max(high - low, abs(high - prev_close), abs(low - prev_close)))


def atr(bars: list[Bar], period: int) -> list[Optional[float]]:
    """Classic ATR using Wilder's smoothing.

    Returns a list aligned to bars, with None until enough history exists.
    """
    if period <= 0:
        raise ValueError("period must be > 0")
    n = len(bars)
    out: list[Optional[float]] = [None] * n
    if n == 0:
        return out

    tr = np.zeros(n, dtype=float)
    tr[0] = bars[0].high - bars[0].low
    for i in range(1, n):
        tr[i] = true_range(bars[i - 1].close, bars[i].high, bars[i].low)

    if n < period:
        return out

    first_atr = float(np.mean(tr[0:period]))
    out[period - 1] = first_atr

    prev = first_atr
    for i in range(period, n):
        prev = (prev * (period - 1) + float(tr[i])) / period
        out[i] = float(prev)

    return out


def donchian_high(bars: list[Bar], lookback: int) -> list[Optional[float]]:
    """Highest high of the PRIOR lookback bars (excludes current bar)."""
    if lookback <= 0:
        raise ValueError("lookback must be > 0")
    n = len(bars)
    out: list[Optional[float]] = [None] * n
    for i in range(n):
        if i < lookback:
            continue
        window = bars[i - lookback : i]
        out[i] = max(b.high for b in window)
    return out


def donchian_low(bars: list[Bar], lookback: int) -> list[Optional[float]]:
    """Lowest low of the PRIOR lookback bars (excludes current bar)."""
    if lookback <= 0:
        raise ValueError("lookback must be > 0")
    n = len(bars)
    out: list[Optional[float]] = [None] * n
    for i in range(n):
        if i < lookback:
            continue
        window = bars[i - lookback : i]
        out[i] = min(b.low for b in window)
    return out
