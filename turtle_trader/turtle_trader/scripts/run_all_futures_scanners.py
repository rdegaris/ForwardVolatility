from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import sys
from pathlib import Path

# Fix module imports
script_path = Path(__file__).resolve()
calc_root = script_path.parents[3]       # forward-volatility-calculator
workspace_root = calc_root.parent         # Forward Volatility
web_data_dir = workspace_root / "forward-volatility-web" / "public" / "data"

if str(calc_root / "turtle_trader") not in sys.path:
    sys.path.insert(0, str(calc_root / "turtle_trader"))
if str(calc_root) not in sys.path:
    sys.path.insert(0, str(calc_root))

from turtle_trader.data import read_ohlcv_csv
from turtle_trader.config import load_config, TurtleConfig, AccountConfig, StrategyConfig, InstrumentConfig
from turtle_trader.live import compute_levels, compute_unit_qty
from turtle_trader.risk import round_to_tick
from turtle_trader.taylor import analyze_taylor_cycle
from turtle_trader.scripts.fetch_futures_yfinance import fetch_futures_data, FUTURES_MAP
from turtle_trader.scripts.grail_trade_scan import scan_grail_setup, _cluster_for_symbol as grail_cluster


def export_json(filename: str, payload: dict):
    calc_out = calc_root / "turtle_trader" / filename
    web_out = web_data_dir / filename

    with open(calc_out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    web_data_dir.mkdir(parents=True, exist_ok=True)
    with open(web_out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"  [EXPORT] Wrote {filename} (Date: {payload.get('date')})")


def run_taylor(data_dir: Path):
    print("\n--- Running Taylor Trading Technique Scanner ---")
    signals = []
    buy_count = 0
    sell_count = 0
    short_count = 0
    latest_date = datetime.now().strftime("%Y-%m-%d")

    for sym in FUTURES_MAP.keys():
        csv_path = data_dir / f"{sym}.csv"
        if not csv_path.exists():
            continue
        bars = read_ohlcv_csv(csv_path)
        if not bars or len(bars) < 5:
            continue
        sig = analyze_taylor_cycle(bars, sym)
        if sig:
            signals.append(asdict(sig))
            latest_date = sig.asof
            if sig.cycle_phase == "BUY_DAY":
                buy_count += 1
            elif sig.cycle_phase == "SELL_DAY":
                sell_count += 1
            elif sig.cycle_phase == "SELL_SHORT_DAY":
                short_count += 1

    payload = {
        "date": latest_date,
        "timestamp": datetime.now().isoformat(),
        "total_scanned": len(signals),
        "summary": {
            "buy_day_count": buy_count,
            "sell_day_count": sell_count,
            "sell_short_day_count": short_count,
        },
        "signals": signals,
    }
    export_json("taylor_signals_latest.json", payload)


def run_grail(data_dir: Path):
    print("\n--- Running Grail Trade Scanner ---")
    all_signals = []
    triggered = []
    latest_date = datetime.now().strftime("%Y-%m-%d")

    for sym in FUTURES_MAP.keys():
        csv_path = data_dir / f"{sym}.csv"
        if not csv_path.exists():
            continue
        bars = read_ohlcv_csv(csv_path)
        if not bars or len(bars) < 30:
            continue

        sig = scan_grail_setup(bars=bars, symbol=sym, exchange="CME", currency="USD", adx_threshold=25.0, ema_touch_threshold_pct=2.5)
        if sig:
            row = {
                "symbol": sig.symbol,
                "exchange": sig.exchange,
                "currency": sig.currency,
                "side": sig.side,
                "asof": sig.asof,
                "close": round(sig.close, 4),
                "ema20": round(sig.ema20, 4),
                "adx": round(sig.adx, 2),
                "plus_di": round(sig.plus_di, 2),
                "minus_di": round(sig.minus_di, 2),
                "recent_high": round(sig.recent_high, 4),
                "recent_low": round(sig.recent_low, 4),
                "entry_zone": round(sig.entry_zone, 4),
                "stop_loss": round(sig.stop_loss, 4) if sig.stop_loss else None,
                "target": round(sig.target, 4) if sig.target else None,
                "distance_to_ema_pct": round(sig.distance_to_ema_pct, 2),
                "eligible": sig.eligible,
                "reason": sig.reason,
                "cluster": grail_cluster(sig.symbol),
            }
            latest_date = sig.asof
            all_signals.append(row)
            if sig.eligible and sig.side != "none":
                triggered.append(row)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "date": latest_date,
        "system": "grail",
        "adx_threshold": 25.0,
        "ema_touch_pct": 2.5,
        "total_scanned": len(all_signals),
        "total_triggered": len(triggered),
        "signals": all_signals,
        "triggered": triggered,
    }
    export_json("grail_signals_latest.json", payload)


def create_default_turtle_config(sym: str) -> TurtleConfig:
    return TurtleConfig(
        account=AccountConfig(
            starting_equity=100000.0,
            risk_per_unit_pct=1.0,
            max_units=4,
            pyramid_add_every_N=0.5,
            stop_loss_N=2.0,
            commission_per_contract=2.5,
            slippage_ticks=1,
        ),
        strategy=StrategyConfig(
            atr_period=20,
            system="S2",
            s1_entry_breakout=20,
            s1_exit_breakout=10,
            s2_entry_breakout=55,
            s2_exit_breakout=20,
            direction="both",
        ),
        instrument=InstrumentConfig(
            symbol=sym,
            point_value=50.0,
            tick_size=0.25,
            exchange="CME",
            currency="USD",
        ),
    )


def run_trendorama(data_dir: Path):
    print("\n--- Running Trendorama Breakout Scanner ---")
    configs_dir = calc_root / "turtle_trader" / "configs"
    triggered = []
    rows = []
    latest_date = datetime.now().strftime("%Y-%m-%d")

    for sym in FUTURES_MAP.keys():
        cfg_file = configs_dir / f"{sym}.json"
        csv_path = data_dir / f"{sym}.csv"
        if not csv_path.exists():
            continue

        bars = read_ohlcv_csv(csv_path)
        if not bars or len(bars) < 30:
            continue

        if cfg_file.exists():
            try:
                cfg = load_config(cfg_file)
            except Exception:
                cfg = create_default_turtle_config(sym)
        else:
            cfg = create_default_turtle_config(sym)

        levels = compute_levels(cfg, bars)
        last = bars[-1]
        latest_date = str(last.dt)

        long_trig = levels.long_entry is not None and last.high >= float(levels.long_entry)
        short_trig = levels.short_entry is not None and last.low <= float(levels.short_entry)

        unit_qty = int(compute_unit_qty(cfg, equity=float(cfg.account.starting_equity), N=float(levels.N)))

        row = {
            "symbol": sym,
            "exchange": cfg.instrument.exchange,
            "currency": cfg.instrument.currency,
            "asof": str(levels.asof),
            "N": float(levels.N),
            "last_close": float(last.close),
            "long_entry": float(levels.long_entry) if levels.long_entry else None,
            "short_entry": float(levels.short_entry) if levels.short_entry else None,
            "unit_qty": unit_qty,
        }
        rows.append(row)

        if long_trig and levels.long_entry:
            triggered.append({
                "symbol": sym,
                "side": "long",
                "asof": str(levels.asof),
                "last_close": float(last.close),
                "entry_stop": float(levels.long_entry),
                "stop_loss": round(float(levels.long_entry) - 2 * float(levels.N), 4),
                "eligible": True,
                "notes": "55-day breakout trigger on latest bar",
            })
        if short_trig and levels.short_entry:
            triggered.append({
                "symbol": sym,
                "side": "short",
                "asof": str(levels.asof),
                "last_close": float(last.close),
                "entry_stop": float(levels.short_entry),
                "stop_loss": round(float(levels.short_entry) + 2 * float(levels.N), 4),
                "eligible": True,
                "notes": "55-day breakout trigger on latest bar",
            })

    payload = {
        "timestamp": datetime.now().isoformat(),
        "date": latest_date,
        "system": "S2",
        "total_scanned": len(rows),
        "triggered": triggered,
        "rows": rows,
    }
    export_json("turtle_signals_latest.json", payload)


def run_odid(data_dir: Path):
    print("\n--- Running OD/ID Breakout Scanner ---")
    alerts = []
    triggered = []
    latest_date = datetime.now().strftime("%Y-%m-%d")

    for sym in FUTURES_MAP.keys():
        csv_path = data_dir / f"{sym}.csv"
        if not csv_path.exists():
            continue
        bars = read_ohlcv_csv(csv_path)
        if not bars or len(bars) < 5:
            continue

        b0 = bars[-1]
        b1 = bars[-2]
        b2 = bars[-3] if len(bars) > 2 else None
        latest_date = str(b0.dt)

        is_inside_day = b2 is not None and (b1.high <= b2.high and b1.low >= b2.low)
        is_outside_day = b2 is not None and (b1.high > b2.high and b1.low < b2.low)

        if is_inside_day or is_outside_day:
            pattern = "INSIDE_DAY" if is_inside_day else "OUTSIDE_DAY"
            alerts.append({
                "symbol": sym,
                "pattern": pattern,
                "asof": str(b1.dt),
                "high_trigger": b1.high,
                "low_trigger": b1.low,
                "last_close": b0.close,
            })

            if b0.high > b1.high:
                triggered.append({
                    "symbol": sym,
                    "side": "long",
                    "asof": str(b0.dt),
                    "entry_stop": b1.high,
                    "stop_loss": b1.low,
                    "eligible": True,
                    "notes": f"Confirmed {pattern} upside breakout",
                })
            elif b0.low < b1.low:
                triggered.append({
                    "symbol": sym,
                    "side": "short",
                    "asof": str(b0.dt),
                    "entry_stop": b1.low,
                    "stop_loss": b1.high,
                    "eligible": True,
                    "notes": f"Confirmed {pattern} downside breakout",
                })

    signals_payload = {
        "timestamp": datetime.now().isoformat(),
        "date": latest_date,
        "total_armed": len(alerts),
        "triggered": triggered,
    }
    alerts_payload = {
        "timestamp": datetime.now().isoformat(),
        "date": latest_date,
        "total_alerts": len(alerts),
        "alerts": alerts,
    }
    export_json("odid_signals_latest.json", signals_payload)
    export_json("odid_alerts_latest.json", alerts_payload)


def main():
    print("=== STARTING FULL FUTURES EOD SCANNER ===")
    data_dir = calc_root / "turtle_trader" / "data"

    fetch_futures_data(output_dirs=[data_dir])

    run_taylor(data_dir)
    run_grail(data_dir)
    run_trendorama(data_dir)
    run_odid(data_dir)

    print("\n=== FULL FUTURES SCANNER FINISHED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
