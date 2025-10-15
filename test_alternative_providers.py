"""
Alternative Option Data Scanner using multiple providers
Tries different free data sources when one fails
"""

import math
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import requests
from bs4 import BeautifulSoup


def calculate_forward_vol(dte1: float, iv1: float, dte2: float, iv2: float) -> Optional[Dict]:
    """Calculate forward volatility and forward factor."""
    if dte1 < 0 or dte2 < 0 or iv1 < 0 or iv2 < 0:
        return None
    if dte2 <= dte1:
        return None
    
    T1 = dte1 / 365.0
    T2 = dte2 / 365.0
    s1 = iv1 / 100.0
    s2 = iv2 / 100.0
    
    tv1 = (s1 ** 2) * T1
    tv2 = (s2 ** 2) * T2
    
    denom = T2 - T1
    if denom <= 0:
        return None
    
    fwd_var = (tv2 - tv1) / denom
    
    if fwd_var < 0:
        return None
    
    fwd_sigma = math.sqrt(fwd_var)
    
    if fwd_sigma == 0.0:
        ff_ratio = None
    else:
        ff_ratio = (s1 - fwd_sigma) / fwd_sigma
    
    return {
        'fwd_sigma': fwd_sigma,
        'fwd_sigma_pct': fwd_sigma * 100,
        'ff_ratio': ff_ratio,
        'ff_pct': ff_ratio * 100 if ff_ratio is not None else None
    }


# Provider 1: Yahoo Finance Alternative (via different method)
def get_yahoo_data_alt(ticker: str):
    """Alternative Yahoo Finance method using download."""
    try:
        import yfinance as yf
        
        # Try using download which sometimes works when Ticker fails
        df = yf.download(ticker, period='1d', progress=False)
        if not df.empty:
            price = df['Close'].iloc[-1]
            return {'price': price, 'source': 'Yahoo Finance (download)'}
    except Exception as e:
        pass
    return None


# Provider 2: Alpha Vantage (free tier - requires API key)
def get_alphavantage_data(ticker: str, api_key: str = 'demo'):
    """Fetch data from Alpha Vantage (free tier available)."""
    try:
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'Global Quote' in data and '05. price' in data['Global Quote']:
            price = float(data['Global Quote']['05. price'])
            return {'price': price, 'source': 'Alpha Vantage'}
    except Exception as e:
        pass
    return None


# Provider 3: Yahoo Finance via web scraping (backup)
def get_yahoo_scrape(ticker: str):
    """Scrape Yahoo Finance website directly."""
    try:
        url = f'https://finance.yahoo.com/quote/{ticker}'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Parse the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find price - this is fragile and may break
            price_element = soup.find('fin-streamer', {'data-symbol': ticker, 'data-field': 'regularMarketPrice'})
            if price_element:
                price = float(price_element.get('value', 0))
                if price > 0:
                    return {'price': price, 'source': 'Yahoo Finance (web)'}
    except Exception as e:
        pass
    return None


# Provider 4: Finnhub (free tier)
def get_finnhub_data(ticker: str, api_key: str = 'demo'):
    """Fetch data from Finnhub (free tier available)."""
    try:
        url = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'c' in data and data['c'] > 0:  # 'c' is current price
            return {'price': data['c'], 'source': 'Finnhub'}
    except Exception as e:
        pass
    return None


def get_stock_price(ticker: str) -> Optional[Dict]:
    """Try multiple providers to get stock price."""
    print(f"\nTrying to fetch {ticker} price from multiple sources...")
    
    providers = [
        ('Yahoo Alt', lambda: get_yahoo_data_alt(ticker)),
        ('Yahoo Web', lambda: get_yahoo_scrape(ticker)),
        ('Finnhub', lambda: get_finnhub_data(ticker)),
        ('Alpha Vantage', lambda: get_alphavantage_data(ticker)),
    ]
    
    for name, provider_func in providers:
        try:
            print(f"  Trying {name}...", end=' ')
            result = provider_func()
            if result:
                print(f"SUCCESS - ${result['price']:.2f}")
                return result
            else:
                print("No data")
        except Exception as e:
            print(f"Error: {str(e)[:50]}")
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"  All providers failed for {ticker}")
    return None


def test_tsla():
    """Test TSLA data fetch from alternative sources."""
    print("=" * 80)
    print("TESTING ALTERNATIVE DATA PROVIDERS FOR TSLA")
    print("=" * 80)
    
    result = get_stock_price('TSLA')
    
    if result:
        print("\n" + "=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print(f"Ticker: TSLA")
        print(f"Price: ${result['price']:.2f}")
        print(f"Source: {result['source']}")
        print("\nYou can now use this provider for option data scanning.")
        print("\nNOTE: For full option chain data with IV, you'll need:")
        print("  - Polygon.io API (free tier: 5 requests/min)")
        print("  - Tradier API (free with account)")
        print("  - Interactive Brokers TWS API (requires account)")
        print("  - TD Ameritrade API (free with account)")
    else:
        print("\n" + "=" * 80)
        print("ALL PROVIDERS FAILED")
        print("=" * 80)
        print("Recommendations:")
        print("1. Check your internet connection")
        print("2. Wait 5-10 minutes (rate limits may have been hit)")
        print("3. Get a free API key from:")
        print("   - Alpha Vantage: https://www.alphavantage.co/support/#api-key")
        print("   - Finnhub: https://finnhub.io/register")
        print("   - Polygon.io: https://polygon.io/")
        print("4. Use broker APIs (TD Ameritrade, Interactive Brokers)")
    
    print("=" * 80)


if __name__ == "__main__":
    # Install required packages if needed
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.run(['pip', 'install', 'requests', 'beautifulsoup4', 'lxml'], check=False)
        import requests
        from bs4 import BeautifulSoup
    
    test_tsla()
