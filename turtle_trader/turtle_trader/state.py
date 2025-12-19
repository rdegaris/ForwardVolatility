from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TurtleLiveState:
    symbol: str
    units: int = 0
    last_add_price: Optional[float] = None


def load_state(path: str | Path, symbol: str) -> TurtleLiveState:
    p = Path(path)
    if not p.exists():
        return TurtleLiveState(symbol=symbol)
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return TurtleLiveState(symbol=symbol)

    s = payload.get(symbol, {}) if isinstance(payload, dict) else {}
    if not isinstance(s, dict):
        return TurtleLiveState(symbol=symbol)

    return TurtleLiveState(
        symbol=symbol,
        units=int(s.get("units", 0) or 0),
        last_add_price=(float(s["last_add_price"]) if s.get("last_add_price") is not None else None),
    )


def save_state(path: str | Path, state: TurtleLiveState) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    payload = {}
    if p.exists():
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    if not isinstance(payload, dict):
        payload = {}

    payload[state.symbol] = {
        "units": int(state.units),
        "last_add_price": float(state.last_add_price) if state.last_add_price is not None else None,
    }

    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
