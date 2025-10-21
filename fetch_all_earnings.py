"""
Fetch earnings dates for all MAG7 and NASDAQ 100 tickers from Finnhub
"""

from earnings_checker import EarningsChecker
from nasdaq100 import NASDAQ_100

print("=" * 80)
print("FETCHING ALL EARNINGS DATES FROM FINNHUB API")
print("=" * 80)
print()

# Initialize checker with Finnhub
checker = EarningsChecker(use_finnhub=True)

# MAG7 stocks
mag7 = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']

print("\n" + "=" * 80)
print("MAG7 EARNINGS DATES")
print("=" * 80)

for ticker in mag7:
    earnings_date = checker.get_earnings_date(ticker)
    if earnings_date:
        print(f"  {ticker:6s} → {earnings_date.strftime('%Y-%m-%d')}")
    else:
        print(f"  {ticker:6s} → NOT FOUND")

# NASDAQ 100
print("\n" + "=" * 80)
print("NASDAQ 100 EARNINGS DATES")
print("=" * 80)

success_count = 0
fail_count = 0

for ticker in sorted(NASDAQ_100):
    earnings_date = checker.get_earnings_date(ticker)
    if earnings_date:
        print(f"  {ticker:6s} → {earnings_date.strftime('%Y-%m-%d')}")
        success_count += 1
    else:
        print(f"  {ticker:6s} → NOT FOUND")
        fail_count += 1

print("\n" + "=" * 80)
print(f"SUMMARY: {success_count} found, {fail_count} not found out of {len(NASDAQ_100)} tickers")
print("=" * 80)
