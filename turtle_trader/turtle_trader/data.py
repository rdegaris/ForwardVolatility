from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from .types import Bar


@dataclass(frozen=True)
class CsvSchema:
    date_col: str = "date"
    open_col: str = "open"
    high_col: str = "high"
    low_col: str = "low"
    close_col: str = "close"
    volume_col: str = "volume"


def read_ohlcv_csv(path: str | Path, schema: Optional[CsvSchema] = None) -> list[Bar]:
    schema = schema or CsvSchema()
    df = pd.read_csv(Path(path))

    required = [schema.date_col, schema.open_col, schema.high_col, schema.low_col, schema.close_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df = df.sort_values(schema.date_col).reset_index(drop=True)

    bars: list[Bar] = []
    for _, row in df.iterrows():
        dt = datetime.strptime(str(row[schema.date_col])[:10], "%Y-%m-%d").date()
        volume = None
        if schema.volume_col in df.columns:
            try:
                volume = float(row[schema.volume_col]) if pd.notna(row[schema.volume_col]) else None
            except Exception:
                volume = None

        bars.append(
            Bar(
                dt=dt,
                open=float(row[schema.open_col]),
                high=float(row[schema.high_col]),
                low=float(row[schema.low_col]),
                close=float(row[schema.close_col]),
                volume=volume,
            )
        )

    return bars
