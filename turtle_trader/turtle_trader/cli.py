from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .data import read_ohlcv_csv
from .backtest import run_backtest
from .report import summarize


def cmd_backtest(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    bars = read_ohlcv_csv(args.csv)

    res = run_backtest(cfg, bars)
    summary = summarize(res.equity_curve, res.trades, cfg.account.starting_equity)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    res.equity_curve.to_csv(out_dir / "equity_curve.csv", index=False)

    # Trades ledger
    if res.trades:
        import pandas as pd

        df = pd.DataFrame([t.__dict__ for t in res.trades])
        df.to_csv(out_dir / "trades.csv", index=False)

    print("Summary")
    print(f"  Start equity: {summary.starting_equity:,.2f}")
    print(f"  End equity:   {summary.ending_equity:,.2f}")
    print(f"  Return:       {summary.total_return_pct:.2f}%")
    print(f"  Max DD:       {summary.max_drawdown_pct:.2f}%")
    print(f"  Sharpe:       {summary.sharpe_daily:.2f}")
    print(f"  Trades:       {summary.trades}")
    print(f"  Win rate:     {summary.win_rate_pct:.1f}%")
    print(f"  Profit fact:  {summary.profit_factor:.2f}")
    print(f"  Output dir:   {out_dir}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="turtle_trader")
    sub = p.add_subparsers(dest="cmd", required=True)

    bt = sub.add_parser("backtest", help="Run a Turtle backtest on OHLCV CSV")
    bt.add_argument("--config", required=True, help="Path to config JSON")
    bt.add_argument("--csv", required=True, help="Path to OHLCV CSV")
    bt.add_argument("--out", default="turtle_trader/out", help="Output directory")
    bt.set_defaults(func=cmd_backtest)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
