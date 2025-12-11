"""
Earnings Checker Module
Fetches earnings dates using Finnhub API with Yahoo Finance fallback, and filters out stocks with upcoming earnings.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import os
import time

# Finnhub API key
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY', 'd3rcvl1r01qopgh82hs0d3rcvl1r01qopgh82hsg')


class EarningsChecker:
    """Check for upcoming earnings dates using Finnhub API with Yahoo Finance fallback."""
    
    def __init__(self, cache_file: str = "earnings_cache.json", use_yahoo_fallback: bool = True):
        self.cache: Dict[str, datetime] = {}
        self.cache_file = cache_file
        self.api_key = FINNHUB_API_KEY
        self.use_yahoo_fallback = use_yahoo_fallback
        self._load_cache()
    
    def _load_cache(self):
        """Load cached earnings dates from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # Convert string dates back to datetime
                    for ticker, date_str in data.items():
                        if date_str:
                            self.cache[ticker] = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception as e:
                print(f"Warning: Could not load earnings cache: {e}")
    
    def _save_cache(self):
        """Save cached earnings dates to file."""
        try:
            data = {}
            for ticker, dt in self.cache.items():
                data[ticker] = dt.strftime('%Y-%m-%d') if dt else None
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save earnings cache: {e}")
    
    def _get_earnings_from_yahoo(self, ticker: str) -> Optional[datetime]:
        """
        Get earnings date from Yahoo Finance using yfinance library.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            datetime of next earnings or None
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            
            if calendar and 'Earnings Date' in calendar:
                earnings_dates = calendar['Earnings Date']
                if earnings_dates and len(earnings_dates) > 0:
                    # yfinance returns date objects
                    earnings_date = earnings_dates[0]
                    
                    # Convert to datetime if needed
                    if hasattr(earnings_date, 'year'):
                        dt = datetime(earnings_date.year, earnings_date.month, earnings_date.day)
                    else:
                        dt = datetime.strptime(str(earnings_date), '%Y-%m-%d')
                    
                    # Only return if it's today or in the future
                    if dt >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                        return dt
            
            return None
            
        except Exception as e:
            print(f"    Warning: Could not fetch earnings from Yahoo for {ticker}: {e}")
            return None
    
    def get_earnings_date(self, ticker: str, days_ahead: int = 60) -> Optional[datetime]:
        """
        Get the next earnings date for a ticker using Finnhub API with IB fallback.
        
        Args:
            ticker: Stock symbol
            days_ahead: How many days ahead to look for earnings
            
        Returns:
            datetime of next earnings or None if not found
        """
        # Check cache first
        if ticker in self.cache:
            cached_date = self.cache[ticker]
            # If cached date is in the future or today, use it
            if cached_date and cached_date >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                return cached_date
            # If cached date is in the past, need to refresh
        
        # Try Finnhub first
        earnings_date = self._get_earnings_from_finnhub(ticker, days_ahead)
        
        # If Finnhub returns None, try Yahoo Finance as fallback
        if earnings_date is None and self.use_yahoo_fallback:
            earnings_date = self._get_earnings_from_yahoo(ticker)
            if earnings_date:
                print(f"    [Yahoo] Found earnings for {ticker}: {earnings_date.strftime('%Y-%m-%d')}")
        
        # Cache the result
        self.cache[ticker] = earnings_date
        self._save_cache()
        
        return earnings_date
    
    def _get_earnings_from_finnhub(self, ticker: str, days_ahead: int = 60) -> Optional[datetime]:
        """
        Get earnings date from Finnhub API.
        
        Args:
            ticker: Stock symbol
            days_ahead: How many days ahead to look
            
        Returns:
            datetime of next earnings or None
        """
        try:
            today = datetime.now().date()
            from_date = today.strftime('%Y-%m-%d')
            to_date = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            
            url = f"https://finnhub.io/api/v1/calendar/earnings?from={from_date}&to={to_date}&symbol={ticker}&token={self.api_key}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we have earnings data
                if data and 'earningsCalendar' in data and len(data['earningsCalendar']) > 0:
                    # Get the first (nearest) earnings date
                    earnings_entry = data['earningsCalendar'][0]
                    date_str = earnings_entry.get('date')
                    
                    if date_str:
                        return datetime.strptime(date_str, '%Y-%m-%d')
            
            return None
            
        except Exception as e:
            print(f"    Warning: Could not fetch earnings from Finnhub for {ticker}: {e}")
            return None
    
    def has_earnings_before(self, ticker: str, expiry_date: str) -> bool:
        """
        Check if a ticker has earnings before the given expiry date.
        
        Args:
            ticker: Stock symbol
            expiry_date: Expiry date in YYYYMMDD format
            
        Returns:
            True if earnings are before expiry, False otherwise
        """
        earnings_date = self.get_earnings_date(ticker)
        if not earnings_date:
            return False
        
        # Parse expiry date
        expiry = datetime.strptime(expiry_date, '%Y%m%d')
        
        # Check if earnings are before or on expiry
        return earnings_date.date() <= expiry.date()
    
    def has_earnings_in_window(self, ticker: str, front_expiry: str, back_expiry: str) -> bool:
        """
        Check if a ticker has earnings between front and back expiry (the danger zone).
        Also returns True if earnings are BEFORE front expiry (already happened or imminent).
        
        Args:
            ticker: Stock symbol
            front_expiry: Front month expiry in YYYYMMDD format
            back_expiry: Back month expiry in YYYYMMDD format
            
        Returns:
            True if earnings fall in the danger zone, False otherwise
        """
        earnings_date = self.get_earnings_date(ticker)
        if not earnings_date:
            return False
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        front = datetime.strptime(front_expiry, '%Y%m%d')
        back = datetime.strptime(back_expiry, '%Y%m%d')
        
        # Danger zone: earnings between today and back expiry
        # This catches:
        # 1. Earnings happening today (before you can trade)
        # 2. Earnings between now and front expiry
        # 3. Earnings between front and back expiry
        return today <= earnings_date <= back
    
    def get_days_to_earnings(self, ticker: str) -> Optional[int]:
        """Get number of days until earnings."""
        earnings_date = self.get_earnings_date(ticker)
        if not earnings_date:
            return None
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        delta = earnings_date - today
        return delta.days
    
    def filter_opportunities(self, opportunities: List[Dict], verbose: bool = False) -> List[Dict]:
        """
        Filter out opportunities that have earnings in the trading window.
        
        Args:
            opportunities: List of opportunity dicts with 'ticker', 'expiry1', 'expiry2'
            verbose: Print details about filtered stocks
            
        Returns:
            Filtered list of opportunities
        """
        filtered = []
        removed_count = 0
        
        for opp in opportunities:
            ticker = opp.get('ticker')
            front_expiry = opp.get('expiry1')
            back_expiry = opp.get('expiry2')
            
            if not all([ticker, front_expiry, back_expiry]):
                filtered.append(opp)
                continue
            
            if self.has_earnings_in_window(ticker, front_expiry, back_expiry):
                removed_count += 1
                earnings_date = self.get_earnings_date(ticker)
                days = self.get_days_to_earnings(ticker)
                if verbose:
                    print(f"    ⚠️  REMOVED {ticker}: Earnings on {earnings_date.strftime('%Y-%m-%d')} ({days} days) - in trading window!")
            else:
                filtered.append(opp)
        
        if verbose and removed_count > 0:
            print(f"    Removed {removed_count} opportunities due to earnings in trading window")
        
        return filtered
    
    def check_batch(self, tickers: List[str]) -> Dict[str, Optional[datetime]]:
        """
        Check earnings dates for a batch of tickers.
        
        Args:
            tickers: List of stock symbols
            
        Returns:
            Dict mapping ticker to earnings date (or None)
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.get_earnings_date(ticker)
        return results


# Test the module
if __name__ == "__main__":
    print("Testing Earnings Checker...\n")
    
    checker = EarningsChecker()
    
    # Test some tickers
    test_tickers = ['AAPL', 'MSFT', 'AEO', 'NVDA', 'AMD']
    
    for ticker in test_tickers:
        earnings_date = checker.get_earnings_date(ticker)
        days = checker.get_days_to_earnings(ticker)
        
        if earnings_date:
            print(f"{ticker}: Earnings on {earnings_date.strftime('%Y-%m-%d')} ({days} days away)")
        else:
            print(f"{ticker}: No earnings date found")
    
    print("\n✅ Earnings checker is working!")
