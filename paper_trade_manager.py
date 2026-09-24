"""
OzCTA Paper Trading Engine & Performance Manager

Handles:
1. Signal Ingestion: Ingests triggered signals from Trendorama (Turtle S2), The Bradman (Taylor),
   YouHaveChosenWisely (Grail), TooHot TooCold (ODID), and The Linda.
2. Trade Ledger: Maintains executed paper trades in a persistent local JSON store (`executed_trades.json`).
3. Daily Monitoring: Evaluates active paper trades against latest daily price bars (High, Low, Close)
   for Stop Loss and Profit Target breaches.
4. Performance Metrics: Calculates running equity curve, win rate, profit factor, total realized/unrealized PnL,
   and exports `paper_trades_latest.json` and `paper_trade_performance.json` for web display.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Point values (contract multipliers) for CME / NYMEX / COMEX futures (Micro contracts for $100k account)
FUTURES_POINT_VALUES: Dict[str, float] = {
    "ES": 5.0,        # Micro E-mini S&P 500 (MES)
    "NQ": 2.0,        # Micro E-mini Nasdaq 100 (MNQ)
    "RTY": 5.0,       # Micro E-mini Russell 2000 (M2K)
    "YM": 0.5,        # Micro E-mini Dow ($0.50) (MYM)
    "GC": 10.0,       # Micro Gold (10 oz) (MGC)
    "SI": 1000.0,     # Micro Silver (1000 oz) (SIL)
    "CL": 100.0,      # Micro WTI Crude Oil (100 bbl) (MCL)
    "NG": 2500.0,     # E-mini Natural Gas (QG)
    "6E": 12500.0,    # Micro Euro FX (M6E)
    "6B": 6250.0,     # Micro British Pound (M6B)
    "6A": 10000.0,    # Micro AUD
    "6C": 10000.0,    # Micro CAD
    "AUD": 10000.0,
    "CAD": 10000.0,
    "EUR": 12500.0,
    "GBP": 6250.0,
    "ZB": 1000.0,     # 30-Year T-Bond Futures
    "ZN": 1000.0,     # 10-Year T-Note Futures
    "ZF": 1000.0,
    "ZT": 2000.0,
    "HG": 2500.0,
    "HO": 4200.0,
    "KC": 375.0,
    "SB": 1120.0,
    "ZC": 50.0,
    "ZS": 50.0,
    "ZW": 50.0,
    "ZL": 600.0,
    "HE": 400.0,
}

TICK_SIZES: Dict[str, float] = {
    "ES": 0.25,
    "NQ": 0.25,
    "RTY": 0.1,
    "YM": 1.0,
    "GC": 0.1,
    "SI": 0.005,
    "CL": 0.01,
    "NG": 0.001,
    "6E": 0.00005,
    "6B": 0.0001,
    "6J": 0.0000005,
    "6A": 0.00005,
    "6C": 0.00005,
    "AUD": 0.00005,
    "CAD": 0.00005,
    "EUR": 0.00005,
    "GBP": 0.0001,
    "JPY": 0.0000005,
    "ZB": 0.03125,
    "ZN": 0.015625,
    "ZF": 0.0078125,
    "ZT": 0.0078125,
    "HG": 0.0005,
    "HO": 0.0001,
    "KC": 0.05,
    "SB": 0.01,
    "ZC": 0.25,
    "ZS": 0.25,
    "ZW": 0.25,
    "ZL": 0.01,
    "HE": 0.025,
}

SYMBOL_NAMES: Dict[str, str] = {
    "ES": "E-mini S&P 500",
    "NQ": "E-mini Nasdaq 100",
    "RTY": "E-mini Russell 2000",
    "YM": "E-mini Dow Jones",
    "GC": "Gold Futures",
    "SI": "Silver Futures",
    "CL": "Crude Oil Futures",
    "NG": "Natural Gas Futures",
    "6E": "Euro FX Futures",
    "EUR": "Euro FX Futures",
    "6B": "British Pound Futures",
    "GBP": "British Pound Futures",
    "6J": "Japanese Yen Futures",
    "JPY": "Japanese Yen Futures",
    "6A": "Australian Dollar Futures",
    "AUD": "Australian Dollar Futures",
    "6C": "Canadian Dollar Futures",
    "CAD": "Canadian Dollar Futures",
    "ZB": "30-Year T-Bond Futures",
    "ZN": "10-Year T-Note Futures",
    "ZF": "5-Year T-Note Futures",
    "ZT": "2-Year T-Note Futures",
    "HG": "Copper Futures",
    "HO": "Heating Oil Futures",
    "KC": "Coffee Futures",
    "SB": "Sugar #11 Futures",
    "ZC": "Corn Futures",
    "ZS": "Soybean Futures",
    "ZW": "Wheat Futures",
    "ZL": "Soybean Oil Futures",
    "HE": "Lean Hogs Futures",
}


def get_point_value(symbol: str) -> float:
    sym = symbol.upper().strip()
    return FUTURES_POINT_VALUES.get(sym, 1.0)


def get_symbol_name(symbol: str) -> str:
    sym = symbol.upper().strip()
    return SYMBOL_NAMES.get(sym, sym)


STARTING_PORTFOLIO_CAPITAL: float = 100000.0  # $100,000 starting portfolio capital
DEFAULT_RISK_PER_TRADE_PCT: float = 0.02       # 2% risk of total equity per trade ($2,000 per trade)
MAX_PORTFOLIO_OPEN_TRADES: int = 8             # Max 8 concurrent open trades (16% max portfolio heat)

CLUSTERS: Dict[str, set[str]] = {
    "equities": {"ES", "NQ", "RTY", "YM"},
    "rates": {"ZB", "ZN", "ZF", "ZT"},
    "energies": {"CL", "NG", "HO", "RB"},
    "metals": {"GC", "SI", "HG"},
    "fx": {"6E", "6B", "6J", "6A", "6C", "EUR", "GBP", "JPY", "CAD", "AUD"},
    "grains": {"ZC", "ZW", "ZS", "ZL"},
    "softs": {"KC", "SB", "CT"},
    "livestock": {"HE", "LE"},
}

CLUSTER_CAPS: Dict[str, int] = {
    "equities": 2,
    "rates": 2,
    "energies": 2,
    "metals": 1,
    "fx": 2,
    "grains": 2,
    "softs": 2,
    "livestock": 1,
    "other": 2,
}


def get_symbol_cluster(symbol: str) -> str:
    sym = symbol.upper().strip()
    for cluster_name, syms in CLUSTERS.items():
        if sym in syms:
            return cluster_name
    return "other"


def calculate_position_size(
    entry_price: float,
    stop_loss: float,
    point_value: float,
    equity: float = STARTING_PORTFOLIO_CAPITAL,
    risk_pct: float = DEFAULT_RISK_PER_TRADE_PCT,
) -> int:
    """
    Calculate position contract quantity so that total trade risk is risk_pct (2%) of equity.
    Dollar risk budget = equity * risk_pct ($2,000 on $100,000 equity).
    Per-contract dollar risk = abs(entry_price - stop_loss) * point_value.
    Qty = floor(dollar_risk / per_contract_risk).
    """
    per_contract_risk = abs(entry_price - stop_loss) * point_value
    if per_contract_risk <= 0:
        return 1
    dollar_risk = equity * risk_pct
    qty = int(dollar_risk // per_contract_risk)
    return max(1, qty)


@dataclass
class PaperTrade:
    id: str
    symbol: str
    symbol_name: str
    strategy: str  # 'Trendorama', 'The Bradman', 'YouHaveChosenWisely', 'TooHot TooCold', 'The Linda'
    side: str      # 'long' | 'short'
    entry_date: str
    entry_price: float
    qty: int
    stop_loss: float
    profit_target: Optional[float]
    point_value: float
    status: str    # 'OPEN' | 'HIT_TARGET' | 'STOPPED_OUT' | 'MANUALLY_CLOSED'
    exit_date: Optional[str] = None
    exit_price: Optional[str | float] = None
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    return_pct: float = 0.0
    duration_days: int = 0
    notes: Optional[str] = None
    initial_risk: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PaperTradeManager:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent
        else:
            self.base_dir = Path(base_dir).resolve()

        self.data_dir = self.base_dir / "turtle_trader" / "data"
        self.executed_trades_file = self.base_dir / "executed_trades.json"
        
        # Web sync destination
        self.web_data_dir = self.base_dir.parent / "forward-volatility-web" / "public" / "data"

    def load_executed_trades(self) -> List[Dict[str, Any]]:
        """Load persistent executed trades list from JSON file."""
        if not self.executed_trades_file.exists():
            return []
        try:
            with open(self.executed_trades_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "trades" in data:
                    return data["trades"]
                return []
        except Exception as e:
            print(f"[PaperTradeManager] Error loading {self.executed_trades_file}: {e}")
            return []

    def save_executed_trades(self, trades: List[Dict[str, Any]]):
        """Save executed trades to JSON file and mirror to web directory."""
        with open(self.executed_trades_file, "w", encoding="utf-8") as f:
            json.dump(trades, f, indent=2)

        if self.web_data_dir.exists():
            web_trades_file = self.web_data_dir / "executed_trades.json"
            try:
                with open(web_trades_file, "w", encoding="utf-8") as f:
                    json.dump(trades, f, indent=2)
            except Exception as e:
                print(f"[PaperTradeManager] Error saving to web dir: {e}")

    def compute_default_profit_target(
        self, strategy: str, side: str, entry_price: float, stop_loss: float, symbol: str
    ) -> float:
        """
        Compute an objective default profit target if none is provided.
        Can be overridden or customized as new target rules are provided.
        Default: 2:1 Reward-to-Risk ratio based on the distance between entry and initial stop.
        """
        risk_dist = abs(entry_price - stop_loss)
        if risk_dist <= 0:
            risk_dist = entry_price * 0.015  # 1.5% fallback

        if side.lower() == "long":
            # 2R target
            target = entry_price + (2.0 * risk_dist)
        else:
            # 2R target
            target = entry_price - (2.0 * risk_dist)

        tick = TICK_SIZES.get(symbol.upper(), 0.01)
        if tick < 1:
            digits = len(str(tick).split(".")[1]) if "." in str(tick) else 2
            return round(target, digits)
        return round(target, 2)

    def ingest_strategy_signals(self) -> int:
        """
        Reads latest signal JSON files and creates new paper trades for any newly fired signals.
        Enforces institutional CTA constraints:
        - Max 8 concurrent open portfolio trades (16% total risk budget).
        - Symbol exclusivity (max 1 active trade per market symbol across all strategies).
        - Sector correlation cluster caps (e.g. max 2 equities, max 2 rates, max 1 metal).
        Returns the number of new trades created.
        """
        existing_trades = self.load_executed_trades()
        # Set of unique keys to prevent duplicate trades: (date, symbol, strategy, side)
        existing_keys = {
            (t.get("entry_date"), t.get("symbol"), t.get("strategy"), t.get("side"))
            for t in existing_trades
        }

        # Track currently open trades & cluster usage
        open_trades = [t for t in existing_trades if t.get("status") == "OPEN"]
        open_symbols = {t.get("symbol", "").upper() for t in open_trades}
        cluster_open_counts: Dict[str, int] = {}
        for t in open_trades:
            c = get_symbol_cluster(t.get("symbol", ""))
            cluster_open_counts[c] = cluster_open_counts.get(c, 0) + 1

        new_trades: List[Dict[str, Any]] = []

        def can_open_trade(sym: str) -> tuple[bool, str]:
            sym_upper = sym.upper().strip()
            # 1. Global open trades cap
            total_active = len(open_trades) + len(new_trades)
            if total_active >= MAX_PORTFOLIO_OPEN_TRADES:
                return False, f"Global portfolio cap reached ({total_active}/{MAX_PORTFOLIO_OPEN_TRADES})"

            # 2. Market exclusivity (1 trade max per symbol)
            active_symbols = open_symbols | {t.get("symbol", "").upper() for t in new_trades}
            if sym_upper in active_symbols:
                return False, f"Symbol {sym_upper} already has an active position"

            # 3. Correlation cluster cap
            cluster = get_symbol_cluster(sym_upper)
            cap = CLUSTER_CAPS.get(cluster, 2)
            cur_count = cluster_open_counts.get(cluster, 0)
            if cur_count >= cap:
                return False, f"Sector cluster cap reached for {cluster} ({cur_count}/{cap})"

            return True, "OK"

        def register_new_trade(pt: Dict[str, Any], key: tuple):
            new_trades.append(pt)
            existing_keys.add(key)
            c = get_symbol_cluster(pt.get("symbol", ""))
            cluster_open_counts[c] = cluster_open_counts.get(c, 0) + 1

        # 1. Trendorama (Turtle S2) Signals
        turtle_files = [
            self.base_dir / "turtle_signals_latest.json",
            self.base_dir / "turtle_trader" / "turtle_signals_latest.json",
            self.web_data_dir / "turtle_signals_latest.json",
        ]
        for tf in turtle_files:
            if tf.exists():
                try:
                    with open(tf, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                        asof_date = payload.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
                        triggered = payload.get("triggered", [])
                        for sig in triggered:
                            sym = sig.get("symbol")
                            side = sig.get("side", "long").lower()
                            if not sym or not sig.get("eligible", True):
                                continue
                            key = (asof_date, sym, "Trendorama", side)
                            if key not in existing_keys:
                                can_open, reason = can_open_trade(sym)
                                if not can_open:
                                    continue
                                entry_price = float(sig.get("entry_stop") or sig.get("last_close") or 0.0)
                                stop_loss = float(sig.get("stop_loss") or (entry_price * 0.98 if side == "long" else entry_price * 1.02))
                                target = self.compute_default_profit_target("Trendorama", side, entry_price, stop_loss, sym)
                                unit_qty = int(sig.get("unit_qty") or 0)
                                pt = self._create_paper_trade_dict(
                                    symbol=sym,
                                    strategy="Trendorama",
                                    side=side,
                                    entry_date=asof_date,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss,
                                    profit_target=target,
                                    qty=unit_qty if unit_qty > 0 else None,
                                    notes=sig.get("notes", "55-day breakout trigger"),
                                )
                                register_new_trade(pt, key)
                except Exception as e:
                    print(f"[PaperTradeManager] Error parsing turtle signals from {tf}: {e}")
                break

        # 2. YouHaveChosenWisely (Grail) Signals
        grail_files = [
            self.base_dir / "grail_signals_latest.json",
            self.base_dir / "turtle_trader" / "grail_signals_latest.json",
            self.web_data_dir / "grail_signals_latest.json",
        ]
        for gf in grail_files:
            if gf.exists():
                try:
                    with open(gf, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                        asof_date = payload.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
                        signals = payload.get("signals", []) + payload.get("triggered", [])
                        for sig in signals:
                            if not sig.get("eligible", False):
                                continue
                            side = sig.get("side", "none").lower()
                            if side not in ("long", "short"):
                                continue
                            sym = sig.get("symbol")
                            key = (asof_date, sym, "YouHaveChosenWisely", side)
                            if key not in existing_keys:
                                can_open, reason = can_open_trade(sym)
                                if not can_open:
                                    continue
                                entry_price = float(sig.get("entry_zone") or sig.get("close") or 0.0)
                                stop_loss = float(sig.get("stop_loss") or (entry_price * 0.98 if side == "long" else entry_price * 1.02))
                                target = float(sig.get("target") or self.compute_default_profit_target("YouHaveChosenWisely", side, entry_price, stop_loss, sym))
                                pt = self._create_paper_trade_dict(
                                    symbol=sym,
                                    strategy="YouHaveChosenWisely",
                                    side=side,
                                    entry_date=asof_date,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss,
                                    profit_target=target,
                                    notes=sig.get("reason", "ADX pullback to 20 EMA"),
                                )
                                register_new_trade(pt, key)
                except Exception as e:
                    print(f"[PaperTradeManager] Error parsing grail signals from {gf}: {e}")
                break

        # 3. The Bradman (Taylor 3-Day Cycle) Signals
        taylor_files = [
            self.base_dir / "taylor_signals_latest.json",
            self.base_dir / "turtle_trader" / "taylor_signals_latest.json",
            self.web_data_dir / "taylor_signals_latest.json",
        ]
        for tf in taylor_files:
            if tf.exists():
                try:
                    with open(tf, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                        asof_date = payload.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
                        signals = payload.get("signals", [])
                        for sig in signals:
                            phase = sig.get("cycle_phase", "")
                            action = sig.get("action", "")
                            if action == "WATCH" or not phase:
                                continue
                            sym = sig.get("symbol")
                            side = "long" if "BUY" in phase or action == "BUY" else "short"
                            key = (asof_date, sym, "The Bradman", side)
                            if key not in existing_keys:
                                can_open, reason = can_open_trade(sym)
                                if not can_open:
                                    continue
                                entry_price = float(sig.get("last_close") or sig.get("entry_target") or 0.0)
                                stop_loss = float(sig.get("stop_loss") or (entry_price * 0.985 if side == "long" else entry_price * 1.015))
                                target = float(sig.get("objective_target") or sig.get("target_high") or sig.get("target_low") or self.compute_default_profit_target("The Bradman", side, entry_price, stop_loss, sym))
                                pt = self._create_paper_trade_dict(
                                    symbol=sym,
                                    strategy="The Bradman",
                                    side=side,
                                    entry_date=asof_date,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss,
                                    profit_target=target,
                                    notes=f"Taylor {phase} Setup",
                                )
                                register_new_trade(pt, key)
                except Exception as e:
                    print(f"[PaperTradeManager] Error parsing taylor signals from {tf}: {e}")
                break

        # 4. TooHot TooCold (OD/ID Breakout) Signals
        odid_files = [
            self.base_dir / "odid_signals_latest.json",
            self.base_dir / "turtle_trader" / "odid_signals_latest.json",
            self.web_data_dir / "odid_signals_latest.json",
        ]
        for of in odid_files:
            if of.exists():
                try:
                    with open(of, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                        asof_date = payload.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
                        triggered = payload.get("triggered", [])
                        for sig in triggered:
                            if not sig.get("eligible", False):
                                continue
                            sym = sig.get("symbol")
                            side = sig.get("side", "long").lower()
                            key = (asof_date, sym, "TooHot TooCold", side)
                            if key not in existing_keys:
                                can_open, reason = can_open_trade(sym)
                                if not can_open:
                                    continue
                                entry_price = float(sig.get("entry_stop") or sig.get("last_close") or 0.0)
                                stop_loss = float(sig.get("stop_loss") or (entry_price * 0.98 if side == "long" else entry_price * 1.02))
                                target = self.compute_default_profit_target("TooHot TooCold", side, entry_price, stop_loss, sym)
                                pt = self._create_paper_trade_dict(
                                    symbol=sym,
                                    strategy="TooHot TooCold",
                                    side=side,
                                    entry_date=asof_date,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss,
                                    profit_target=target,
                                    notes=sig.get("notes", "OD/ID Range Expansion Breakout"),
                                )
                                register_new_trade(pt, key)
                except Exception as e:
                    print(f"[PaperTradeManager] Error parsing odid signals from {of}: {e}")
                break

        # 5. The Linda Signals
        linda_files = [
            self.web_data_dir / "linda_signals_latest.json",
            self.base_dir / "linda_signals_latest.json",
        ]
        for lf in linda_files:
            if lf.exists():
                try:
                    with open(lf, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                        asof_date = payload.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
                        signals = payload.get("signals", [])
                        for sig in signals:
                            if not sig.get("triggered", False):
                                continue
                            sym = sig.get("symbol")
                            side = sig.get("side", "long").lower()
                            key = (asof_date, sym, "The Linda", side)
                            if key not in existing_keys:
                                can_open, reason = can_open_trade(sym)
                                if not can_open:
                                    continue
                                entry_price = float(sig.get("entry_price") or sig.get("close") or 0.0)
                                stop_loss = float(sig.get("stop_loss") or (entry_price * 0.98 if side == "long" else entry_price * 1.02))
                                target = float(sig.get("target") or self.compute_default_profit_target("The Linda", side, entry_price, stop_loss, sym))
                                pt = self._create_paper_trade_dict(
                                    symbol=sym,
                                    strategy="The Linda",
                                    side=side,
                                    entry_date=asof_date,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss,
                                    profit_target=target,
                                    notes=sig.get("setup", "Linda Raschke Setup"),
                                )
                                register_new_trade(pt, key)
                except Exception as e:
                    print(f"[PaperTradeManager] Error parsing linda signals from {lf}: {e}")
                break

        if new_trades:
            all_trades = existing_trades + new_trades
            self.save_executed_trades(all_trades)
            print(f"[PaperTradeManager] Ingested {len(new_trades)} new paper trades.")
        return len(new_trades)

    def _create_paper_trade_dict(
        self,
        symbol: str,
        strategy: str,
        side: str,
        entry_date: str,
        entry_price: float,
        stop_loss: float,
        profit_target: Optional[float],
        notes: Optional[str] = None,
        qty: Optional[int] = None,
        equity: float = STARTING_PORTFOLIO_CAPITAL,
    ) -> Dict[str, Any]:
        sym = symbol.upper().strip()
        point_val = get_point_value(sym)
        sym_name = get_symbol_name(sym)
        trade_id = f"pt_{sym}_{strategy.replace(' ', '')[:4]}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}"
        
        if qty is None or qty <= 0:
            qty = calculate_position_size(
                entry_price=entry_price,
                stop_loss=stop_loss,
                point_value=point_val,
                equity=equity,
                risk_pct=DEFAULT_RISK_PER_TRADE_PCT,
            )

        initial_risk = abs(entry_price - stop_loss) * point_val * qty

        trade = PaperTrade(
            id=trade_id,
            symbol=sym,
            symbol_name=sym_name,
            strategy=strategy,
            side=side.lower(),
            entry_date=entry_date,
            entry_price=round(entry_price, 4),
            qty=qty,
            stop_loss=round(stop_loss, 4),
            profit_target=round(profit_target, 4) if profit_target else None,
            point_value=point_val,
            status="OPEN",
            current_price=round(entry_price, 4),
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            return_pct=0.0,
            duration_days=0,
            notes=notes,
            initial_risk=round(initial_risk, 2),
        )
        return asdict(trade)

    def get_latest_market_bar(self, symbol: str) -> Optional[Dict[str, float | str]]:
        """
        Retrieves the latest daily OHLC bar for a symbol from local CSV or Yahoo cache.
        """
        sym = symbol.upper()
        # Check in turtle_trader/data/{symbol}.csv
        csv_file = self.data_dir / f"{sym}.csv"
        if csv_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(csv_file)
                if not df.empty:
                    last_row = df.iloc[-1]
                    # standard columns: Date/datetime, Open, High, Low, Close
                    dt_col = "Date" if "Date" in df.columns else ("datetime" if "datetime" in df.columns else df.columns[0])
                    return {
                        "date": str(last_row[dt_col]).split(" ")[0],
                        "open": float(last_row.get("Open", last_row.get("open", 0))),
                        "high": float(last_row.get("High", last_row.get("high", 0))),
                        "low": float(last_row.get("Low", last_row.get("low", 0))),
                        "close": float(last_row.get("Close", last_row.get("close", 0))),
                    }
            except Exception:
                pass
        return None

    def get_symbol_technicals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest bar and key technical levels (20-day Donchian, 20 EMA) for a symbol.
        """
        sym = symbol.upper()
        csv_file = self.data_dir / f"{sym}.csv"
        if csv_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(csv_file)
                if not df.empty:
                    dt_col = "Date" if "Date" in df.columns else ("datetime" if "datetime" in df.columns else df.columns[0])
                    last_row = df.iloc[-1]
                    highs = df["High"].tail(22).values if "High" in df.columns else df["high"].tail(22).values
                    lows = df["Low"].tail(22).values if "Low" in df.columns else df["low"].tail(22).values
                    closes = df["Close"] if "Close" in df.columns else df["close"]
                    ema20 = closes.ewm(span=20, adjust=False).mean().iloc[-1] if len(closes) >= 5 else float(last_row.get("Close", 0))

                    donchian_low_20 = float(min(lows[:-1])) if len(lows) > 1 else float(min(lows))
                    donchian_high_20 = float(max(highs[:-1])) if len(highs) > 1 else float(max(highs))

                    return {
                        "date": str(last_row[dt_col]).split(" ")[0],
                        "open": float(last_row.get("Open", last_row.get("open", 0))),
                        "high": float(last_row.get("High", last_row.get("high", 0))),
                        "low": float(last_row.get("Low", last_row.get("low", 0))),
                        "close": float(last_row.get("Close", last_row.get("close", 0))),
                        "donchian_low_20": donchian_low_20,
                        "donchian_high_20": donchian_high_20,
                        "ema_20": float(ema20),
                    }
            except Exception:
                pass
        bar = self.get_latest_market_bar(symbol)
        return bar

    def evaluate_daily_monitoring(self) -> Dict[str, Any]:
        """
        Monitors active paper trades daily with institutional strategy-specific exits:
        - Stop Loss hits (all strategies)
        - Profit Target / Objective hits (all strategies)
        - Trendorama: 20-day Donchian trailing breakout exit
        - The Bradman: Taylor 3-day cycle exit (max 3 days holding)
        - YouHaveChosenWisely: 20 EMA cross exit or 5-day max duration
        - TooHot TooCold: 4-day time exit
        - The Linda: 5-day time exit
        - Updates Unrealized & Realized PnL based on point multiplier and risk sizing
        """
        trades = self.load_executed_trades()
        if not trades:
            return {"total": 0, "open": 0, "closed": 0, "hit_target": 0, "stopped_out": 0}

        now_str = datetime.utcnow().strftime("%Y-%m-%d")
        now_dt = datetime.utcnow()

        stats = {
            "total": len(trades),
            "open": 0,
            "closed": 0,
            "hit_target": 0,
            "stopped_out": 0,
            "donchian_exit": 0,
            "time_exit": 0,
            "ema_exit": 0,
            "updated": 0,
        }

        for t in trades:
            sym = t.get("symbol", "").upper()
            point_val = float(t.get("point_value") or get_point_value(sym))
            t["point_value"] = point_val
            t["symbol_name"] = get_symbol_name(sym)

            side = t.get("side", "long").lower()
            strat = t.get("strategy", "")
            entry_price = float(t.get("entry_price") or 0.0)
            stop_loss = float(t.get("stop_loss") or 0.0)
            profit_target = float(t.get("profit_target")) if t.get("profit_target") is not None else None
            qty = int(t.get("qty") or 1)

            entry_date_str = t.get("entry_date", now_str)
            try:
                entry_dt = datetime.strptime(entry_date_str[:10], "%Y-%m-%d")
                duration = (now_dt - entry_dt).days
                t["duration_days"] = max(0, duration)
            except Exception:
                duration = 0
                t["duration_days"] = 0

            if t.get("status") == "OPEN":
                stats["open"] += 1
                tech = self.get_symbol_technicals(sym)

                if tech:
                    high = float(tech["high"])
                    low = float(tech["low"])
                    close = float(tech["close"])
                    bar_date = str(tech["date"])

                    t["current_price"] = round(close, 4)

                    # 1. Stop Loss check
                    is_stopped = (side == "long" and stop_loss > 0 and low <= stop_loss) or \
                                 (side == "short" and stop_loss > 0 and high >= stop_loss)

                    # 2. Profit Target check
                    hit_target = (side == "long" and profit_target and profit_target > 0 and high >= profit_target) or \
                                 (side == "short" and profit_target and profit_target > 0 and low <= profit_target)

                    # 3. The Linda: Same-Day Mean Reversion with Mandatory EOD Exit
                    if strat == "The Linda":
                        if is_stopped:
                            t["status"] = "STOPPED_OUT"
                            exit_price = stop_loss
                            t["exit_price"] = round(exit_price, 4)
                            t["exit_date"] = bar_date
                            pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                            t["realized_pnl"] = round(pnl, 2)
                            t["unrealized_pnl"] = 0.0
                            t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                            stats["stopped_out"] += 1
                            stats["open"] -= 1
                            stats["closed"] += 1
                        elif hit_target:
                            t["status"] = "HIT_TARGET"
                            exit_price = profit_target
                            t["exit_price"] = round(exit_price, 4)
                            t["exit_date"] = bar_date
                            pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                            t["realized_pnl"] = round(pnl, 2)
                            t["unrealized_pnl"] = 0.0
                            t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                            stats["hit_target"] += 1
                            stats["open"] -= 1
                            stats["closed"] += 1
                        else:
                            # Mandatory Same-Day End of Day (EOD) Exit
                            t["status"] = "EOD_EXIT"
                            exit_price = close
                            t["exit_price"] = round(exit_price, 4)
                            t["exit_date"] = bar_date
                            pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                            t["realized_pnl"] = round(pnl, 2)
                            t["unrealized_pnl"] = 0.0
                            t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                            stats["eod_exit"] = stats.get("eod_exit", 0) + 1
                            stats["open"] -= 1
                            stats["closed"] += 1
                        t["updated_at"] = datetime.utcnow().isoformat()
                        stats["updated"] += 1
                        continue

                    # 4. Trendorama Donchian 20 Trailing Exit
                    donchian_exit = False
                    if strat == "Trendorama" and tech:
                        if side == "long" and tech.get("donchian_low_20") and low <= tech["donchian_low_20"]:
                            donchian_exit = True
                        elif side == "short" and tech.get("donchian_high_20") and high >= tech["donchian_high_20"]:
                            donchian_exit = True

                    # 5. Strategy Time Exits
                    time_exit = False
                    if strat == "The Bradman" and duration >= 3:
                        time_exit = True
                    elif strat == "TooHot TooCold" and duration >= 4:
                        time_exit = True
                    elif strat == "YouHaveChosenWisely" and duration >= 5:
                        time_exit = True

                    # 6. Holy Grail EMA Exit
                    ema_exit = False
                    if strat == "YouHaveChosenWisely" and tech and tech.get("ema_20"):
                        if side == "long" and close < tech["ema_20"]:
                            ema_exit = True
                        elif side == "short" and close > tech["ema_20"]:
                            ema_exit = True

                    if is_stopped:
                        t["status"] = "STOPPED_OUT"
                        exit_price = stop_loss
                        t["exit_price"] = round(exit_price, 4)
                        t["exit_date"] = bar_date
                        pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                        t["realized_pnl"] = round(pnl, 2)
                        t["unrealized_pnl"] = 0.0
                        t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                        stats["stopped_out"] += 1
                        stats["open"] -= 1
                        stats["closed"] += 1
                    elif hit_target:
                        t["status"] = "HIT_TARGET"
                        exit_price = profit_target
                        t["exit_price"] = round(exit_price, 4)
                        t["exit_date"] = bar_date
                        pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                        t["realized_pnl"] = round(pnl, 2)
                        t["unrealized_pnl"] = 0.0
                        t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                        stats["hit_target"] += 1
                        stats["open"] -= 1
                        stats["closed"] += 1
                    elif donchian_exit:
                        t["status"] = "DONCHIAN_EXIT"
                        exit_price = tech["donchian_low_20"] if side == "long" else tech["donchian_high_20"]
                        t["exit_price"] = round(exit_price, 4)
                        t["exit_date"] = bar_date
                        pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                        t["realized_pnl"] = round(pnl, 2)
                        t["unrealized_pnl"] = 0.0
                        t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                        stats["donchian_exit"] += 1
                        stats["open"] -= 1
                        stats["closed"] += 1
                    elif ema_exit:
                        t["status"] = "EMA_EXIT"
                        exit_price = close
                        t["exit_price"] = round(exit_price, 4)
                        t["exit_date"] = bar_date
                        pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                        t["realized_pnl"] = round(pnl, 2)
                        t["unrealized_pnl"] = 0.0
                        t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                        stats["ema_exit"] += 1
                        stats["open"] -= 1
                        stats["closed"] += 1
                    elif time_exit:
                        t["status"] = "TIME_EXIT"
                        exit_price = close
                        t["exit_price"] = round(exit_price, 4)
                        t["exit_date"] = bar_date
                        pnl = (exit_price - entry_price if side == "long" else entry_price - exit_price) * point_val * qty
                        t["realized_pnl"] = round(pnl, 2)
                        t["unrealized_pnl"] = 0.0
                        t["return_pct"] = round(((exit_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
                        stats["time_exit"] += 1
                        stats["open"] -= 1
                        stats["closed"] += 1
                    else:
                        # Trade stays open
                        unrealized = (close - entry_price if side == "long" else entry_price - close) * point_val * qty
                        t["unrealized_pnl"] = round(unrealized, 2)
                        t["return_pct"] = round(((close - entry_price if side == "long" else entry_price - close) / entry_price) * 100, 2) if entry_price > 0 else 0.0

                    t["updated_at"] = datetime.utcnow().isoformat()
                    stats["updated"] += 1
            else:
                stats["closed"] += 1
                if t.get("status") == "HIT_TARGET":
                    stats["hit_target"] += 1
                elif t.get("status") == "STOPPED_OUT":
                    stats["stopped_out"] += 1
                elif t.get("status") == "DONCHIAN_EXIT":
                    stats["donchian_exit"] += 1
                elif t.get("status") == "TIME_EXIT":
                    stats["time_exit"] += 1
                elif t.get("status") == "EMA_EXIT":
                    stats["ema_exit"] += 1
                elif t.get("status") == "EOD_EXIT":
                    stats["eod_exit"] = stats.get("eod_exit", 0) + 1

        self.save_executed_trades(trades)
        return stats

    def calculate_performance_summary(self) -> Dict[str, Any]:
        """
        Calculates running performance statistics, equity curve, and strategy breakdown.
        """
        trades = self.load_executed_trades()
        now_iso = datetime.utcnow().isoformat()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        if not trades:
            empty_payload = {
                "timestamp": now_iso,
                "date": today_str,
                "total_trades": 0,
                "open_trades_count": 0,
                "closed_trades_count": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "total_realized_pnl": 0.0,
                "total_unrealized_pnl": 0.0,
                "net_pnl": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "strategy_breakdown": {},
                "equity_curve": [
                    {
                        "date": today_str,
                        "cum_pnl": 0.0,
                        "equity": STARTING_PORTFOLIO_CAPITAL,
                        "drawdown_pct": 0.0,
                    }
                ],
                "recent_trades": [],
            }
            self._export_json("paper_trade_performance.json", empty_payload)
            self._export_json("paper_trades_latest.json", {"timestamp": now_iso, "date": today_str, "trades": []})
            return empty_payload

        closed_trades = [t for t in trades if t.get("status") in ("HIT_TARGET", "STOPPED_OUT", "MANUALLY_CLOSED", "DONCHIAN_EXIT", "TIME_EXIT", "EMA_EXIT", "EOD_EXIT")]
        open_trades = [t for t in trades if t.get("status") == "OPEN"]

        total_realized = sum(float(t.get("realized_pnl", 0.0)) for t in closed_trades)
        total_unrealized = sum(float(t.get("unrealized_pnl", 0.0)) for t in open_trades)
        net_pnl = total_realized + total_unrealized

        wins = [t for t in closed_trades if float(t.get("realized_pnl", 0.0)) > 0]
        losses = [t for t in closed_trades if float(t.get("realized_pnl", 0.0)) < 0]

        total_win_dollars = sum(float(t.get("realized_pnl", 0.0)) for t in wins)
        total_loss_dollars = abs(sum(float(t.get("realized_pnl", 0.0)) for t in losses))

        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else (
            # If all trades are currently open, compute based on current open profit
            (len([t for t in open_trades if float(t.get("unrealized_pnl", 0.0)) > 0]) / len(open_trades) * 100) if open_trades else 0.0
        )
        profit_factor = (total_win_dollars / total_loss_dollars) if total_loss_dollars > 0 else (99.9 if total_win_dollars > 0 else 1.0)
        avg_win = (total_win_dollars / len(wins)) if wins else 0.0
        avg_loss = (total_loss_dollars / len(losses)) if losses else 0.0

        # Strategy breakdown
        strategy_stats: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            st = t.get("strategy", "Unknown")
            if st not in strategy_stats:
                strategy_stats[st] = {
                    "strategy": st,
                    "total_trades": 0,
                    "open_trades": 0,
                    "closed_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": 0.0,
                    "net_pnl": 0.0,
                    "win_rate_pct": 0.0,
                }
            s_stat = strategy_stats[st]
            s_stat["total_trades"] += 1
            if t.get("status") == "OPEN":
                s_stat["open_trades"] += 1
                s_stat["unrealized_pnl"] += float(t.get("unrealized_pnl", 0.0))
            else:
                s_stat["closed_trades"] += 1
                rp = float(t.get("realized_pnl", 0.0))
                s_stat["realized_pnl"] += rp
                if rp > 0:
                    s_stat["wins"] += 1
                elif rp < 0:
                    s_stat["losses"] += 1

        for s_stat in strategy_stats.values():
            s_stat["net_pnl"] = round(s_stat["realized_pnl"] + s_stat["unrealized_pnl"], 2)
            s_stat["realized_pnl"] = round(s_stat["realized_pnl"], 2)
            s_stat["unrealized_pnl"] = round(s_stat["unrealized_pnl"], 2)
            cl = s_stat["closed_trades"]
            s_stat["win_rate_pct"] = round((s_stat["wins"] / cl * 100), 1) if cl > 0 else 0.0

        # Generate Equity Curve over dates
        sorted_trades = sorted(trades, key=lambda x: x.get("entry_date", ""))
        dates = sorted(list(set(t.get("entry_date", "") for t in sorted_trades if t.get("entry_date"))))
        
        equity_curve: List[Dict[str, Any]] = []
        running_equity = STARTING_PORTFOLIO_CAPITAL  # $100,000 starting portfolio capital
        cum_pnl = 0.0
        peak_equity = running_equity
        max_dd = 0.0

        for d in dates:
            day_trades = [t for t in trades if t.get("entry_date") == d or t.get("exit_date") == d]
            day_pnl = sum(float(t.get("realized_pnl", 0.0)) if t.get("exit_date") == d else float(t.get("unrealized_pnl", 0.0)) for t in day_trades)
            cum_pnl += day_pnl
            current_eq = running_equity + cum_pnl
            if current_eq > peak_equity:
                peak_equity = current_eq
            dd = ((peak_equity - current_eq) / peak_equity * 100) if peak_equity > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

            equity_curve.append({
                "date": d,
                "cum_pnl": round(cum_pnl, 2),
                "equity": round(current_eq, 2),
                "drawdown_pct": round(dd, 2),
            })

        # Most recent 20 trades
        recent_trades = sorted(trades, key=lambda x: (x.get("updated_at", ""), x.get("entry_date", "")), reverse=True)[:20]

        payload = {
            "timestamp": now_iso,
            "date": today_str,
            "total_trades": len(trades),
            "open_trades_count": len(open_trades),
            "closed_trades_count": len(closed_trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(win_rate, 1),
            "total_realized_pnl": round(total_realized, 2),
            "total_unrealized_pnl": round(total_unrealized, 2),
            "net_pnl": round(net_pnl, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "strategy_breakdown": strategy_stats,
            "equity_curve": equity_curve,
            "recent_trades": recent_trades,
        }

        # Export performance payload
        self._export_json("paper_trade_performance.json", payload)
        self._export_json("paper_trades_latest.json", {"timestamp": now_iso, "date": today_str, "trades": trades})

        return payload

    def _export_json(self, filename: str, payload: dict):
        local_path = self.base_dir / filename
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        self.web_data_dir.mkdir(parents=True, exist_ok=True)
        web_path = self.web_data_dir / filename
        try:
            with open(web_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            print(f"[PaperTradeManager] Wrote {filename} -> {web_path}")
        except Exception as e:
            print(f"[PaperTradeManager] Warning writing to web data dir: {e}")

    def run_daily_update(self) -> Dict[str, Any]:
        """
        Executes full daily cycle:
        1. Ingest any new strategy signals that fired today
        2. Evaluate daily stops, targets, and PnL
        3. Recalculate running performance & export JSONs
        """
        print("\n=== [PaperTradeManager] Running Daily Paper Trade Update ===")
        new_trades_count = self.ingest_strategy_signals()
        eval_stats = self.evaluate_daily_monitoring()
        perf = self.calculate_performance_summary()
        print(f"[PaperTradeManager] Completed: {new_trades_count} new trades, {eval_stats['open']} open, {eval_stats['closed']} closed. Net PnL: ${perf['net_pnl']:,.2f}")
        return perf


def process_daily_paper_trades() -> Dict[str, Any]:
    manager = PaperTradeManager()
    return manager.run_daily_update()


if __name__ == "__main__":
    manager = PaperTradeManager()
    manager.run_daily_update()
