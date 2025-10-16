"""
Earnings Calendar Checker
Filters out tickers with earnings reports in the trading window
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from ib_insync import IB, Stock
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False


class EarningsChecker:
    """Check if earnings falls within a trading window."""
    
    def __init__(self, use_ib=False, ib_connection=None):
        """
        Initialize earnings checker.
        
        Args:
            use_ib: Use Interactive Brokers for fundamental data
            ib_connection: Existing IB connection (optional)
        """
        self.use_ib = use_ib and IB_AVAILABLE
        self.ib = ib_connection
        self.cache = {}  # Cache earnings dates to avoid repeat API calls
    
    def get_earnings_date_yfinance(self, ticker: str) -> Optional[datetime]:
        """Get next earnings date using yfinance."""
        if not YFINANCE_AVAILABLE:
            return None
        
        # Check cache first
        if ticker in self.cache:
            return self.cache[ticker]
        
        try:
            stock = yf.Ticker(ticker)
            time.sleep(0.3)  # Rate limit
            
            # Try calendar attribute
            if hasattr(stock, 'calendar') and stock.calendar is not None:
                if 'Earnings Date' in stock.calendar:
                    earnings_dates = stock.calendar['Earnings Date']
                    if earnings_dates is not None and len(earnings_dates) > 0:
                        # Get the first (next) earnings date
                        next_earnings = earnings_dates[0]
                        if isinstance(next_earnings, str):
                            next_earnings = datetime.strptime(next_earnings, '%Y-%m-%d')
                        self.cache[ticker] = next_earnings
                        return next_earnings
            
            # Try info dictionary
            info = stock.info
            if 'earningsDate' in info and info['earningsDate']:
                next_earnings = datetime.fromtimestamp(info['earningsDate'])
                self.cache[ticker] = next_earnings
                return next_earnings
            
            # Try earnings_dates attribute
            if hasattr(stock, 'earnings_dates'):
                earnings_df = stock.earnings_dates
                if earnings_df is not None and not earnings_df.empty:
                    # Get most recent future earnings
                    future_earnings = earnings_df[earnings_df.index > datetime.now()]
                    if not future_earnings.empty:
                        next_earnings = future_earnings.index[0]
                        self.cache[ticker] = next_earnings
                        return next_earnings
        
        except Exception as e:
            # Silently fail - many tickers won't have earnings data
            pass
        
        self.cache[ticker] = None
        return None
    
    def get_earnings_date_ib(self, ticker: str) -> Optional[datetime]:
        """Get next earnings date using IB fundamental data."""
        if not self.use_ib or self.ib is None:
            return None
        
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # Request fundamental data
            fundamentals = self.ib.reqFundamentalData(stock, 'ReportsFinSummary')
            
            if fundamentals:
                # Parse XML for earnings date
                # IB returns XML with financial data including earnings dates
                import xml.etree.ElementTree as ET
                root = ET.fromstring(fundamentals)
                
                # Look for earnings date in various fields
                for element in root.iter():
                    if 'earnings' in element.tag.lower() or 'report' in element.tag.lower():
                        date_str = element.text
                        if date_str:
                            try:
                                earnings_date = datetime.strptime(date_str, '%Y%m%d')
                                if earnings_date > datetime.now():
                                    self.cache[ticker] = earnings_date
                                    return earnings_date
                            except:
                                continue
        
        except Exception as e:
            # IB fundamental data requires subscription
            pass
        
        return None
    
    def has_earnings_in_window(self, ticker: str, start_date: str, end_date: str, 
                                buffer_days: int = 2) -> bool:
        """
        Check if earnings falls within trading window.
        
        Args:
            ticker: Stock symbol
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            buffer_days: Days before/after earnings to avoid (default 2)
        
        Returns:
            True if earnings is in window (should EXCLUDE), False otherwise
        """
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        # Add buffer
        start_dt = start_dt - timedelta(days=buffer_days)
        end_dt = end_dt + timedelta(days=buffer_days)
        
        # Get earnings date
        earnings_date = None
        
        # Try yfinance first (most reliable free source)
        if YFINANCE_AVAILABLE:
            earnings_date = self.get_earnings_date_yfinance(ticker)
        
        # Try IB if yfinance fails and IB is available
        if earnings_date is None and self.use_ib:
            earnings_date = self.get_earnings_date_ib(ticker)
        
        # If we have an earnings date, check if it's in window
        if earnings_date:
            if start_dt <= earnings_date <= end_dt:
                return True  # EXCLUDE - earnings in window
        
        return False  # Safe to trade
    
    def filter_opportunities(self, opportunities: List[Dict], 
                            buffer_days: int = 2, 
                            verbose: bool = True) -> List[Dict]:
        """
        Filter out opportunities with earnings in trading window.
        
        Args:
            opportunities: List of opportunity dicts with ticker, expiry1, expiry2
            buffer_days: Days before/after earnings to avoid
            verbose: Print filtered tickers
        
        Returns:
            Filtered list of opportunities
        """
        filtered = []
        excluded = []
        
        for opp in opportunities:
            ticker = opp['ticker']
            expiry1 = opp['expiry1']
            expiry2 = opp['expiry2']
            
            has_earnings = self.has_earnings_in_window(ticker, expiry1, expiry2, buffer_days)
            
            if has_earnings:
                excluded.append(ticker)
                if verbose:
                    earnings_date = self.cache.get(ticker)
                    date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "Unknown"
                    print(f"  ⚠️  EXCLUDED {ticker}: Earnings on {date_str} (in trading window)")
            else:
                filtered.append(opp)
        
        if verbose and excluded:
            print(f"\n🚫 Excluded {len(excluded)} ticker(s) due to earnings: {', '.join(set(excluded))}")
        
        return filtered


def check_earnings(ticker: str, expiry1: str, expiry2: str, verbose: bool = True) -> bool:
    """
    Quick check if a single ticker has earnings in window.
    
    Args:
        ticker: Stock symbol
        expiry1: Front month expiry (YYYYMMDD)
        expiry2: Back month expiry (YYYYMMDD)
        verbose: Print result
    
    Returns:
        True if earnings in window (EXCLUDE), False if safe
    """
    checker = EarningsChecker()
    has_earnings = checker.has_earnings_in_window(ticker, expiry1, expiry2)
    
    if verbose:
        if has_earnings:
            earnings_date = checker.cache.get(ticker)
            date_str = earnings_date.strftime('%Y-%m-%d') if earnings_date else "Unknown"
            print(f"⚠️  {ticker}: Earnings on {date_str} - EXCLUDE")
        else:
            print(f"✅ {ticker}: No earnings in window - SAFE")
    
    return has_earnings


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("EARNINGS CHECKER TEST")
    print("=" * 80)
    print()
    
    # Test single ticker
    print("Testing TSLA for Oct 24 / Oct 31 window:")
    check_earnings('TSLA', '20251024', '20251031', verbose=True)
    
    print("\nTesting AAPL for Nov 15 / Dec 20 window:")
    check_earnings('AAPL', '20251115', '20251220', verbose=True)
    
    print("\nTesting NVDA for Nov 1 / Nov 15 window:")
    check_earnings('NVDA', '20251101', '20251115', verbose=True)
    
    # Test batch filtering
    print("\n" + "=" * 80)
    print("BATCH FILTERING TEST")
    print("=" * 80)
    
    sample_opportunities = [
        {'ticker': 'TSLA', 'expiry1': '20251024', 'expiry2': '20251031'},
        {'ticker': 'AAPL', 'expiry1': '20251115', 'expiry2': '20251220'},
        {'ticker': 'MSFT', 'expiry1': '20251101', 'expiry2': '20251115'},
    ]
    
    checker = EarningsChecker()
    filtered = checker.filter_opportunities(sample_opportunities, verbose=True)
    
    print(f"\nOriginal: {len(sample_opportunities)} opportunities")
    print(f"Filtered: {len(filtered)} opportunities (safe to trade)")
