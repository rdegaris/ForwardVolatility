"""
Test Finnhub API for earnings dates
Get your free API key from: https://finnhub.io/register
"""

import os
import sys
from earnings_checker import EarningsChecker

def test_finnhub():
    """Test Finnhub API connection and earnings data retrieval."""
    
    # Use hardcoded API key or environment variable
    api_key = os.environ.get('FINNHUB_API_KEY', 'd3rcvl1r01qopgh82hs0d3rcvl1r01qopgh82hsg')
    
    if not api_key:
        print("❌ FINNHUB_API_KEY not set!")
        print("\nTo set it:")
        print("  Windows (PowerShell): $env:FINNHUB_API_KEY='your_key_here'")
        print("  Windows (CMD):        set FINNHUB_API_KEY=your_key_here")
        print("  Mac/Linux:            export FINNHUB_API_KEY='your_key_here'")
        print("\nGet your free API key from: https://finnhub.io/register")
        sys.exit(1)
    
    print(f"✅ API Key found: {api_key[:10]}...")
    print("\nTesting Finnhub API with MAG7 stocks:")
    print("=" * 60)
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
    
    # Create checker with Finnhub enabled
    checker = EarningsChecker(use_finnhub=True)
    
    for ticker in test_tickers:
        earnings = checker.get_earnings_date(ticker)
        if earnings:
            print(f"✅ {ticker}: {earnings.strftime('%Y-%m-%d')}")
        else:
            print(f"⚠️  {ticker}: No earnings data found")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_finnhub()
