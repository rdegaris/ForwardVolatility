from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SystemName = Literal["S1", "S2"]
Direction = Literal["long", "short", "both"]
SignalContract = Literal["continuous"]
ExecutionContract = Literal["front_month"]


@dataclass(frozen=True)
class AccountConfig:
    starting_equity: float
    risk_per_unit_pct: float
    max_units: int
    pyramid_add_every_N: float
    stop_loss_N: float
    commission_per_contract: float
    slippage_ticks: int


@dataclass(frozen=True)
class InstrumentConfig:
    symbol: str
    point_value: float
    tick_size: float
    exchange: str = "CME"
    currency: str = "USD"

    # Signals computed from continuous futures history; trades executed in a specific contract.
    signal_contract: SignalContract = "continuous"
    execution_contract: ExecutionContract = "front_month"
    roll_days_before_expiry: int = 7
    min_days_to_expiry: int = 10


@dataclass(frozen=True)
class StrategyConfig:
    atr_period: int
    system: SystemName
    s1_entry_breakout: int
    s1_exit_breakout: int
    s2_entry_breakout: int
    s2_exit_breakout: int
    direction: Direction
    skip_winner_s1: bool = False


@dataclass(frozen=True)
class TurtleConfig:
    account: AccountConfig
    instrument: InstrumentConfig
    strategy: StrategyConfig


def load_config(path: str | Path) -> TurtleConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    account = payload["account"]
    instrument = payload["instrument"]
    strategy = payload["strategy"]

    # Backwards/forwards compatible defaults.
    strategy.setdefault("skip_winner_s1", False)

    # Backwards/forwards compatible defaults.
    instrument.setdefault("exchange", "CME")
    instrument.setdefault("currency", "USD")
    instrument.setdefault("signal_contract", "continuous")
    instrument.setdefault("execution_contract", "front_month")
    instrument.setdefault("roll_days_before_expiry", 7)
    instrument.setdefault("min_days_to_expiry", 10)

    return TurtleConfig(
        account=AccountConfig(**account),
        instrument=InstrumentConfig(**instrument),
        strategy=StrategyConfig(**strategy),
    )
