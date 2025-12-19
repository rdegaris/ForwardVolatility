from __future__ import annotations

import math


def round_to_tick(price: float, tick_size: float) -> float:
    if tick_size <= 0:
        return price
    return round(price / tick_size) * tick_size


def calc_unit_qty(
    equity: float,
    risk_per_unit_pct: float,
    N: float,
    point_value: float,
    stop_loss_N: float,
) -> int:
    """Contracts per unit sized to the configured stop distance.

    Classic Turtle sizing risks ~1% of equity per unit, using a stop at 2N.
    Per-contract $ risk is (stop_loss_N * N * point_value).
    """
    if (
        equity <= 0
        or risk_per_unit_pct <= 0
        or N is None
        or N <= 0
        or point_value <= 0
        or stop_loss_N is None
        or stop_loss_N <= 0
    ):
        return 0

    dollar_risk = equity * risk_per_unit_pct
    per_contract_risk = (stop_loss_N * N) * point_value
    qty = int(math.floor(dollar_risk / per_contract_risk))
    return max(qty, 0)
