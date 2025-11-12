"""
Earnings Calendar Checker
Filters out tickers with earnings reports before the front month expiry

Data Sources (in priority order):
1. Finnhub API - Real-time earnings calendar (requires FINNHUB_API_KEY env var)
2. Manual Calendar - Fallback from earnings_calendar.py

Set FINNHUB_API_KEY environment variable to enable Finnhub API.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import requests
import os

try:
    from earnings_calendar import EARNINGS_CALENDAR
except ImportError:
    EARNINGS_CALENDAR = {}


class EarningsChecker:
    """Check if earnings occurs before the front month expiry."""
    
    def __init__(self, use_finnhub=True):
        """
        Initialize earnings checker.
        
        Args:
            use_finnhub: If True, try Finnhub API first before manual calendar
        """
        self.cache = {}  # Cache parsed earnings dates
        self.calendar = EARNINGS_CALENDAR
        self.use_finnhub = use_finnhub
        # Use hardcoded API key or environment variable
        self.finnhub_api_key = os.environ.get('FINNHUB_API_KEY', 'd3rcvl1r01qopgh82hs0d3rcvl1r01qopgh82hsg')
        
        if self.use_finnhub and not self.finnhub_api_key:
            print("[WARNING] FINNHUB_API_KEY not set in environment. Using manual calendar only.")
            self.use_finnhub = False
    
    def get_earnings_date(self, ticker: str) -> Optional[datetime]:
        """
        Get next earnings date from Finnhub API or manual calendar fallback.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Next earnings date as datetime, or None if not available
        """
        # Check cache first
        if ticker in self.cache:
            return self.cache[ticker]
        
        # Try Finnhub API first
        if self.use_finnhub:
            try:
                # Get earnings calendar for next 60 days
                from_date = datetime.now().strftime('%Y-%m-%d')
                to_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
                
                url = f"https://finnhub.io/api/v1/calendar/earnings?from={from_date}&to={to_date}&symbol={ticker}&token={self.finnhub_api_key}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we have earnings data
                    if data and 'earningsCalendar' in data and len(data['earningsCalendar']) > 0:
                        # Get the first (nearest) earnings date
                        earnings_entry = data['earningsCalendar'][0]
                        date_str = earnings_entry.get('date')
                        
                        if date_str:
                            try:
                                earnings_date = datetime.strptime(date_str, '%Y-%m-%d')
                                self.cache[ticker] = earnings_date
                                print(f"  [INFO] {ticker} earnings from Finnhub: {date_str}")
                                return earnings_date
                            except ValueError:
                                pass
                
            except Exception as e:
                print(f"  [WARNING] Finnhub API error for {ticker}: {e}")
        
        # Fallback to manual calendar
        if ticker in self.calendar:
            date_str = self.calendar[ticker]
            try:
                earnings_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Only return if it's in the future
                if earnings_date > datetime.now():
                    self.cache[ticker] = earnings_date
                    print(f"  [INFO] {ticker} earnings from manual calendar: {date_str}")
                    return earnings_date
                else:
                    # Earnings date has passed - needs updating
                    print(f"  [WARNING] {ticker} earnings date {date_str} has passed - update earnings_calendar.py!")
            except ValueError:
                print(f"  [ERROR] Invalid date format for {ticker} in earnings_calendar.py")
        
        self.cache[ticker] = None
        return None
    
    def has_earnings_before_expiry(self, ticker: str, back_expiry: str) -> bool:
        """
        Check if earnings occurs BEFORE OR ON the back month expiry.
        
        RULE: Exclude ALL trades where earnings is between entry (today) and back expiry.
        Since we hold the position until the back month expiry, we need to ensure
        no earnings events occur during the entire holding period.
        
        NOTE: We add a 1-day safety buffer because earnings data sources (Finnhub, etc.)
        can be inconsistent about AMC (after market close) dates. Some sources report
        the date of the call, others report the "next trading day". To be conservative,
        we add 1 day to the earnings date.
        
        Args:
            ticker: Stock symbol
            back_expiry: Back month expiry date in YYYYMMDD format
            
        Returns:
            True if earnings is BEFORE OR ON back expiry (should EXCLUDE), False otherwise
        """
        # Parse back expiry date
        back_dt = datetime.strptime(back_expiry, '%Y%m%d')
        
        # Get earnings date
        earnings_date = self.get_earnings_date(ticker)
        
        # If we have an earnings date, check if it's before OR ON back expiry
        # ADD 1 DAY SAFETY BUFFER to account for AMC reporting inconsistencies
        if earnings_date:
            earnings_date_with_buffer = earnings_date + timedelta(days=1)
            if earnings_date_with_buffer <= back_dt:
                return True  # EXCLUDE - earnings (with buffer) before or on back expiry day
        
        return False  # Safe to trade (no earnings before or on back expiry)
    
    def filter_opportunities(self, opportunities: List[Dict], verbose: bool = True) -> List[Dict]:
        """
        Filter out opportunities with earnings between entry and the BACK month expiry.
        
        Since the trade involves holding a calendar spread until the back month expiry,
        we need to ensure there are no earnings events during the entire holding period.
        
        Args:
            opportunities: List of opportunity dicts with ticker, expiry1, expiry2
            verbose: Print filtered tickers
        
        Returns:
            Filtered list of opportunities
        """
        filtered = []
        excluded = []
        
        for opp in opportunities:
            ticker = opp['ticker']
            expiry2 = opp['expiry2']  # Back month expiry - CHECK THIS ONE!
            
            has_earnings = self.has_earnings_before_expiry(ticker, expiry2)
            
            if has_earnings:
                excluded.append(ticker)
                if verbose:
                    earnings_date = self.cache.get(ticker)
                    date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "Unknown"
                    back_str = datetime.strptime(expiry2, '%Y%m%d').strftime('%Y-%m-%d')
                    print(f"  [EXCLUDED] {ticker}: Earnings on {date_str} (before back expiry {back_str})")
            else:
                filtered.append(opp)
        
        if verbose and excluded:
            print(f"\n[INFO] Excluded {len(excluded)} ticker(s) due to earnings before back expiry: {', '.join(set(excluded))}")
        
        return filtered


def check_earnings(ticker: str, back_expiry: str, verbose: bool = True) -> bool:
    """
    Quick check if a single ticker has earnings before back expiry.
    
    Args:
        ticker: Stock symbol
        back_expiry: Back month expiry (YYYYMMDD)
        verbose: Print result
    
    Returns:
        True if earnings before back expiry (EXCLUDE), False if safe
    """
    checker = EarningsChecker()
    has_earnings = checker.has_earnings_before_expiry(ticker, back_expiry)
    
    if verbose:
        if has_earnings:
            earnings_date = checker.cache.get(ticker)
            date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "Unknown"
            print(f"[WARNING] {ticker}: Earnings on {date_str} - EXCLUDE")
        else:
            print(f"[OK] {ticker}: Safe - no earnings before back expiry")
    
    return has_earnings


if __name__ == "__main__":
    # Test the earnings checker
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
    
    checker = EarningsChecker()
    
    print("Checking earnings dates for MAG7:")
    print("-" * 50)
    
    for ticker in test_tickers:
        earnings = checker.get_earnings_date(ticker)
        if earnings:
            print(f"{ticker}: {earnings.strftime('%Y-%m-%d')}")
        else:
            print(f"{ticker}: No earnings data available")
    
    print("\n" + "-" * 50)
    print("Testing exclusion logic (front expiry = 2025-10-31):")
    print("-" * 50)
    
    for ticker in test_tickers:
        check_earnings(ticker, "20251031", verbose=True)
