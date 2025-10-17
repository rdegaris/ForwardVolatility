"""
Earnings Calendar Checker
Filters out tickers with earnings reports before the front month expiry
Uses manually maintained earnings calendar for reliability
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List

try:
    from earnings_calendar import EARNINGS_CALENDAR
except ImportError:
    EARNINGS_CALENDAR = {}


class EarningsChecker:
    """Check if earnings occurs before the front month expiry."""
    
    def __init__(self):
        """Initialize earnings checker with manual earnings calendar."""
        self.cache = {}  # Cache parsed earnings dates
        self.calendar = EARNINGS_CALENDAR
    
    def get_earnings_date(self, ticker: str) -> Optional[datetime]:
        """
        Get next earnings date from manually maintained calendar.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Next earnings date as datetime, or None if not available
        """
        # Check cache first
        if ticker in self.cache:
            return self.cache[ticker]
        
        # Check manual calendar
        if ticker in self.calendar:
            date_str = self.calendar[ticker]
            try:
                earnings_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Only return if it's in the future
                if earnings_date > datetime.now():
                    self.cache[ticker] = earnings_date
                    return earnings_date
                else:
                    # Earnings date has passed - needs updating
                    print(f"  ⚠️  WARNING: {ticker} earnings date {date_str} has passed - update earnings_calendar.py!")
            except ValueError:
                print(f"  ⚠️  ERROR: Invalid date format for {ticker} in earnings_calendar.py")
        
        self.cache[ticker] = None
        return None
    
    def has_earnings_before_expiry(self, ticker: str, front_expiry: str) -> bool:
        """
        Check if earnings occurs BEFORE OR ON the front month expiry.
        
        RULE: Exclude ALL trades where earnings is before OR ON front expiry date.
        No buffer, no tolerance - if earnings is same day or before front expiry, EXCLUDE.
        
        Args:
            ticker: Stock symbol
            front_expiry: Front month expiry date in YYYYMMDD format
            
        Returns:
            True if earnings is BEFORE OR ON front expiry (should EXCLUDE), False otherwise
        """
        # Parse front expiry date
        front_dt = datetime.strptime(front_expiry, '%Y%m%d')
        
        # Get earnings date
        earnings_date = self.get_earnings_date(ticker)
        
        # If we have an earnings date, check if it's before OR ON front expiry
        if earnings_date:
            if earnings_date <= front_dt:
                return True  # EXCLUDE - earnings before or on front expiry day
        
        return False  # Safe to trade (no earnings before or on front expiry)
    
    def filter_opportunities(self, opportunities: List[Dict], verbose: bool = True) -> List[Dict]:
        """
        Filter out opportunities with earnings BEFORE the front month expiry.
        
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
            expiry1 = opp['expiry1']  # Front month expiry
            
            has_earnings = self.has_earnings_before_expiry(ticker, expiry1)
            
            if has_earnings:
                excluded.append(ticker)
                if verbose:
                    earnings_date = self.cache.get(ticker)
                    date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "Unknown"
                    front_str = datetime.strptime(expiry1, '%Y%m%d').strftime('%Y-%m-%d')
                    print(f"  ⚠️  EXCLUDED {ticker}: Earnings on {date_str} (before front expiry {front_str})")
            else:
                filtered.append(opp)
        
        if verbose and excluded:
            print(f"\n🚫 Excluded {len(excluded)} ticker(s) due to earnings before front expiry: {', '.join(set(excluded))}")
        
        return filtered


def check_earnings(ticker: str, front_expiry: str, verbose: bool = True) -> bool:
    """
    Quick check if a single ticker has earnings before front expiry.
    
    Args:
        ticker: Stock symbol
        front_expiry: Front month expiry (YYYYMMDD)
        verbose: Print result
    
    Returns:
        True if earnings before front expiry (EXCLUDE), False if safe
    """
    checker = EarningsChecker()
    has_earnings = checker.has_earnings_before_expiry(ticker, front_expiry)
    
    if verbose:
        if has_earnings:
            earnings_date = checker.cache.get(ticker)
            date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "Unknown"
            print(f"⚠️  {ticker}: Earnings on {date_str} - EXCLUDE")
        else:
            print(f"✓ {ticker}: Safe - no earnings before front expiry")
    
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
