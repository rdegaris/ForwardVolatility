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
from pathlib import Path
from typing import Any

# NOTE: We intentionally DO NOT freeze FINNHUB_API_KEY at import time.
# Some entrypoints load env vars (e.g. from .env/.secrets.env) after imports.
# Always read from os.environ when needed.


def _finnhub_key() -> Optional[str]:
    key = (os.environ.get('FINNHUB_API_KEY') or '').strip()
    return key or None

# Cache controls
EARNINGS_CACHE_TTL_SECONDS = int(os.environ.get('EARNINGS_CACHE_TTL_SECONDS', '86400'))  # 1 day
CONFIRM_WITH_YFINANCE = (os.environ.get('EARNINGS_CONFIRM_YFINANCE', '1').strip() != '0')


def _default_cache_path() -> str:
    # Shared across scripts/repos; safe for Task Scheduler.
    base = Path(os.environ.get('FORWARD_VOL_CACHE_DIR') or (Path.home() / '.forward-volatility'))
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return str(base / 'earnings_cache.json')


class EarningsChecker:
    """Check for upcoming earnings dates using Finnhub API with Yahoo Finance fallback."""
    
    def __init__(self, cache_file: Optional[str] = None, use_yahoo_fallback: bool = True):
        self.cache: Dict[str, Optional[datetime]] = {}
        self._checked_at: Dict[str, float] = {}
        self._api_key_present: Dict[str, bool] = {}
        self._source: Dict[str, str] = {}
        self.cache_file = (cache_file or os.environ.get('EARNINGS_CACHE_FILE') or _default_cache_path())
        self.api_key = _finnhub_key()
        self.use_yahoo_fallback = use_yahoo_fallback
        self._load_cache()
    
    def _load_cache(self):
        """Load cached earnings dates from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Back-compat: {"AAPL": "2025-01-01"}
                if isinstance(data, dict) and all(isinstance(v, (str, type(None))) for v in data.values()):
                    for ticker, date_str in data.items():
                        if date_str:
                            self.cache[ticker] = datetime.strptime(date_str, '%Y-%m-%d')
                            self._checked_at[ticker] = 0.0
                        else:
                            self.cache[ticker] = None
                            self._checked_at[ticker] = 0.0
                    return

                # Current format: {"tickers": {"AAPL": {"date": "YYYY-MM-DD"|null, "checked_at": <epoch>}}, "meta": {...}}
                tickers_obj = data.get('tickers') if isinstance(data, dict) else None
                if isinstance(tickers_obj, dict):
                    for ticker, entry in tickers_obj.items():
                        if not isinstance(entry, dict):
                            continue
                        date_str = entry.get('date')
                        checked_at = entry.get('checked_at')
                        api_key_present = entry.get('api_key_present')
                        source = entry.get('source')
                        if isinstance(checked_at, (int, float)):
                            self._checked_at[ticker] = float(checked_at)
                        else:
                            self._checked_at[ticker] = 0.0
                        if isinstance(api_key_present, bool):
                            self._api_key_present[ticker] = api_key_present
                        if isinstance(source, str):
                            self._source[ticker] = source
                        if date_str:
                            try:
                                self.cache[ticker] = datetime.strptime(date_str, '%Y-%m-%d')
                            except Exception:
                                self.cache[ticker] = None
                        else:
                            self.cache[ticker] = None
            except Exception as e:
                print(f"Warning: Could not load earnings cache: {e}")
    
    def _save_cache(self):
        """Save cached earnings dates to file."""
        try:
            tickers_obj: Dict[str, Dict[str, object]] = {}
            for ticker, dt in self.cache.items():
                tickers_obj[ticker] = {
                    'date': dt.strftime('%Y-%m-%d') if dt else None,
                    'checked_at': float(self._checked_at.get(ticker, 0.0)),
                    'api_key_present': bool(self._api_key_present.get(ticker, False)),
                    'source': self._source.get(ticker, 'unknown'),
                }
            payload = {
                'meta': {'version': 2},
                'tickers': tickers_obj,
            }
            # Ensure parent exists
            try:
                Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save earnings cache: {e}")

    def _cache_fresh(self, ticker: str) -> bool:
        checked_at = float(self._checked_at.get(ticker, 0.0) or 0.0)
        if checked_at <= 0:
            return False
        return (time.time() - checked_at) <= EARNINGS_CACHE_TTL_SECONDS
    
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
        # Refresh API key each call (env may be loaded after import).
        self.api_key = _finnhub_key()
        api_key_present_now = bool(self.api_key)

        # Check cache first.
        # Important nuance: if we previously cached None *without* a Finnhub key,
        # and a key is available now, we should re-check Finnhub.
        if ticker in self.cache and self._cache_fresh(ticker):
            cached_date = self.cache.get(ticker)
            if cached_date is None:
                cached_had_key = bool(self._api_key_present.get(ticker, False))
                if api_key_present_now and not cached_had_key:
                    pass  # ignore stale negative cache from a no-key run
                else:
                    return None
            else:
                # If cached date is in the future or today, use it
                if cached_date >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                    return cached_date
        
        # Try Finnhub first
        source = 'none'
        earnings_date = self._get_earnings_from_finnhub(ticker, days_ahead)
        if earnings_date is not None:
            source = 'finnhub'

        # Confirm with Yahoo Finance if available (sanity check)
        if earnings_date is not None and self.use_yahoo_fallback and CONFIRM_WITH_YFINANCE:
            yahoo_date = self._get_earnings_from_yahoo(ticker)
            if yahoo_date is not None:
                try:
                    diff_days = abs((earnings_date - yahoo_date).days)
                    if diff_days >= 4:
                        print(
                            f"    Warning: Finnhub vs Yahoo mismatch for {ticker}: "
                            f"Finnhub={earnings_date.strftime('%Y-%m-%d')} Yahoo={yahoo_date.strftime('%Y-%m-%d')}"
                        )
                except Exception:
                    pass
        
        # If Finnhub returns None, try Yahoo Finance as fallback
        if earnings_date is None and self.use_yahoo_fallback:
            earnings_date = self._get_earnings_from_yahoo(ticker)
            if earnings_date:
                source = 'yahoo'
                print(f"    [Yahoo] Found earnings for {ticker}: {earnings_date.strftime('%Y-%m-%d')}")
        
        # Cache the result
        self.cache[ticker] = earnings_date
        self._checked_at[ticker] = time.time()
        self._api_key_present[ticker] = api_key_present_now
        self._source[ticker] = source
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
        if not self.api_key:
            return None
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
                    # Finnhub does not guarantee ordering; pick the nearest future date.
                    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    dates: List[datetime] = []
                    for entry in data.get('earningsCalendar', []):
                        if not isinstance(entry, dict):
                            continue
                        date_str = entry.get('date')
                        if not date_str:
                            continue
                        try:
                            dt = datetime.strptime(date_str, '%Y-%m-%d')
                        except Exception:
                            continue
                        if dt >= today_dt:
                            dates.append(dt)

                    if dates:
                        return min(dates)
            
            return None

        except Exception as e:
            print(f"    Warning: Could not fetch earnings from Finnhub for {ticker}: {e}")
            return None

    def has_earnings_within_days(self, ticker: str, days: int) -> bool:
        """True if earnings are within the next N calendar days (including today)."""
        if days <= 0:
            return False
        earnings_date = self.get_earnings_date(ticker, days_ahead=max(days, 60))
        if not earnings_date:
            return False
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return today <= earnings_date <= (today + timedelta(days=days))
    
    def has_earnings_before(self, ticker: str, expiry_date: str) -> bool:
        """
        Check if a ticker has earnings before the given expiry date.
        
        Args:
            ticker: Stock symbol
            expiry_date: Expiry date in YYYYMMDD format
            
        Returns:
            True if earnings are before expiry, False otherwise
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expiry = datetime.strptime(expiry_date, '%Y%m%d')
        days_ahead = max(60, int((expiry - today).days) + 7)

        earnings_date = self.get_earnings_date(ticker, days_ahead=days_ahead)
        if not earnings_date:
            return False
        
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
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        back = datetime.strptime(back_expiry, '%Y%m%d')
        days_ahead = max(60, int((back - today).days) + 7)

        earnings_date = self.get_earnings_date(ticker, days_ahead=days_ahead)
        if not earnings_date:
            return False

        front = datetime.strptime(front_expiry, '%Y%m%d')
        
        # Danger zone: earnings between today and back expiry
        # This catches:
        # 1. Earnings happening today (before you can trade)
        # 2. Earnings between now and front expiry
        # 3. Earnings between front and back expiry
        return today <= earnings_date <= back
    
    def get_days_to_earnings(self, ticker: str) -> Optional[int]:
        """Get number of days until earnings."""
        earnings_date = self.get_earnings_date(ticker, days_ahead=180)
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
