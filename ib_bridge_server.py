"""Local IB Bridge Server (no external deps)

Purpose
- Expose a tiny local HTTP API the web UI can call to get:
  - Open pre-earnings long straddle positions (paired call+put)
  - Live marks from IB (bid/ask/mid)
  - Unrealized P&L (from IB avgCost vs current mid)
  - Actions-needed (exit before earnings)

Why local?
- IB/TWS is local-only for most setups.
- The production Vercel site cannot safely reach your localhost.

Run
    cd forward-volatility-calculator
    .venv\\Scripts\\python.exe ib_bridge_server.py

Then (locally) run the web app and open the Pre-Earnings Trades page.

Endpoints
- GET /api/health
- GET /api/preearnings/open

Notes
- Requires ib_insync installed in the same venv.
- Requires FINNHUB_API_KEY for earnings-date lookups.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

try:
    from earnings_checker import EarningsChecker

    EARNINGS_CHECKER_AVAILABLE = True
except Exception:
    EARNINGS_CHECKER_AVAILABLE = False

try:
    import asyncio
    from ib_insync import IB, Contract

    IB_AVAILABLE = True
except Exception:
    IB_AVAILABLE = False


HOST = os.environ.get("IB_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("IB_BRIDGE_PORT", "8787"))

IB_HOST = os.environ.get("IB_HOST", "127.0.0.1")
IB_PORT = int(os.environ.get("IB_PORT", "7498"))
IB_PORTS = [
    int(p)
    for p in os.environ.get("IB_PORTS", str(IB_PORT)).split(",")
    if p.strip()
]
IB_CLIENT_ID = int(os.environ.get("IB_CLIENT_ID", "1101"))

# Market data pacing: keep conservative
MKT_DATA_SLEEP_SECONDS = float(os.environ.get("IB_BRIDGE_MKT_SLEEP", "1.5"))

# How often to refresh IB snapshot (seconds)
REFRESH_SECONDS = float(os.environ.get("IB_BRIDGE_REFRESH_SECONDS", "15"))


def _ensure_event_loop_in_this_thread() -> None:
    """Create/set an asyncio loop for the current thread."""
    if not IB_AVAILABLE:
        return
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _finnhub_key() -> str:
    return (os.environ.get("FINNHUB_API_KEY") or "").strip()


_earnings_checker = EarningsChecker(use_yahoo_fallback=True) if EARNINGS_CHECKER_AVAILABLE else None


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, indent=2, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    # Basic CORS for local dev
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def fetch_next_earnings_date(symbol: str, days_ahead: int = 60) -> Optional[str]:
    if not _earnings_checker:
        return None
    # EarningsChecker caches (including negative results) in a shared file cache.
    dt = _earnings_checker.get_earnings_date(symbol, days_ahead=days_ahead)
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d")


def days_to(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None
    return (d - date.today()).days


def action_needed(days_until_earnings: Optional[int]) -> Optional[str]:
    if days_until_earnings is None:
        return None
    if days_until_earnings <= 1:
        return "EXIT TODAY/TOMORROW (avoid gap risk)"
    if days_until_earnings <= 3:
        return "EXIT SOON"
    if days_until_earnings <= 7:
        return "PLAN EXIT"
    return None


@dataclass
class StraddleLegQuote:
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    mid: Optional[float]


@dataclass
class OpenStraddle:
    ticker: str
    expiry: str
    strike: float
    quantity: int
    earnings_date: Optional[str]
    days_to_earnings: Optional[int]
    action_needed: Optional[str]

    call: Dict[str, Any]
    put: Dict[str, Any]

    straddle_mid: Optional[float]
    cost_basis_per_straddle: Optional[float]
    unrealized_pnl: Optional[float]
    unrealized_pnl_pct: Optional[float]


class IBClient:
    def __init__(self) -> None:
        self._ib = IB()

    def connect(self) -> Tuple[bool, Optional[int], Optional[str]]:
        if not IB_AVAILABLE:
            return False, None, "ib_insync not installed"

        if self._ib.isConnected():
            return True, self._ib.client.port, None

        for port in IB_PORTS:
            try:
                self._ib.connect(IB_HOST, port, clientId=IB_CLIENT_ID)
                return True, port, None
            except Exception as e:
                last_err = str(e)
                continue
        return False, None, last_err if 'last_err' in locals() else "Could not connect"

    def disconnect(self) -> None:
        try:
            self._ib.disconnect()
        except Exception:
            pass

    def _get_quote(self, contract: Contract) -> StraddleLegQuote:
        self._ib.qualifyContracts(contract)
        tkr = self._ib.reqMktData(contract, "", False, False)
        self._ib.sleep(MKT_DATA_SLEEP_SECONDS)

        bid = tkr.bid if tkr.bid and tkr.bid > 0 else None
        ask = tkr.ask if tkr.ask and tkr.ask > 0 else None
        last = tkr.last if tkr.last and tkr.last > 0 else None

        if bid is not None and ask is not None:
            mid = (bid + ask) / 2.0
        elif last is not None:
            mid = last
        elif bid is not None:
            mid = bid
        elif ask is not None:
            mid = ask
        else:
            mid = None

        try:
            self._ib.cancelMktData(contract)
        except Exception:
            pass

        return StraddleLegQuote(bid=bid, ask=ask, last=last, mid=mid)

    def get_open_preearnings_straddles(self) -> Dict[str, Any]:
        ok, port, err = self.connect()
        if not ok:
            return {
                "ok": False,
                "error": err or "Could not connect to IB",
            }

        positions = self._ib.positions()

        # Identify paired long call + long put with same (symbol, expiry, strike)
        # Group key is based on contract details.
        grouped: Dict[Tuple[str, str, float], Dict[str, Any]] = {}

        for p in positions:
            c = p.contract
            if getattr(c, "secType", None) != "OPT":
                continue
            if getattr(c, "right", None) not in ("C", "P"):
                continue
            qty = int(getattr(p, "position", 0) or 0)
            if qty <= 0:
                continue  # only long legs for this strategy

            symbol = getattr(c, "symbol", None)
            expiry = getattr(c, "lastTradeDateOrContractMonth", None)
            strike = float(getattr(c, "strike", 0) or 0)
            right = getattr(c, "right", None)

            if not symbol or not expiry or strike <= 0:
                continue

            key = (symbol, expiry, strike)
            if key not in grouped:
                grouped[key] = {
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": strike,
                    "C": None,
                    "P": None,
                }

            grouped[key][right] = {
                "contract": c,
                "quantity": qty,
                "avgCost": float(getattr(p, "avgCost", 0) or 0),
            }

        open_straddles: List[OpenStraddle] = []

        for (symbol, expiry, strike), legs in grouped.items():
            call_leg = legs.get("C")
            put_leg = legs.get("P")
            if not call_leg or not put_leg:
                continue

            qty = min(int(call_leg["quantity"]), int(put_leg["quantity"]))
            if qty <= 0:
                continue

            # Live marks
            call_quote = self._get_quote(call_leg["contract"])
            put_quote = self._get_quote(put_leg["contract"])

            straddle_mid = None
            if call_quote.mid is not None and put_quote.mid is not None:
                straddle_mid = float(call_quote.mid + put_quote.mid)

            cost_basis_per_straddle = float(call_leg["avgCost"] + put_leg["avgCost"])

            unrealized_pnl = None
            unrealized_pnl_pct = None
            if straddle_mid is not None:
                unrealized_pnl = (straddle_mid - cost_basis_per_straddle) * qty * 100.0
                denom = cost_basis_per_straddle * qty * 100.0
                if denom > 0:
                    unrealized_pnl_pct = unrealized_pnl / denom * 100.0

            # Earnings + action
            earnings_date = fetch_next_earnings_date(symbol, days_ahead=120)
            dte = days_to(earnings_date)

            open_straddles.append(
                OpenStraddle(
                    ticker=symbol,
                    expiry=datetime.strptime(expiry, "%Y%m%d").strftime("%Y-%m-%d")
                    if len(expiry) == 8
                    else expiry,
                    strike=float(strike),
                    quantity=int(qty),
                    earnings_date=earnings_date,
                    days_to_earnings=dte,
                    action_needed=action_needed(dte),
                    call={
                        "avgCost": round(float(call_leg["avgCost"]), 4),
                        "bid": None if call_quote.bid is None else round(call_quote.bid, 4),
                        "ask": None if call_quote.ask is None else round(call_quote.ask, 4),
                        "mid": None if call_quote.mid is None else round(call_quote.mid, 4),
                    },
                    put={
                        "avgCost": round(float(put_leg["avgCost"]), 4),
                        "bid": None if put_quote.bid is None else round(put_quote.bid, 4),
                        "ask": None if put_quote.ask is None else round(put_quote.ask, 4),
                        "mid": None if put_quote.mid is None else round(put_quote.mid, 4),
                    },
                    straddle_mid=None if straddle_mid is None else round(straddle_mid, 4),
                    cost_basis_per_straddle=round(cost_basis_per_straddle, 4),
                    unrealized_pnl=None if unrealized_pnl is None else round(unrealized_pnl, 2),
                    unrealized_pnl_pct=None if unrealized_pnl_pct is None else round(unrealized_pnl_pct, 2),
                )
            )

        # Sort actions-needed first, then by most urgent
        def sort_key(x: OpenStraddle):
            urgent = 1 if x.action_needed else 0
            d = x.days_to_earnings if x.days_to_earnings is not None else 9999
            return (-urgent, d, x.ticker)

        open_straddles.sort(key=sort_key)

        return {
            "ok": True,
            "ib_port": port,
            "asof": datetime.now().isoformat(),
            "open_straddles": [asdict(x) for x in open_straddles],
        }


_ib_client = IBClient()

_snapshot_lock = threading.Lock()
_snapshot: Dict[str, Any] = {
    "ok": False,
    "error": "starting",
    "asof": datetime.now().isoformat(),
    "open_straddles": [],
}


def _set_snapshot(payload: Dict[str, Any]) -> None:
    with _snapshot_lock:
        _snapshot.clear()
        _snapshot.update(payload)


def _get_snapshot() -> Dict[str, Any]:
    with _snapshot_lock:
        return dict(_snapshot)


def _snapshot_worker() -> None:
    """Background worker: all IB calls run here (single thread + its loop)."""
    if not IB_AVAILABLE:
        _set_snapshot({"ok": False, "error": "ib_insync not installed", "asof": datetime.now().isoformat(), "open_straddles": []})
        return

    _ensure_event_loop_in_this_thread()

    while True:
        try:
            payload = _ib_client.get_open_preearnings_straddles()
            if "asof" not in payload:
                payload["asof"] = datetime.now().isoformat()
            _set_snapshot(payload)
        except Exception as e:
            _set_snapshot({"ok": False, "error": str(e), "asof": datetime.now().isoformat(), "open_straddles": []})

        time.sleep(REFRESH_SECONDS)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        _json_response(self, 200, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            snap = _get_snapshot()
            _json_response(
                self,
                200,
                {
                    "ok": bool(snap.get("ok")),
                    "ib_connected": bool(snap.get("ok")),
                    "ib_port": snap.get("ib_port"),
                    "error": snap.get("error"),
                    "asof": snap.get("asof"),
                },
            )
            return

        if path == "/api/preearnings/open":
            payload = _get_snapshot()
            _json_response(self, 200 if payload.get("ok") else 503, payload)
            return

        _json_response(self, 404, {"ok": False, "error": "Not found"})

    def log_message(self, format: str, *args) -> None:
        # Keep server output clean
        return


def main() -> int:
    if not IB_AVAILABLE:
        print("ERROR: ib_insync not installed in this environment")
        print("Install into .venv: pip install ib_insync")
        return 1

    t = threading.Thread(target=_snapshot_worker, name="ib_snapshot_worker", daemon=True)
    t.start()

    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"IB Bridge listening on http://{HOST}:{PORT}")
    print("Endpoints: /api/health , /api/preearnings/open")
    print(f"IB ports tried: {IB_PORTS}")
    print(f"Refresh interval: {REFRESH_SECONDS}s")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            httpd.server_close()
        except Exception:
            pass
        try:
            _ib_client.disconnect()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
