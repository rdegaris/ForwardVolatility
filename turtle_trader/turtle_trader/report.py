from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .types import Trade


@dataclass(frozen=True)
class Summary:
    starting_equity: float
    ending_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_daily: float
    trades: int
    win_rate_pct: float
    profit_factor: float


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return float(dd.min())


def summarize(equity_curve: pd.DataFrame, trades: list[Trade], starting_equity: float) -> Summary:
    eq = equity_curve["equity"].astype(float)
    ending = float(eq.iloc[-1]) if len(eq) else float(starting_equity)

    rets = eq.pct_change().fillna(0.0)
    vol = float(rets.std(ddof=0))
    mean = float(rets.mean())
    sharpe = (mean / vol) * np.sqrt(252.0) if vol > 0 else 0.0

    mdd = _max_drawdown(eq)

    wins = [t for t in trades if t.pnl_after_costs > 0]
    losses = [t for t in trades if t.pnl_after_costs < 0]
    win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
    gross_win = sum(t.pnl_after_costs for t in wins)
    gross_loss = -sum(t.pnl_after_costs for t in losses)
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0

    total_return = (ending / float(starting_equity) - 1.0) * 100.0

    return Summary(
        starting_equity=float(starting_equity),
        ending_equity=ending,
        total_return_pct=float(total_return),
        max_drawdown_pct=float(mdd * 100.0),
        sharpe_daily=float(sharpe),
        trades=int(len(trades)),
        win_rate_pct=float(win_rate),
        profit_factor=float(profit_factor),
    )
