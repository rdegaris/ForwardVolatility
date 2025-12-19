from __future__ import annotations

import argparse

from turtle_trader.brokers.ib.client import IBClient, IBConfig


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve current front-month IB futures contract")
    ap.add_argument("--symbol", required=True, help="e.g. ES")
    ap.add_argument("--exchange", default="CME")
    ap.add_argument("--currency", default="USD")
    ap.add_argument("--min-dte", type=int, default=10, help="Minimum days-to-expiry buffer")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7497)
    ap.add_argument("--client-id", type=int, default=41)
    args = ap.parse_args()

    client = IBClient(IBConfig(host=args.host, port=args.port, client_id=args.client_id))
    client.connect()
    try:
        c = client.resolve_front_month(
            symbol=args.symbol,
            exchange=args.exchange,
            currency=args.currency,
            min_days_to_expiry=args.min_dte,
        )
        print("Resolved front month:")
        print(f"  symbol: {getattr(c, 'symbol', None)}")
        print(f"  localSymbol: {getattr(c, 'localSymbol', None)}")
        print(f"  conId: {getattr(c, 'conId', None)}")
        print(f"  lastTradeDateOrContractMonth: {getattr(c, 'lastTradeDateOrContractMonth', None)}")
        print(f"  exchange: {getattr(c, 'exchange', None)}")
        print(f"  currency: {getattr(c, 'currency', None)}")
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
