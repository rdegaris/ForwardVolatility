from __future__ import annotations

import argparse
from pathlib import Path

from turtle_trader.brokers.ib.client import IBClient, IBConfig


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch daily futures history from Interactive Brokers")
    ap.add_argument("--symbol", required=True, help="e.g. ES")
    ap.add_argument("--exchange", default="CME")
    ap.add_argument("--currency", default="USD")
    ap.add_argument("--cont", action="store_true", help="Use continuous future (recommended for backtest data)")
    ap.add_argument("--month", help="Contract month YYYYMM (required if not --cont)")
    ap.add_argument("--duration", default="10 Y", help="e.g. '5 Y', '10 Y'")
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7497)
    ap.add_argument("--client-id", type=int, default=31)
    args = ap.parse_args()

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    try:
        if args.cont:
            c = client.cont_future(args.symbol, exchange=args.exchange, currency=args.currency)
        else:
            if not args.month:
                raise SystemExit("--month YYYYMM is required when not using --cont")
            c = client.future(args.symbol, last_trade_month=args.month, exchange=args.exchange, currency=args.currency)

        client.qualify(c)
        df = client.fetch_daily_bars(c, duration=args.duration)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Wrote {len(df)} rows -> {out}")
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
