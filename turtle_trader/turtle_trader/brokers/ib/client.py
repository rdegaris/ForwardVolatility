from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pandas as pd

try:
    from ib_insync import IB, util, Contract, Future, ContFuture, BarData
except Exception as e:  # pragma: no cover
    IB = None  # type: ignore
    util = None  # type: ignore
    # Use Any so type checkers don't treat these as runtime variables in annotations.
    Contract = Any  # type: ignore
    Future = Any  # type: ignore
    ContFuture = Any  # type: ignore
    BarData = Any  # type: ignore


@dataclass(frozen=True)
class IBConfig:
    host: str = "127.0.0.1"
    port: int = 7498
    client_id: int = 21


class IBClient:
    """Thin wrapper around ib_insync for historical data + trading hooks.

    This is intentionally minimal; we can expand it into a full live engine after
    you confirm your preferred contract selection/rolling approach.
    """

    def __init__(self, cfg: IBConfig):
        if IB is None:
            raise RuntimeError("ib_insync is not installed. Install turtle_trader/requirements.txt")
        self.cfg = cfg
        self.ib = IB()

    def connect(self) -> None:
        self.ib.connect(self.cfg.host, self.cfg.port, clientId=self.cfg.client_id)
        # Prevent long hangs on stalled requests.
        try:
            self.ib.RequestTimeout = 20
        except Exception:
            pass

    def disconnect(self) -> None:
        try:
            self.ib.disconnect()
        except Exception:
            pass

    def qualify(self, contract: Any) -> Any:
        self.ib.qualifyContracts(contract)
        return contract

    def cont_future(self, symbol: str, exchange: str = "CME", currency: str = "USD") -> Any:
        """Continuous futures contract for history (IB rolls internally)."""
        # Use keyword args: ib_insync ContFuture positional args are (symbol, exchange, localSymbol, ...)
        # Passing currency positionally breaks for e.g. 6E and other currency futures.
        return ContFuture(symbol=symbol, exchange=exchange, currency=currency)  # type: ignore

    def future(self, symbol: str, last_trade_month: str, exchange: str = "CME", currency: str = "USD") -> Any:
        """Specific futures contract (e.g. ES 202503)."""
        return Future(symbol=symbol, lastTradeDateOrContractMonth=last_trade_month, exchange=exchange, currency=currency)  # type: ignore

    def resolve_front_month(
        self,
        symbol: str,
        exchange: str = "CME",
        currency: str = "USD",
        min_days_to_expiry: int = 10,
    ) -> Any:
        """Resolve the current front-month contract.

        Uses IB contract details and picks the nearest expiry that is at least
        `min_days_to_expiry` days away. This matches the live-trading requirement:
        signals on continuous series, execute in the front month with a roll buffer.
        """
        if min_days_to_expiry < 0:
            min_days_to_expiry = 0

        generic = Future(symbol=symbol, exchange=exchange, currency=currency)  # type: ignore
        details = self.ib.reqContractDetails(generic)
        if not details:
            raise RuntimeError(f"No contract details returned for {symbol} {exchange}")

        today = datetime.now().date()
        candidates: list[tuple[datetime, Any]] = []
        for d in details:
            c = d.contract
            ym = getattr(c, "lastTradeDateOrContractMonth", None)
            if not ym:
                continue
            # IB uses YYYYMM or YYYYMMDD. Treat YYYYMM as first of month.
            try:
                if len(str(ym)) == 6:
                    exp = datetime.strptime(str(ym) + "01", "%Y%m%d")
                else:
                    exp = datetime.strptime(str(ym)[:8], "%Y%m%d")
            except Exception:
                continue

            dte = (exp.date() - today).days
            if dte >= min_days_to_expiry:
                candidates.append((exp, c))

        if not candidates:
            # Fall back to the nearest contract if everything is inside the buffer.
            for d in details:
                c = d.contract
                ym = getattr(c, "lastTradeDateOrContractMonth", None)
                if not ym:
                    continue
                try:
                    if len(str(ym)) == 6:
                        exp = datetime.strptime(str(ym) + "01", "%Y%m%d")
                    else:
                        exp = datetime.strptime(str(ym)[:8], "%Y%m%d")
                except Exception:
                    continue
                candidates.append((exp, c))

        if not candidates:
            raise RuntimeError(f"Could not parse expiries for {symbol} {exchange}")

        candidates.sort(key=lambda x: x[0])
        chosen = candidates[0][1]
        self.qualify(chosen)
        return chosen

    def fetch_daily_bars(
        self,
        contract: Any,
        duration: str = "10 Y",
        use_rth: bool = False,
    ) -> pd.DataFrame:
        """Fetch daily bars from IB.

        Returns a DataFrame with columns: date, open, high, low, close, volume.
        """
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=use_rth,
            formatDate=1,
        )

        if not bars:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        df = util.df(bars)  # type: ignore
        # ib_insync uses 'date' as datetime
        df = df.rename(columns={"date": "date"})
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
        out = df[["date", "open", "high", "low", "close", "volume"]].copy()
        return out
