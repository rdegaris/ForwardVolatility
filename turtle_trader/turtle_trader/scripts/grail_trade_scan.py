"""
Grail Trade Scanner - "Holy Grail" setup from Street Smarts by Linda Raschke.

The setup occurs when:
1. 14-period ADX rises above 30 (strong trend)
2. Price retraces to the 20-period EMA
3. Entry on a pullback to EMA with stop below recent swing low/high

Target: Retest of the most recently formed high (for longs) or low (for shorts).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from dataclasses import dataclass

from turtle_trader.brokers.ib.client import IBClient, IBConfig
from turtle_trader.config import load_config
from turtle_trader.types import Bar


# Same clusters as trendorama for correlation tracking
CLUSTERS: dict[str, set[str]] = {
    "equities": {"ES", "NQ", "RTY"},
    "energies": {"CL", "NG", "HO", "RB"},
    "rates": {"ZB", "ZN", "ZF", "ZT"},
    "metals": {"GC", "SI", "HG"},
    "grains": {"ZC", "ZW", "ZS", "ZL"},
    "softs": {"KC", "SB", "CT"},
    "livestock": {"HE", "LE"},
    "fx": {"EUR", "JPY", "GBP", "CAD", "AUD"},
}


@dataclass
class GrailSignal:
    """A potential Grail Trade signal."""
    symbol: str
    exchange: str
    currency: str
    side: str  # "long" or "short"
    asof: str
    close: float
    ema20: float
    adx: float
    plus_di: float
    minus_di: float
    recent_high: float
    recent_low: float
    entry_zone: float
    stop_loss: float
    target: float
    distance_to_ema_pct: float
    eligible: bool
    reason: str


def _cluster_for_symbol(symbol: str) -> str:
    s = (symbol or "").upper()
    for name, symbols in CLUSTERS.items():
        if s in symbols:
            return name
    return "other"


def _bars_from_ib_df(df) -> list[Bar]:
    bars: list[Bar] = []
    if df is None or len(df) == 0:
        return bars

    for row in df.itertuples(index=False):
        dt = getattr(row, "date")
        try:
            d = datetime.strptime(str(dt), "%Y-%m-%d").date()
        except Exception:
            continue
        bars.append(
            Bar(
                dt=d,
                open=float(getattr(row, "open")),
                high=float(getattr(row, "high")),
                low=float(getattr(row, "low")),
                close=float(getattr(row, "close")),
                volume=(float(getattr(row, "volume")) if getattr(row, "volume", None) is not None else None),
            )
        )
    return bars


def compute_ema(closes: List[float], period: int) -> List[float]:
    """Compute Exponential Moving Average."""
    if len(closes) < period:
        return []
    
    multiplier = 2 / (period + 1)
    ema = [sum(closes[:period]) / period]  # Start with SMA
    
    for price in closes[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    
    # Pad with None for alignment
    return [None] * (period - 1) + ema


def compute_adx(bars: List[Bar], period: int = 14) -> tuple[List[float], List[float], List[float]]:
    """
    Compute ADX, +DI, and -DI.
    
    Returns:
        Tuple of (adx_values, plus_di_values, minus_di_values)
    """
    if len(bars) < period + 1:
        return [], [], []
    
    # Calculate True Range, +DM, -DM
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []
    
    for i in range(1, len(bars)):
        high = bars[i].high
        low = bars[i].low
        close_prev = bars[i-1].close
        high_prev = bars[i-1].high
        low_prev = bars[i-1].low
        
        # True Range
        tr = max(
            high - low,
            abs(high - close_prev),
            abs(low - close_prev)
        )
        tr_list.append(tr)
        
        # +DM and -DM
        up_move = high - high_prev
        down_move = low_prev - low
        
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0
        
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
    
    # Smooth using Wilder's method (similar to EMA but different formula)
    def wilder_smooth(data: List[float], period: int) -> List[float]:
        if len(data) < period:
            return []
        result = [sum(data[:period])]  # First value is sum
        for val in data[period:]:
            result.append(result[-1] - (result[-1] / period) + val)
        return result
    
    atr_smooth = wilder_smooth(tr_list, period)
    plus_dm_smooth = wilder_smooth(plus_dm_list, period)
    minus_dm_smooth = wilder_smooth(minus_dm_list, period)
    
    if not atr_smooth:
        return [], [], []
    
    # Calculate +DI and -DI
    plus_di = []
    minus_di = []
    dx_list = []
    
    for i in range(len(atr_smooth)):
        atr = atr_smooth[i]
        if atr == 0:
            plus_di.append(0)
            minus_di.append(0)
            dx_list.append(0)
        else:
            pdi = 100 * plus_dm_smooth[i] / atr
            mdi = 100 * minus_dm_smooth[i] / atr
            plus_di.append(pdi)
            minus_di.append(mdi)
            
            # DX
            di_sum = pdi + mdi
            if di_sum == 0:
                dx_list.append(0)
            else:
                dx_list.append(100 * abs(pdi - mdi) / di_sum)
    
    # Smooth DX to get ADX
    adx = wilder_smooth(dx_list, period)
    
    # Align arrays - pad with None
    offset = period
    adx_aligned = [None] * offset + [None] * (period - 1) + adx
    plus_di_aligned = [None] * offset + plus_di
    minus_di_aligned = [None] * offset + minus_di
    
    # Ensure same length as bars
    while len(adx_aligned) < len(bars):
        adx_aligned.append(None)
    while len(plus_di_aligned) < len(bars):
        plus_di_aligned.append(None)
    while len(minus_di_aligned) < len(bars):
        minus_di_aligned.append(None)
    
    return adx_aligned[:len(bars)], plus_di_aligned[:len(bars)], minus_di_aligned[:len(bars)]


def find_recent_swing(bars: List[Bar], lookback: int = 20) -> tuple[float, float]:
    """Find recent swing high and low."""
    if len(bars) < lookback:
        lookback = len(bars)
    
    recent = bars[-lookback:]
    high = max(b.high for b in recent)
    low = min(b.low for b in recent)
    return high, low


def scan_grail_setup(
    bars: List[Bar],
    symbol: str,
    exchange: str,
    currency: str,
    adx_threshold: float = 30.0,
    ema_period: int = 20,
    adx_period: int = 14,
    swing_lookback: int = 20,
    ema_touch_threshold_pct: float = 1.0,  # Within 1% of EMA
) -> Optional[GrailSignal]:
    """
    Scan for Grail Trade setup.
    
    Returns GrailSignal if setup is present, None otherwise.
    """
    if len(bars) < max(ema_period, adx_period * 2) + swing_lookback:
        return None
    
    closes = [b.close for b in bars]
    ema = compute_ema(closes, ema_period)
    adx, plus_di, minus_di = compute_adx(bars, adx_period)
    
    # Get latest values
    if not ema or ema[-1] is None:
        return None
    if not adx or adx[-1] is None:
        return None
    
    last_bar = bars[-1]
    last_ema = ema[-1]
    last_adx = adx[-1]
    last_plus_di = plus_di[-1] if plus_di and plus_di[-1] is not None else 0
    last_minus_di = minus_di[-1] if minus_di and minus_di[-1] is not None else 0
    
    recent_high, recent_low = find_recent_swing(bars, swing_lookback)
    
    # Distance from close to EMA
    distance_to_ema_pct = abs(last_bar.close - last_ema) / last_ema * 100
    
    # Check ADX threshold
    if last_adx < adx_threshold:
        return GrailSignal(
            symbol=symbol,
            exchange=exchange,
            currency=currency,
            side="none",
            asof=str(last_bar.dt),
            close=last_bar.close,
            ema20=last_ema,
            adx=last_adx,
            plus_di=last_plus_di,
            minus_di=last_minus_di,
            recent_high=recent_high,
            recent_low=recent_low,
            entry_zone=last_ema,
            stop_loss=0,
            target=0,
            distance_to_ema_pct=distance_to_ema_pct,
            eligible=False,
            reason=f"ADX too low ({last_adx:.1f} < {adx_threshold})"
        )
    
    # Determine trend direction from +DI/-DI
    is_uptrend = last_plus_di > last_minus_di
    
    # Check if price is near EMA (retracement)
    near_ema = distance_to_ema_pct <= ema_touch_threshold_pct
    
    # For uptrend: price should be at or slightly below EMA
    # For downtrend: price should be at or slightly above EMA
    
    if is_uptrend:
        # Long setup: ADX > 30, +DI > -DI, price near/at 20 EMA
        price_at_ema = last_bar.low <= last_ema * (1 + ema_touch_threshold_pct/100)
        
        if price_at_ema:
            # Calculate stop and target
            stop_loss = recent_low * 0.995  # Just under the recent swing low
            target = recent_high  # Target retest of recent high
            
            return GrailSignal(
                symbol=symbol,
                exchange=exchange,
                currency=currency,
                side="long",
                asof=str(last_bar.dt),
                close=last_bar.close,
                ema20=last_ema,
                adx=last_adx,
                plus_di=last_plus_di,
                minus_di=last_minus_di,
                recent_high=recent_high,
                recent_low=recent_low,
                entry_zone=last_bar.high,
                stop_loss=stop_loss,
                target=target,
                distance_to_ema_pct=distance_to_ema_pct,
                eligible=True,
                reason="Uptrend pullback to EMA - enter above bar high"
            )
        else:
            return GrailSignal(
                symbol=symbol,
                exchange=exchange,
                currency=currency,
                side="long",
                asof=str(last_bar.dt),
                close=last_bar.close,
                ema20=last_ema,
                adx=last_adx,
                plus_di=last_plus_di,
                minus_di=last_minus_di,
                recent_high=recent_high,
                recent_low=recent_low,
                entry_zone=last_ema,
                stop_loss=0,
                target=recent_high,
                distance_to_ema_pct=distance_to_ema_pct,
                eligible=False,
                reason=f"Waiting for pullback to EMA (price {distance_to_ema_pct:.1f}% away)"
            )
    else:
        # Short setup: ADX > 30, -DI > +DI, price near/at 20 EMA
        price_at_ema = last_bar.high >= last_ema * (1 - ema_touch_threshold_pct/100)
        
        if price_at_ema:
            # Calculate stop and target
            stop_loss = recent_high * 1.005  # Just above the recent swing high
            target = recent_low  # Target retest of recent low
            
            return GrailSignal(
                symbol=symbol,
                exchange=exchange,
                currency=currency,
                side="short",
                asof=str(last_bar.dt),
                close=last_bar.close,
                ema20=last_ema,
                adx=last_adx,
                plus_di=last_plus_di,
                minus_di=last_minus_di,
                recent_high=recent_high,
                recent_low=recent_low,
                entry_zone=last_bar.low,
                stop_loss=stop_loss,
                target=target,
                distance_to_ema_pct=distance_to_ema_pct,
                eligible=True,
                reason="Downtrend rally to EMA - enter below bar low"
            )
        else:
            return GrailSignal(
                symbol=symbol,
                exchange=exchange,
                currency=currency,
                side="short",
                asof=str(last_bar.dt),
                close=last_bar.close,
                ema20=last_ema,
                adx=last_adx,
                plus_di=last_plus_di,
                minus_di=last_minus_di,
                recent_high=recent_high,
                recent_low=recent_low,
                entry_zone=last_ema,
                stop_loss=0,
                target=recent_low,
                distance_to_ema_pct=distance_to_ema_pct,
                eligible=False,
                reason=f"Waiting for rally to EMA (price {distance_to_ema_pct:.1f}% away)"
            )


def _load_configs(configs_dir: Path) -> list[Path]:
    if not configs_dir.exists():
        return []
    return sorted([p for p in configs_dir.glob("*.json") if p.is_file()])


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Holy Grail Trade Scanner - Scans for ADX > 30 with pullback to 20 EMA. "
            "Uses the same futures basket as the Turtle/Trendorama system."
        )
    )
    ap.add_argument("--configs-dir", default="configs", help="Directory containing per-instrument config JSONs")
    ap.add_argument("--duration", default="1 Y", help="IB historical duration")
    ap.add_argument("--use-rth", action="store_true", help="Use regular trading hours only")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7498)
    ap.add_argument("--client-id", type=int, default=63)
    ap.add_argument("--out", default="", help="Optional JSON output path")
    ap.add_argument("--adx-threshold", type=float, default=30.0, help="ADX threshold for trend strength")
    ap.add_argument("--ema-touch-pct", type=float, default=2.0, help="Percent distance from EMA to count as 'at EMA'")

    args = ap.parse_args()

    cfg_paths = _load_configs(Path(args.configs_dir))
    if not cfg_paths:
        print(f"No configs found in: {args.configs_dir}")
        return 2

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    
    try:
        all_signals: list[dict[str, Any]] = []
        triggered: list[dict[str, Any]] = []

        for p in cfg_paths:
            cfg = load_config(p)
            inst = cfg.instrument

            print(f"[grail_scan] {inst.symbol}: fetching continuous daily bars ({args.duration})")
            try:
                cont = client.cont_future(inst.symbol, exchange=inst.exchange, currency=inst.currency)
                cont = client.qualify(cont)
                df = client.fetch_daily_bars(cont, duration=args.duration, use_rth=args.use_rth)
            except Exception as e:
                print(f"[grail_scan] {inst.symbol}: skip (history unavailable: {type(e).__name__}: {e})")
                continue

            bars = _bars_from_ib_df(df)
            if len(bars) < 50:
                print(f"[grail_scan] {inst.symbol}: skip (not enough bars: {len(bars)})")
                continue

            signal = scan_grail_setup(
                bars=bars,
                symbol=inst.symbol,
                exchange=inst.exchange,
                currency=inst.currency,
                adx_threshold=args.adx_threshold,
                ema_touch_threshold_pct=args.ema_touch_pct,
            )

            if signal:
                row = {
                    "symbol": signal.symbol,
                    "exchange": signal.exchange,
                    "currency": signal.currency,
                    "side": signal.side,
                    "asof": signal.asof,
                    "close": round(signal.close, 4),
                    "ema20": round(signal.ema20, 4),
                    "adx": round(signal.adx, 2),
                    "plus_di": round(signal.plus_di, 2),
                    "minus_di": round(signal.minus_di, 2),
                    "recent_high": round(signal.recent_high, 4),
                    "recent_low": round(signal.recent_low, 4),
                    "entry_zone": round(signal.entry_zone, 4),
                    "stop_loss": round(signal.stop_loss, 4) if signal.stop_loss else None,
                    "target": round(signal.target, 4) if signal.target else None,
                    "distance_to_ema_pct": round(signal.distance_to_ema_pct, 2),
                    "eligible": signal.eligible,
                    "reason": signal.reason,
                    "cluster": _cluster_for_symbol(signal.symbol),
                }
                all_signals.append(row)
                
                if signal.eligible:
                    triggered.append(row)

        # Sort by eligibility then symbol
        all_signals = sorted(all_signals, key=lambda r: (not r.get("eligible", False), r.get("symbol", "")))
        triggered = sorted(triggered, key=lambda r: r.get("symbol", ""))

        print("\n=== Holy Grail Trade: Signals Summary ===")
        print(f"Total scanned: {len(all_signals)}")
        print(f"Triggered (eligible): {len(triggered)}")
        
        if triggered:
            print("\n--- TRIGGERED SETUPS ---")
            for r in triggered:
                print(
                    f"{r['symbol']:>6} {str(r.get('side','')).upper():<6} "
                    f"ADX={r['adx']:.1f} +DI={r['plus_di']:.1f} -DI={r['minus_di']:.1f} "
                    f"Close={r['close']:.2f} EMA={r['ema20']:.2f} "
                    f"Target={r['target']:.2f} Stop={r['stop_loss']:.2f}"
                )
        
        # Show watching (strong ADX but not yet at EMA)
        watching = [s for s in all_signals if not s.get("eligible") and s.get("adx", 0) >= args.adx_threshold]
        if watching:
            print("\n--- WATCHING (ADX strong, waiting for EMA pullback) ---")
            for r in watching[:10]:  # Show top 10
                print(
                    f"{r['symbol']:>6} {str(r.get('side','')).upper():<6} "
                    f"ADX={r['adx']:.1f} Close={r['close']:.2f} EMA={r['ema20']:.2f} "
                    f"Dist={r['distance_to_ema_pct']:.1f}%"
                )

        if args.out:
            payload = {
                "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "date": datetime.utcnow().date().isoformat(),
                "system": "grail",
                "adx_threshold": args.adx_threshold,
                "ema_touch_pct": args.ema_touch_pct,
                "total_scanned": len(all_signals),
                "total_triggered": len(triggered),
                "signals": all_signals,
                "triggered": triggered,
            }
            Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"\nWrote: {args.out}")

        return 0
    finally:
        client.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
