"""
Forward Volatility Scanner using Interactive Brokers API
Requires: ib_insync library and IB Gateway/TWS running
"""

import math
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import os

from excluded_tickers import ExcludedTickers

try:
    from ib_insync import IB, Stock, Option
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("ERROR: ib_insync not installed")
    print("Install with: pip install ib_insync")

try:
    from earnings_checker import EarningsChecker
    EARNINGS_CHECKER_AVAILABLE = True
except ImportError:
    EARNINGS_CHECKER_AVAILABLE = False


def calculate_forward_vol(dte1: float, iv1: float, dte2: float, iv2: float) -> Optional[Dict]:
    """Calculate forward volatility and forward factor.
    
    Returns:
        Dict with forward variance, forward vol, and forward factor metrics
    """
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
    
    # Forward variance (annualized)
    fwd_var = (tv2 - tv1) / denom
    
    if fwd_var < 0:
        return None
    
    # Forward volatility (annualized)
    fwd_sigma = math.sqrt(fwd_var)
    
    if fwd_sigma == 0.0:
        ff_ratio = None
    else:
        ff_ratio = (s1 - fwd_sigma) / fwd_sigma
    
    return {
        'fwd_var': fwd_var,  # Annualized forward variance
        'fwd_var_pct': fwd_var * 100,  # As percentage
        'fwd_sigma': fwd_sigma,  # Annualized forward volatility
        'fwd_sigma_pct': fwd_sigma * 100,  # As percentage
        'ff_ratio': ff_ratio,
        'ff_pct': ff_ratio * 100 if ff_ratio is not None else None
    }


def calculate_dte(expiry_str: str) -> int:
    """Calculate days to expiration."""
    try:
        expiry = datetime.strptime(expiry_str, '%Y%m%d')
        today = datetime.now()
        dte = (expiry - today).days
        return max(0, dte)
    except:
        return 0


def print_bordered_table(df):
    """Print a DataFrame with ASCII borders."""
    col_widths = {}
    for col in df.columns:
        col_widths[col] = max(len(str(col)), df[col].astype(str).str.len().max())
    
    sep_line = '+'
    for col in df.columns:
        sep_line += '-' * (col_widths[col] + 2) + '+'
    
    print(sep_line)
    
    header = '|'
    for col in df.columns:
        header += f' {str(col).ljust(col_widths[col])} |'
    print(header)
    print(sep_line)
    
    for _, row in df.iterrows():
        row_str = '|'
        for col in df.columns:
            value = str(row[col])
            row_str += f' {value.ljust(col_widths[col])} |'
        print(row_str)
    
    print(sep_line)


class IBScanner:
    """Interactive Brokers Forward Volatility Scanner."""
    
    def __init__(self, host=None, port=None, client_id=None, check_earnings=True):
        """
        Initialize IB connection.
        
        Args:
            host: IB Gateway/TWS host (default: localhost)
            port: 7498 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
            client_id: Unique client ID
            check_earnings: Filter out tickers with earnings in trading window (default: True)
        """
        if host is None:
            host = os.environ.get('IB_HOST', '127.0.0.1')
        if port is None:
            port = int(os.environ.get('IB_PORT', '7498'))
        if client_id is None:
            # Default to a higher clientId to reduce collisions with manual TWS/Gateway sessions.
            client_id = int(os.environ.get('IB_CLIENT_ID', '110'))
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.check_earnings = check_earnings and EARNINGS_CHECKER_AVAILABLE
        self.earnings_checker = EarningsChecker() if self.check_earnings else None
        self.price_cache = {}  # Cache for stock prices
        self.ma_200_cache = {}  # Cache for 200-day MA
        self._opt_params_cache = {}  # Cache for reqSecDefOptParams results per ticker
        self._opt_chain_choice_cache = {}  # Cache chosen option chain per ticker

        # Persistent exclude list for tickers IB can't qualify (e.g., delisted / no security definition).
        exclude_enabled = os.environ.get('EXCLUDE_TICKERS_ENABLED', '1').strip().lower() not in ('0', 'false', 'no', 'n')
        exclude_path = os.environ.get(
            'EXCLUDE_TICKERS_FILE',
            os.path.join(os.path.dirname(__file__), 'excluded_tickers.json')
        )
        self.excluded_tickers = ExcludedTickers(exclude_path, enabled=exclude_enabled)
        self._last_ib_error_by_symbol = {}
        self._error_handler_registered = False

        # Performance toggles
        self.fetch_ma_200 = os.environ.get('FETCH_MA_200', '1').strip().lower() not in ('0', 'false', 'no', 'n')
    
    def connect(self, max_retries=3):
        """Connect to IB Gateway or TWS with retry logic."""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    print(f"  Retrying in {wait_time} seconds (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                
                print(f"Connecting to Interactive Brokers at {self.host}:{self.port}...")
                self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10)

                # Register error handler once so we can persistently exclude unqualifiable tickers.
                if not self._error_handler_registered:
                    try:
                        self.ib.errorEvent += self._on_ib_error
                        self._error_handler_registered = True
                    except Exception:
                        pass

                self.connected = True
                print("  Connected successfully!")
                return True
            except Exception as e:
                print(f"  Connection failed: {e}")
                if attempt == max_retries - 1:
                    print("\nMake sure:")
                    print("  1. IB Gateway or TWS is running")
                    print("  2. API connections are enabled in settings")
                    print("  3. Port number is correct:")
                    print("     - TWS Paper: 7497")
                    print("     - TWS Live: 7496")
            print("     - Gateway Paper: 4002")
            print("     - Gateway Live: 4001")
            return False

    @staticmethod
    def _looks_like_not_found_error(message: str) -> bool:
        if not message:
            return False
        msg = message.lower()
        needles = (
            'no security definition has been found',
            'unknown contract',
            'unknown security',
            'no such contract',
            'no contract found',
            'security definition',
        )
        return any(n in msg for n in needles)

    def _on_ib_error(self, *args):
        """IB error event handler.

        Signature (ib_insync): (reqId, errorCode, errorString, contract)
        but we accept *args to be resilient across versions.
        """
        try:
            req_id = args[0] if len(args) > 0 else None
            error_code = args[1] if len(args) > 1 else None
            error_string = args[2] if len(args) > 2 else ''
            contract = args[3] if len(args) > 3 else None
        except Exception:
            return

        symbol = None
        try:
            symbol = getattr(contract, 'symbol', None) if contract is not None else None
        except Exception:
            symbol = None

        if symbol:
            self._last_ib_error_by_symbol[symbol.upper()] = {
                'ts': time.time(),
                'code': error_code,
                'msg': str(error_string),
                'req_id': req_id,
            }

        # Error 200 is the canonical "no security definition" / unknown contract.
        if symbol and int(error_code or 0) == 200:
            self.excluded_tickers.add(symbol, reason=str(error_string), source='ib_errorEvent:200')

    def _should_exclude_on_exception(self, ticker: str, exc: Exception) -> bool:
        msg = str(exc)
        if self._looks_like_not_found_error(msg):
            return True

        # Sometimes the error comes through errorEvent and qualifyContracts doesn't raise.
        last = self._last_ib_error_by_symbol.get(ticker.upper())
        if last and int(last.get('code') or 0) == 200 and (time.time() - float(last.get('ts') or 0)) < 30:
            return True
        return False
    
    def disconnect(self):
        """Disconnect from IB."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
    
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """Get current stock price."""
        if self.excluded_tickers.is_excluded(ticker):
            return None

        # Check cache first
        if ticker in self.price_cache:
            return self.price_cache[ticker]
        
        stock = None
        ticker_data = None
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            try:
                self.ib.qualifyContracts(stock)
            except Exception as e:
                if self._should_exclude_on_exception(ticker, e):
                    self.excluded_tickers.add(ticker, reason=str(e), source='qualifyContracts:stock')
                raise

            # qualifyContracts may not raise even when IB returns error 200.
            if not getattr(stock, 'conId', 0):
                last = self._last_ib_error_by_symbol.get(ticker.upper())
                if last and int(last.get('code') or 0) == 200:
                    self.excluded_tickers.add(ticker, reason=str(last.get('msg') or 'Error 200'), source='qualifyContracts:stock')
                return None

            # Fast path: snapshot tick (avoids a fixed multi-second sleep)
            try:
                snap = self.ib.reqTickers(stock)
                if snap and len(snap) > 0:
                    t = snap[0]
                    price = t.marketPrice()
                    if price and price > 0:
                        self.price_cache[ticker] = price
                        return price
                    if getattr(t, 'last', None) and t.last > 0:
                        self.price_cache[ticker] = t.last
                        return t.last
            except Exception:
                pass
            
            ticker_data = self.ib.reqMktData(stock, '', False, False)

            # Fallback: short wait for streaming data
            try:
                wait_s = float(os.environ.get('IB_STOCK_PRICE_SLEEP_SECONDS', '0.6'))
            except Exception:
                wait_s = 0.6
            self.ib.sleep(wait_s)
            
            price = ticker_data.marketPrice()
            if price and price > 0:
                self.price_cache[ticker] = price
                return price
            
            # Try last price if market price not available
            if ticker_data.last and ticker_data.last > 0:
                self.price_cache[ticker] = ticker_data.last
                return ticker_data.last
            
            return None
        except Exception as e:
            print(f"  Error getting price: {e}")
            return None
        finally:
            # ALWAYS cancel market data subscription to free up data lines
            if stock:
                try:
                    self.ib.cancelMktData(stock)
                except:
                    pass
    
    def get_200day_ma(self, ticker: str) -> Optional[float]:
        """Get 200-day moving average for a stock.
        
        Returns:
            200-day MA price, or None if not available
        """
        # Check cache first
        if ticker in self.ma_200_cache:
            return self.ma_200_cache[ticker]
        
        try:
            if self.excluded_tickers.is_excluded(ticker):
                return None
            stock = Stock(ticker, 'SMART', 'USD')
            try:
                self.ib.qualifyContracts(stock)
            except Exception as e:
                if self._should_exclude_on_exception(ticker, e):
                    self.excluded_tickers.add(ticker, reason=str(e), source='qualifyContracts:ma200')
                raise

            if not getattr(stock, 'conId', 0):
                last = self._last_ib_error_by_symbol.get(ticker.upper())
                if last and int(last.get('code') or 0) == 200:
                    self.excluded_tickers.add(ticker, reason=str(last.get('msg') or 'Error 200'), source='qualifyContracts:ma200')
                return None
            
            # Request 200 days of daily bars
            bars = self.ib.reqHistoricalData(
                stock,
                endDateTime='',
                durationStr='200 D',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if bars and len(bars) >= 200:
                # Calculate average of close prices
                closes = [bar.close for bar in bars[-200:]]
                ma_200 = sum(closes) / len(closes)
                self.ma_200_cache[ticker] = ma_200
                return ma_200
            
            return None
            
        except Exception as e:
            return None
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """Get stock price and 200-day MA.
        
        Returns:
            Dict with 'price', 'ma_200', 'above_ma_200'
        """
        try:
            print(f"    Getting price for {ticker}...", flush=True)
            price = self.get_stock_price(ticker)
            if not price:
                print(f"    No price available for {ticker}", flush=True)
                return None
            print(f"    Price: ${price:.2f}", flush=True)

            ma_200 = None
            if self.fetch_ma_200:
                print(f"    Getting 200-day MA...", flush=True)
                ma_200 = self.get_200day_ma(ticker)
            
            above_ma_200 = None
            if ma_200:
                above_ma_200 = price > ma_200
            
            return {
                'price': price,
                'ma_200': ma_200,
                'above_ma_200': above_ma_200
            }
            
        except Exception as e:
            return None
    
    def get_option_chains(self, ticker: str) -> List[str]:
        """Get available option expiration dates."""
        try:
            print(f"    Getting option chains for {ticker}...", flush=True)
            chain = self._select_option_chain(ticker)
            
            if not chain:
                return []
            
            expirations = sorted(chain.expirations)
            return expirations
        except Exception as e:
            print(f"  Error getting option chains: {e}")
            return []

    def get_secdef_opt_params(self, ticker: str):
        """Get (and cache) option security definition params for a ticker."""
        cached = self._opt_params_cache.get(ticker)
        if cached is not None:
            return cached

        try:
            if self.excluded_tickers.is_excluded(ticker):
                self._opt_params_cache[ticker] = []
                return []

            stock = Stock(ticker, 'SMART', 'USD')
            try:
                self.ib.qualifyContracts(stock)
            except Exception as e:
                if self._should_exclude_on_exception(ticker, e):
                    self.excluded_tickers.add(ticker, reason=str(e), source='qualifyContracts:optParams')
                raise

            if not getattr(stock, 'conId', 0):
                last = self._last_ib_error_by_symbol.get(ticker.upper())
                if last and int(last.get('code') or 0) == 200:
                    self.excluded_tickers.add(ticker, reason=str(last.get('msg') or 'Error 200'), source='qualifyContracts:optParams')
                self._opt_params_cache[ticker] = []
                return []

            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            self._opt_params_cache[ticker] = chains
            return chains
        except Exception:
            self._opt_params_cache[ticker] = []
            return []

    def _select_option_chain(self, ticker: str):
        """Choose the best SecDefOptParam chain for a ticker.

        Some symbols have multiple chains (e.g., a "2{SYMBOL}" tradingClass). Picking the
        wrong chain can lead to ambiguous contracts or missing security definitions.
        """
        cached = self._opt_chain_choice_cache.get(ticker)
        if cached is not None:
            return cached

        chains = self.get_secdef_opt_params(ticker)
        if not chains:
            self._opt_chain_choice_cache[ticker] = None
            return None

        def score(chain) -> tuple:
            exch = (getattr(chain, 'exchange', '') or '').upper()
            trading_class = (getattr(chain, 'tradingClass', '') or '').upper()
            return (
                1 if exch == 'SMART' else 0,
                1 if trading_class == ticker.upper() else 0,
                0 if trading_class.startswith('2') else 1,
            )

        chosen = max(chains, key=score)
        self._opt_chain_choice_cache[ticker] = chosen
        return chosen

    def _make_option(self, ticker: str, expiry: str, strike: float, right: str, chain) -> 'Option':
        """Construct an Option contract with enough fields to avoid ambiguity in IB."""
        trading_class = getattr(chain, 'tradingClass', '') if chain is not None else ''
        multiplier = getattr(chain, 'multiplier', '100') if chain is not None else '100'

        return Option(
            ticker,
            expiry,
            float(strike),
            right,
            'SMART',
            multiplier=str(multiplier) if multiplier else '100',
            currency='USD',
            tradingClass=str(trading_class) if trading_class else '',
        )

    @staticmethod
    def _candidate_strikes(strikes, current_price: float, max_candidates: int = 12) -> List[float]:
        """Return a small list of strikes closest to price (for qualify fallbacks)."""
        if not strikes:
            return []
        uniq = []
        seen = set()
        for s in strikes:
            if s is None:
                continue
            try:
                fs = float(s)
            except Exception:
                continue
            if fs not in seen:
                seen.add(fs)
                uniq.append(fs)
        uniq.sort(key=lambda x: abs(x - current_price))
        return uniq[:max_candidates]
    
    def get_near_term_iv(self, ticker: str, current_price: float) -> Optional[float]:
        """Get near-term IV for quick ranking. Accepts 7-90 day expirations.
        
        Returns:
            Average IV as a percentage, or None if not available
        """
        try:
            expirations = self.get_option_chains(ticker)
            if not expirations:
                return None
            
            # Find the nearest expiration in the 7-90 day range
            # Prefer shorter DTEs but accept monthly expirations (30/60/90)
            best_expiry = None
            best_dte = None
            
            for exp in expirations:
                dte = calculate_dte(exp)
                if 7 <= dte <= 90:  # Accept 1 week to 3 months
                    if best_expiry is None or dte < best_dte:
                        best_expiry = exp
                        best_dte = dte
            
            if not best_expiry:
                return None
            
            # Get IV for this expiry
            iv_data = self.get_atm_iv(ticker, best_expiry, current_price, debug=False)
            if iv_data and iv_data['avg_iv']:
                return iv_data['avg_iv']
            
            return None
            
        except Exception as e:
            return None
    
    def get_atm_iv(self, ticker: str, expiry: str, current_price: float, debug: bool = False) -> Optional[Dict]:
        """Get ATM implied volatility for specific expiry.
        
        Returns:
            Dict with 'call_iv', 'put_iv', 'avg_iv' or None
        """
        call = None
        put = None
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            chain = self._select_option_chain(ticker)
            if not chain:
                if debug:
                    print(f"\n    [DEBUG] No chains found")
                return None

            candidates = self._candidate_strikes(getattr(chain, 'strikes', []), current_price)
            if not candidates:
                return None

            atm_strike = None
            for candidate_strike in candidates:
                try:
                    call = self._make_option(ticker, expiry, candidate_strike, 'C', chain)
                    put = self._make_option(ticker, expiry, candidate_strike, 'P', chain)
                    self.ib.qualifyContracts(call, put)

                    # qualifyContracts may not raise even when IB returns error 200.
                    # Treat it as a failure unless conId is populated.
                    if not getattr(call, 'conId', 0) or not getattr(put, 'conId', 0):
                        call = None
                        put = None
                        continue

                    atm_strike = float(candidate_strike)
                    break
                except Exception:
                    call = None
                    put = None
                    continue

            if atm_strike is None:
                return None
            
            if debug:
                print(f"\n    [DEBUG] ATM Strike: {atm_strike} (Price: {current_price})")
            
            if debug:
                print(f"    [DEBUG] Call: {call.localSymbol if hasattr(call, 'localSymbol') else 'qualified'}")
                print(f"    [DEBUG] Put: {put.localSymbol if hasattr(put, 'localSymbol') else 'qualified'}")
            
            # Request market data with generic tick for IV
            if debug:
                print(f"    [DEBUG] Requesting market data...")
            print(f"    Requesting market data for {ticker} {expiry} strike {atm_strike}...", flush=True)
            call_ticker = self.ib.reqMktData(call, '106', False, False)  # 106 = option IV
            put_ticker = self.ib.reqMktData(put, '106', False, False)
            
            if debug:
                print(f"    [DEBUG] Waiting for IV data (2 sec)...")
            print(f"    Waiting for IV data...", flush=True)
            try:
                iv_wait_s = float(os.environ.get('IB_OPTION_IV_SLEEP_SECONDS', '2'))
            except Exception:
                iv_wait_s = 2.0
            self.ib.sleep(iv_wait_s)
            if debug:
                print(f"    [DEBUG] Data received")
            print(f"    IV data received", flush=True)
            
            # Try multiple methods to get IV
            call_iv = None
            put_iv = None
            
            # Method 1: modelGreeks (pre-calculated by IB for liquid options)
            if call_ticker.modelGreeks and call_ticker.modelGreeks.impliedVol:
                call_iv = call_ticker.modelGreeks.impliedVol * 100  # Convert to percentage
                if debug:
                    print(f"    [DEBUG] Call IV (modelGreeks): {call_iv:.2f}%")
            
            if put_ticker.modelGreeks and put_ticker.modelGreeks.impliedVol:
                put_iv = put_ticker.modelGreeks.impliedVol * 100  # Convert to percentage
                if debug:
                    print(f"    [DEBUG] Put IV (modelGreeks): {put_iv:.2f}%")
            
            # Method 2: Calculate IV from option price if modelGreeks not available
            # This is critical for less liquid MidCap stocks where IB doesn't provide modelGreeks
            if not call_iv and call_ticker.last and call_ticker.last > 0:
                if debug:
                    print(f"    [DEBUG] Call has price ${call_ticker.last} but no modelGreeks, requesting IV calculation...")
                try:
                    # Request IB to calculate IV from the market price
                    calc_iv = self.ib.calculateImpliedVolatility(call, call_ticker.last, current_price)
                    self.ib.sleep(1)  # Wait for calculation
                    if calc_iv and hasattr(calc_iv, 'impliedVolatility') and calc_iv.impliedVolatility:
                        call_iv = calc_iv.impliedVolatility * 100
                        if debug:
                            print(f"    [DEBUG] Call IV (calculated): {call_iv:.2f}%")
                except Exception as e:
                    if debug:
                        print(f"    [DEBUG] Failed to calculate call IV: {e}")
            
            if not put_iv and put_ticker.last and put_ticker.last > 0:
                if debug:
                    print(f"    [DEBUG] Put has price ${put_ticker.last} but no modelGreeks, requesting IV calculation...")
                try:
                    # Request IB to calculate IV from the market price
                    calc_iv = self.ib.calculateImpliedVolatility(put, put_ticker.last, current_price)
                    self.ib.sleep(1)  # Wait for calculation
                    if calc_iv and hasattr(calc_iv, 'impliedVolatility') and calc_iv.impliedVolatility:
                        put_iv = calc_iv.impliedVolatility * 100
                        if debug:
                            print(f"    [DEBUG] Put IV (calculated): {put_iv:.2f}%")
                except Exception as e:
                    if debug:
                        print(f"    [DEBUG] Failed to calculate put IV: {e}")
            
            # Get bid/ask prices for midpoint calculation
            call_bid = call_ticker.bid if call_ticker.bid and call_ticker.bid > 0 else None
            call_ask = call_ticker.ask if call_ticker.ask and call_ticker.ask > 0 else None
            call_last = call_ticker.last if call_ticker.last and call_ticker.last > 0 else None
            call_mid = (call_bid + call_ask) / 2 if call_bid and call_ask else call_last
            
            put_bid = put_ticker.bid if put_ticker.bid and put_ticker.bid > 0 else None
            put_ask = put_ticker.ask if put_ticker.ask and put_ticker.ask > 0 else None
            put_last = put_ticker.last if put_ticker.last and put_ticker.last > 0 else None
            put_mid = (put_bid + put_ask) / 2 if put_bid and put_ask else put_last
            
            # Calculate average
            ivs = []
            if call_iv and call_iv > 0:
                ivs.append(call_iv)
            if put_iv and put_iv > 0:
                ivs.append(put_iv)
            
            if not ivs:
                if debug:
                    print(f"    [DEBUG] No valid IV found")
                return None
            
            avg_iv = sum(ivs) / len(ivs)
            if debug:
                print(f"    [DEBUG] Average IV: {avg_iv:.2f}%")
            
            return {
                'call_iv': call_iv,
                'put_iv': put_iv,
                'avg_iv': avg_iv,
                'atm_strike': atm_strike,
                'call_bid': call_bid,
                'call_ask': call_ask,
                'call_mid': call_mid,
                'put_bid': put_bid,
                'put_ask': put_ask,
                'put_mid': put_mid
            }
            
        except Exception as e:
            if debug:
                print(f"\n    [DEBUG] Exception: {e}")
            return None
        finally:
            # ALWAYS cancel market data subscriptions to free up data lines
            if call:
                try:
                    self.ib.cancelMktData(call)
                except:
                    pass
            if put:
                try:
                    self.ib.cancelMktData(put)
                except:
                    pass
    
    def get_atm_iv_batch(self, ticker: str, expiry1: str, expiry2: str, current_price: float, debug: bool = False) -> tuple:
        """Get ATM implied volatility for two expirations in a single batch request.
        
        This is faster than calling get_atm_iv twice because it requests all 4 options
        (call1, put1, call2, put2) at once and waits only once for all data.
        
        Returns:
            Tuple of (iv_data1, iv_data2) or (None, None) on error
        """
        call1 = None
        put1 = None
        call2 = None
        put2 = None
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            chain = self._select_option_chain(ticker)
            if not chain:
                return None, None

            candidates = self._candidate_strikes(getattr(chain, 'strikes', []), current_price)
            if not candidates:
                return None, None

            atm_strike = None
            call1 = None
            put1 = None
            call2 = None
            put2 = None
            for candidate_strike in candidates:
                try:
                    call1 = self._make_option(ticker, expiry1, candidate_strike, 'C', chain)
                    put1 = self._make_option(ticker, expiry1, candidate_strike, 'P', chain)
                    call2 = self._make_option(ticker, expiry2, candidate_strike, 'C', chain)
                    put2 = self._make_option(ticker, expiry2, candidate_strike, 'P', chain)
                    self.ib.qualifyContracts(call1, put1, call2, put2)

                    # qualifyContracts may not raise even when IB returns error 200.
                    if not all(getattr(c, 'conId', 0) for c in (call1, put1, call2, put2)):
                        call1 = None
                        put1 = None
                        call2 = None
                        put2 = None
                        continue

                    atm_strike = float(candidate_strike)
                    break
                except Exception:
                    call1 = None
                    put1 = None
                    call2 = None
                    put2 = None
                    continue

            if atm_strike is None:
                return None, None
            
            if debug:
                print(f"\n    [DEBUG] Batch request: ATM Strike {atm_strike} for {expiry1} and {expiry2}")
            
            # Request all market data at once
            print(f"    Requesting batch IV data for {expiry1} and {expiry2}...", flush=True)
            call1_ticker = self.ib.reqMktData(call1, '106', False, False)
            put1_ticker = self.ib.reqMktData(put1, '106', False, False)
            call2_ticker = self.ib.reqMktData(call2, '106', False, False)
            put2_ticker = self.ib.reqMktData(put2, '106', False, False)
            
            # Wait once for all data
            print(f"    Waiting for batch IV data...", flush=True)
            try:
                iv_wait_s = float(os.environ.get('IB_OPTION_IV_SLEEP_SECONDS', '2'))
            except Exception:
                iv_wait_s = 2.0
            self.ib.sleep(iv_wait_s)
            print(f"    Batch IV data received", flush=True)
            
            # Extract IV from all tickers
            def extract_iv(ticker_data, contract, label):
                iv = None
                if ticker_data.modelGreeks and ticker_data.modelGreeks.impliedVol:
                    iv = ticker_data.modelGreeks.impliedVol * 100
                    if debug:
                        print(f"    [DEBUG] {label} IV (modelGreeks): {iv:.2f}%")
                elif ticker_data.last and ticker_data.last > 0:
                    try:
                        calc_iv = self.ib.calculateImpliedVolatility(contract, ticker_data.last, current_price)
                        try:
                            calc_wait_s = float(os.environ.get('IB_CALC_IV_SLEEP_SECONDS', '0.5'))
                        except Exception:
                            calc_wait_s = 0.5
                        self.ib.sleep(calc_wait_s)
                        if calc_iv and hasattr(calc_iv, 'impliedVolatility') and calc_iv.impliedVolatility:
                            iv = calc_iv.impliedVolatility * 100
                            if debug:
                                print(f"    [DEBUG] {label} IV (calculated): {iv:.2f}%")
                    except:
                        pass
                return iv, ticker_data
            
            call1_iv, _ = extract_iv(call1_ticker, call1, f"{expiry1} Call")
            put1_iv, _ = extract_iv(put1_ticker, put1, f"{expiry1} Put")
            call2_iv, _ = extract_iv(call2_ticker, call2, f"{expiry2} Call")
            put2_iv, _ = extract_iv(put2_ticker, put2, f"{expiry2} Put")
            
            # Build iv_data dicts
            def build_iv_data(call_iv, put_iv, call_ticker, put_ticker):
                ivs = [iv for iv in [call_iv, put_iv] if iv and iv > 0]
                if not ivs:
                    return None
                avg_iv = sum(ivs) / len(ivs)
                
                call_bid = call_ticker.bid if call_ticker.bid and call_ticker.bid > 0 else None
                call_ask = call_ticker.ask if call_ticker.ask and call_ticker.ask > 0 else None
                call_mid = (call_bid + call_ask) / 2 if call_bid and call_ask else (call_ticker.last if call_ticker.last else None)
                
                put_bid = put_ticker.bid if put_ticker.bid and put_ticker.bid > 0 else None
                put_ask = put_ticker.ask if put_ticker.ask and put_ticker.ask > 0 else None
                put_mid = (put_bid + put_ask) / 2 if put_bid and put_ask else (put_ticker.last if put_ticker.last else None)
                
                return {
                    'call_iv': call_iv,
                    'put_iv': put_iv,
                    'avg_iv': avg_iv,
                    'atm_strike': atm_strike,
                    'call_bid': call_bid,
                    'call_ask': call_ask,
                    'call_mid': call_mid,
                    'put_bid': put_bid,
                    'put_ask': put_ask,
                    'put_mid': put_mid
                }
            
            iv_data1 = build_iv_data(call1_iv, put1_iv, call1_ticker, put1_ticker)
            iv_data2 = build_iv_data(call2_iv, put2_iv, call2_ticker, put2_ticker)
            
            return iv_data1, iv_data2
            
        except Exception as e:
            if debug:
                print(f"\n    [DEBUG] Batch exception: {e}")
            return None, None
        finally:
            # ALWAYS cancel all subscriptions to free up data lines
            for contract in [call1, put1, call2, put2]:
                if contract:
                    try:
                        self.ib.cancelMktData(contract)
                    except:
                        pass
    
    def scan_ticker(self, ticker: str, threshold: float = 0.4) -> List[Dict]:
        """Scan a ticker for forward volatility opportunities."""
        opportunities = []
        
        print(f"\nScanning {ticker}...")
        
        # Get stock info (price and 200-day MA)
        stock_info = self.get_stock_info(ticker)
        if not stock_info:
            print(f"  Could not get price for {ticker}")
            return opportunities
        
        current_price = stock_info['price']
        ma_200 = stock_info.get('ma_200')
        above_ma_200 = stock_info.get('above_ma_200')

        # Optional: skip tickers with earnings in the next N days.
        # NOTE: Default is OFF (0). Most stocks have earnings within 90 days,
        # so a default like 90 can unintentionally zero out the entire scan.
        if self.check_earnings and self.earnings_checker:
            try:
                ignore_days = int(os.environ.get('EARNINGS_IGNORE_WITHIN_DAYS', '0'))
            except Exception:
                ignore_days = 0
            if ignore_days > 0 and self.earnings_checker.has_earnings_within_days(ticker, ignore_days):
                ed = self.earnings_checker.get_earnings_date(ticker, days_ahead=max(ignore_days, 60))
                if ed:
                    print(f"  Skipping: earnings within {ignore_days} days ({ed.strftime('%Y-%m-%d')})")
                else:
                    print(f"  Skipping: earnings within {ignore_days} days")
                return opportunities
        
        # Display price and MA info
        print(f"  Price: ${current_price:.2f}")
        if ma_200:
            trend = "ABOVE" if above_ma_200 else "BELOW"
            print(f"  200-day MA: ${ma_200:.2f} ({trend})")
        
        # Get option chains
        print(f"  -> Fetching option expirations...")
        expirations = self.get_option_chains(ticker)
        if len(expirations) < 2:
            print(f"  Not enough expiration dates")
            return opportunities
        
        print(f"  Found {len(expirations)} expiration dates: {', '.join(expirations[:5])}{'...' if len(expirations) > 5 else ''}")
        
        # Define target DTE pairs with tolerance
        # Format: (target_dte1, target_dte2, tolerance)
        target_pairs = [
            (7, 14, 5),    # ~1 week vs ~2 weeks
            (14, 21, 5),   # ~2 weeks vs ~3 weeks
            (7, 21, 5),    # ~1 week vs ~3 weeks
            (30, 60, 5),   # ~1 month vs ~2 months
            (60, 90, 5),   # ~2 months vs ~3 months
            (30, 90, 5),   # ~1 month vs ~3 months
        ]
        
        # Find expirations matching target DTEs
        checked_pairs = set()  # Track pairs to avoid duplicates
        
        for target_dte1, target_dte2, tolerance in target_pairs:
            # Find expiry closest to target_dte1
            expiry1 = None
            min_diff1 = float('inf')
            for exp in expirations:
                dte = calculate_dte(exp)
                diff = abs(dte - target_dte1)
                if diff <= tolerance and diff < min_diff1:
                    expiry1 = exp
                    min_diff1 = diff
            
            # Find expiry closest to target_dte2
            expiry2 = None
            min_diff2 = float('inf')
            for exp in expirations:
                dte = calculate_dte(exp)
                diff = abs(dte - target_dte2)
                if diff <= tolerance and diff < min_diff2 and exp != expiry1:
                    expiry2 = exp
                    min_diff2 = diff
            
            # Skip if we didn't find both or if already checked
            if not expiry1 or not expiry2:
                continue
            
            pair_key = (expiry1, expiry2)
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)
            
            dte1 = calculate_dte(expiry1)
            dte2 = calculate_dte(expiry2)
            
            if dte1 < 1 or dte2 < 1 or dte2 <= dte1:
                continue
            
            print(f"  Checking {expiry1} (DTE={dte1}) vs {expiry2} (DTE={dte2}) [Target: {target_dte1}/{target_dte2}]...", flush=True)
            
            # Use batch method to fetch both expirations at once (saves ~2s per pair)
            scan_iv_debug = os.environ.get('SCAN_IV_DEBUG', '0').strip().lower() in ('1', 'true', 'yes', 'y')
            iv_data1, iv_data2 = self.get_atm_iv_batch(ticker, expiry1, expiry2, current_price, debug=scan_iv_debug)
            
            if iv_data1 is None or iv_data2 is None:
                print("  -> No IV data\n")
                continue
            
            # Calculate FF for average (blended calls+puts)
            result_avg = calculate_forward_vol(dte1, iv_data1['avg_iv'], dte2, iv_data2['avg_iv'])
            
            # Calculate FF for calls only
            result_call = None
            if iv_data1['call_iv'] and iv_data2['call_iv']:
                result_call = calculate_forward_vol(dte1, iv_data1['call_iv'], dte2, iv_data2['call_iv'])
            
            # Calculate FF for puts only
            result_put = None
            if iv_data1['put_iv'] and iv_data2['put_iv']:
                result_put = calculate_forward_vol(dte1, iv_data1['put_iv'], dte2, iv_data2['put_iv'])
            
            if result_avg is None:
                print("Invalid")
                continue
            
            ff_ratio_avg = result_avg.get('ff_ratio')
            ff_ratio_call = result_call.get('ff_ratio') if result_call else None
            ff_ratio_put = result_put.get('ff_ratio') if result_put else None
            
            # Check if any FF meets threshold
            max_ff = ff_ratio_avg
            if ff_ratio_call and ff_ratio_call > max_ff:
                max_ff = ff_ratio_call
            if ff_ratio_put and ff_ratio_put > max_ff:
                max_ff = ff_ratio_put
            
            call_str = f"{ff_ratio_call:.3f}" if ff_ratio_call else "N/A"
            put_str = f"{ff_ratio_put:.3f}" if ff_ratio_put else "N/A"
            print(f"    -> FF: avg={ff_ratio_avg:.3f}, call={call_str}, put={put_str}, max={max_ff:.3f}")
            
            if max_ff is not None and max_ff >= threshold:
                # Get earnings date if available
                next_earnings = None
                if self.check_earnings and self.earnings_checker:
                    earnings_date = self.earnings_checker.cache.get(ticker)
                    if not earnings_date:
                        # Fetch it from cached earnings sources (Finnhub primary; Yahoo fallback/confirm)
                        # Use a long enough window to cover the back expiry (e.g. 30/90 pairs).
                        days_ahead = max(120, int(dte2) + 7)
                        earnings_date = self.earnings_checker.get_earnings_date(ticker, days_ahead=days_ahead)
                    if earnings_date:
                        next_earnings = earnings_date.strftime('%Y-%m-%d')
                
                opportunity = {
                    'ticker': ticker,
                    'price': current_price,
                    'ma_200': round(ma_200, 2) if ma_200 else None,
                    'above_ma_200': above_ma_200,
                    'expiry1': expiry1,
                    'expiry2': expiry2,
                    'dte1': dte1,
                    'dte2': dte2,
                    'strike1': iv_data1.get('atm_strike') if iv_data1 else None,
                    'strike2': iv_data2.get('atm_strike') if iv_data2 else None,
                    'call_iv1': round(iv_data1['call_iv'], 2) if iv_data1['call_iv'] else None,
                    'call_iv2': round(iv_data2['call_iv'], 2) if iv_data2['call_iv'] else None,
                    'put_iv1': round(iv_data1['put_iv'], 2) if iv_data1['put_iv'] else None,
                    'put_iv2': round(iv_data2['put_iv'], 2) if iv_data2['put_iv'] else None,
                    'avg_iv1': round(iv_data1['avg_iv'], 2),
                    'avg_iv2': round(iv_data2['avg_iv'], 2),
                    # Option prices (front month)
                    'call1_bid': round(iv_data1.get('call_bid'), 2) if iv_data1.get('call_bid') else None,
                    'call1_ask': round(iv_data1.get('call_ask'), 2) if iv_data1.get('call_ask') else None,
                    'call1_mid': round(iv_data1.get('call_mid'), 2) if iv_data1.get('call_mid') else None,
                    'put1_bid': round(iv_data1.get('put_bid'), 2) if iv_data1.get('put_bid') else None,
                    'put1_ask': round(iv_data1.get('put_ask'), 2) if iv_data1.get('put_ask') else None,
                    'put1_mid': round(iv_data1.get('put_mid'), 2) if iv_data1.get('put_mid') else None,
                    # Option prices (back month)
                    'call2_bid': round(iv_data2.get('call_bid'), 2) if iv_data2.get('call_bid') else None,
                    'call2_ask': round(iv_data2.get('call_ask'), 2) if iv_data2.get('call_ask') else None,
                    'call2_mid': round(iv_data2.get('call_mid'), 2) if iv_data2.get('call_mid') else None,
                    'put2_bid': round(iv_data2.get('put_bid'), 2) if iv_data2.get('put_bid') else None,
                    'put2_ask': round(iv_data2.get('put_ask'), 2) if iv_data2.get('put_ask') else None,
                    'put2_mid': round(iv_data2.get('put_mid'), 2) if iv_data2.get('put_mid') else None,
                    # Forward factor ratios
                    'ff_call': round(ff_ratio_call, 3) if ff_ratio_call else None,
                    'ff_put': round(ff_ratio_put, 3) if ff_ratio_put else None,
                    'ff_avg': round(ff_ratio_avg, 3) if ff_ratio_avg else None,
                    # Forward variance (annualized) - for debugging
                    'fwd_var_call': round(result_call.get('fwd_var'), 6) if result_call else None,
                    'fwd_var_put': round(result_put.get('fwd_var'), 6) if result_put else None,
                    'fwd_var_avg': round(result_avg.get('fwd_var'), 6) if result_avg else None,
                    # Forward volatility (annualized %) - for debugging
                    'fwd_vol_call': round(result_call.get('fwd_sigma_pct'), 2) if result_call else None,
                    'fwd_vol_put': round(result_put.get('fwd_sigma_pct'), 2) if result_put else None,
                    'fwd_vol_avg': round(result_avg.get('fwd_sigma_pct'), 2) if result_avg else None,
                    'next_earnings': next_earnings
                }
                opportunities.append(opportunity)
                
                print(f"  -> FOUND!")
                if ff_ratio_call:
                    print(f"     Call FF = {ff_ratio_call:.3f}")
                if ff_ratio_put:
                    print(f"     Put FF  = {ff_ratio_put:.3f}")
                print(f"     Avg FF  = {ff_ratio_avg:.3f}")
                print(f"     Fwd Vol = {result_avg.get('fwd_sigma_pct'):.2f}% (annualized)\n")
            else:
                ff_str_avg = f"{ff_ratio_avg:.3f}" if ff_ratio_avg is not None else "N/A"
                ff_str_call = f"{ff_ratio_call:.3f}" if ff_ratio_call is not None else "N/A"
                ff_str_put = f"{ff_ratio_put:.3f}" if ff_ratio_put is not None else "N/A"
                print(f"  -> Call FF={ff_str_call}, Put FF={ff_str_put}, Avg FF={ff_str_avg}\n")
        
        # Filter out opportunities with earnings before back month expiry
        if self.check_earnings and self.earnings_checker and opportunities:
            print(f"\n  Checking for earnings before back expiry...")
            opportunities = self.earnings_checker.filter_opportunities(opportunities, verbose=True)
        
        return opportunities


# Reconnect to IB every N tickers to avoid memory buildup
RECONNECT_INTERVAL = 100


def rank_tickers_by_iv(scanner: IBScanner, tickers: List[str], top_n: Optional[int] = None, 
                       reconnect_interval: int = RECONNECT_INTERVAL) -> List[tuple]:
    """
    Rank tickers by near-term IV to prioritize high IV stocks.
    
    Args:
        scanner: IBScanner instance
        tickers: List of ticker symbols
        top_n: Return only top N tickers (None = return all)
        reconnect_interval: Reconnect to IB every N tickers to avoid memory buildup
    
    Returns:
        List of (ticker, iv, price) tuples sorted by IV descending
    """
    print("\n" + "=" * 80)
    print("RANKING TICKERS BY NEAR-TERM IV")
    print("=" * 80)
    print("This helps prioritize high-volatility opportunities...\n")
    
    ticker_ivs = []
    tickers_since_reconnect = 0
    total = len(tickers)
    
    for i, ticker in enumerate(tickers, 1):
        if scanner.excluded_tickers.is_excluded(ticker):
            print(f"[{i}/{total}] Checking {ticker}... [SKIP] Excluded")
            continue
        # Periodic reconnection to avoid memory buildup
        tickers_since_reconnect += 1
        if tickers_since_reconnect >= reconnect_interval:
            print(f"\n[INFO] Reconnecting to IB to free memory ({i}/{total})...")
            try:
                scanner.disconnect()
                time.sleep(2)  # Wait for clean disconnect
                if not scanner.connect():
                    print("[ERROR] Failed to reconnect to IB")
                    break
                tickers_since_reconnect = 0
                print(f"[OK] Reconnected successfully\n")
            except Exception as e:
                print(f"[ERROR] Reconnection failed: {e}")
                break
        
        print(f"[{i}/{total}] Checking {ticker}...", end=" ")
        
        try:
            price = scanner.get_stock_price(ticker)
            if not price:
                print("[ERROR] No price data")
                continue
            
            iv = scanner.get_near_term_iv(ticker, price)
            if iv:
                ticker_ivs.append((ticker, iv, price))
                print(f"[OK] IV: {iv:.1f}%")
            else:
                print("[WARNING] No IV data")
            
            time.sleep(0.05)  # Reduced rate limiting for faster scans
            
        except Exception as e:
            print(f"[ERROR] Error: {e}")
    
    # Sort by IV descending
    ticker_ivs.sort(key=lambda x: x[1], reverse=True)
    
    print("\n" + "=" * 80)
    print("IV RANKING RESULTS")
    print("=" * 80)
    
    for i, (ticker, iv, price) in enumerate(ticker_ivs[:top_n] if top_n else ticker_ivs, 1):
        print(f"{i:2d}. {ticker:6s} - IV: {iv:5.1f}% (Price: ${price:.2f})")
    
    if top_n and len(ticker_ivs) > top_n:
        print(f"\n(Showing top {top_n} of {len(ticker_ivs)} tickers)")
    
    return ticker_ivs[:top_n] if top_n else ticker_ivs


def rank_tickers_by_underlying_iv(
    scanner: IBScanner,
    tickers: List[str],
    top_n: Optional[int] = None,
    batch_size: int = 75,
) -> List[tuple]:
    """Rank tickers by underlying implied volatility (snapshot).

    This is much faster than option-chain based IV because it avoids:
    - reqSecDefOptParams per ticker
    - reqMktData on option contracts
    - fixed sleeps per ticker

    Notes:
    - Requires the IB account to have market data permissions for the IV fields.
    - Falls back to historical volatility if implied vol is unavailable.
    """

    print("\n" + "=" * 80)
    print("RANKING TICKERS BY UNDERLYING IV (SNAPSHOT)")
    print("=" * 80)
    print("Fast path: uses stock snapshot fields (impliedVolatility / histVolatility).\n")

    results: List[tuple] = []
    tickers = [t for t in tickers if not scanner.excluded_tickers.is_excluded(t)]
    total = len(tickers)

    def _process_single(symbol: str) -> None:
        if scanner.excluded_tickers.is_excluded(symbol):
            return

        contract = Stock(symbol, 'SMART', 'USD')
        try:
            try:
                scanner.ib.qualifyContracts(contract)
            except Exception as e:
                if scanner._should_exclude_on_exception(symbol, e):
                    scanner.excluded_tickers.add(symbol, reason=str(e), source='qualifyContracts:underlyingIV')
                return

            if not getattr(contract, 'conId', 0):
                last = scanner._last_ib_error_by_symbol.get(symbol.upper())
                if last and int(last.get('code') or 0) == 200:
                    scanner.excluded_tickers.add(symbol, reason=str(last.get('msg') or 'Error 200'), source='qualifyContracts:underlyingIV')
                return

            tickers_data = scanner.ib.reqTickers(contract)
            if not tickers_data:
                return
            tkr_data = tickers_data[0]

            price = tkr_data.marketPrice()
            if not price or price <= 0:
                if getattr(tkr_data, 'last', None) and tkr_data.last > 0:
                    price = tkr_data.last
            if not price or price <= 0:
                return

            iv = getattr(tkr_data, 'impliedVolatility', None)
            if iv and iv > 0:
                iv_pct = iv * 100
            else:
                hv = getattr(tkr_data, 'histVolatility', None)
                if hv and hv > 0:
                    iv_pct = hv * 100
                else:
                    return

            scanner.price_cache[symbol] = float(price)
            results.append((symbol, float(iv_pct), float(price)))

        except Exception as e:
            if scanner._should_exclude_on_exception(symbol, e):
                scanner.excluded_tickers.add(symbol, reason=str(e), source='reqTickers:underlyingIV')
            return

    # Build + qualify stock contracts in batches, then snapshot them.
    for start in range(0, total, batch_size):
        batch = tickers[start:start + batch_size]
        contracts = [Stock(t, 'SMART', 'USD') for t in batch]

        try:
            try:
                scanner.ib.qualifyContracts(*contracts)
            except Exception as e:
                print(f"[WARNING] Qualify batch {start + 1}-{min(start + batch_size, total)} failed; falling back to per-ticker. Error: {e}")
                for sym in batch:
                    _process_single(sym)
                continue

            # qualifyContracts may not raise even when IB returns error 200; drop + persist excludes.
            for c in contracts:
                sym = getattr(c, 'symbol', None)
                if not sym:
                    continue
                if not getattr(c, 'conId', 0):
                    last = scanner._last_ib_error_by_symbol.get(str(sym).upper())
                    if last and int(last.get('code') or 0) == 200:
                        scanner.excluded_tickers.add(sym, reason=str(last.get('msg') or 'Error 200'), source='qualifyContracts:underlyingIV')

            try:
                tickers_data = scanner.ib.reqTickers(*contracts)
            except Exception as e:
                print(f"[WARNING] Snapshot batch {start + 1}-{min(start + batch_size, total)} failed; falling back to per-ticker. Error: {e}")
                for sym in batch:
                    _process_single(sym)
                continue

            for tkr_data in tickers_data:
                symbol = getattr(tkr_data.contract, 'symbol', None)
                if not symbol or scanner.excluded_tickers.is_excluded(symbol):
                    continue

                price = tkr_data.marketPrice()
                if not price or price <= 0:
                    if getattr(tkr_data, 'last', None) and tkr_data.last > 0:
                        price = tkr_data.last

                if not price or price <= 0:
                    continue

                # Prefer implied vol; fallback to historical vol.
                iv = getattr(tkr_data, 'impliedVolatility', None)
                if iv and iv > 0:
                    iv_pct = iv * 100
                else:
                    hv = getattr(tkr_data, 'histVolatility', None)
                    if hv and hv > 0:
                        iv_pct = hv * 100
                    else:
                        continue

                scanner.price_cache[str(symbol)] = float(price)
                results.append((str(symbol), float(iv_pct), float(price)))

        except Exception as e:
            print(f"[WARNING] Batch {start + 1}-{min(start + batch_size, total)} failed unexpectedly: {e}")
            for sym in batch:
                _process_single(sym)
            continue

    results.sort(key=lambda x: x[1], reverse=True)

    if top_n:
        return results[:top_n]
    return results


def scan_batch(scanner: IBScanner, tickers: List[str], threshold: float = 0.2, 
               rank_by_iv: bool = True, top_n: Optional[int] = None) -> List[Dict]:
    """
    Scan multiple tickers for forward volatility opportunities.
    
    Args:
        scanner: IBScanner instance
        tickers: List of ticker symbols to scan
        threshold: FF threshold (default: 0.2)
        rank_by_iv: If True, rank tickers by IV first (default: True)
        top_n: If rank_by_iv=True, scan only top N tickers (None = scan all)
    
    Returns:
        List of all opportunities found
    """
    if rank_by_iv:
        ranked = rank_tickers_by_iv(scanner, tickers, top_n)
        scan_list = [ticker for ticker, iv, price in ranked]
    else:
        scan_list = tickers
    
    print("\n" + "=" * 80)
    print(f"SCANNING {len(scan_list)} TICKERS FOR OPPORTUNITIES")
    print("=" * 80)
    
    all_opportunities = []
    
    for i, ticker in enumerate(scan_list, 1):
        if scanner.excluded_tickers.is_excluded(ticker):
            print(f"\n[{i}/{len(scan_list)}] {ticker}... [SKIP] Excluded")
            continue
        print(f"\n[{i}/{len(scan_list)}] {ticker}...")
        opportunities = scanner.scan_ticker(ticker, threshold)
        all_opportunities.extend(opportunities)
        
        if opportunities:
            print(f"  [+] Found {len(opportunities)} opportunity(ies)")
        else:
            print(f"  [-] No opportunities")
    
    return all_opportunities


def main():
    """Main function."""
    print("=" * 80)
    print("INTERACTIVE BROKERS FORWARD VOLATILITY SCANNER")
    print("=" * 80)
    print()
    
    if not IB_AVAILABLE:
        print("Please install ib_insync:")
        print("  pip install ib_insync")
        return
    
    # Connection settings
    print("Connection Settings:")
    print("  Default: localhost:7497 (TWS Paper Trading)")
    print()
    
    port_input = input("Enter port (press Enter for 7497): ").strip()
    port = int(port_input) if port_input else 7497
    
    scanner = IBScanner(port=port)
    
    if not scanner.connect():
        return
    
    try:
        # Test with TSLA
        print("\n" + "=" * 80)
        print("SCANNING TSLA")
        print("=" * 80)
        
        opportunities = scanner.scan_ticker('TSLA', threshold=0.4)
        
        if opportunities:
            df = pd.DataFrame(opportunities)
            print("\n" + "=" * 140)
            print("OPPORTUNITIES FOUND (FF > 0.4)".center(140))
            print("=" * 140)
            print()
            print_bordered_table(df)
            
            # Save to CSV
            filename = f"forward_vol_IB_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"\nResults saved to {filename}")
        else:
            print("\nNo opportunities found above threshold 0.4")
        
        # Ask to scan more
        print("\n" + "=" * 80)
        more = input("\nScan more tickers? (y/n): ").strip().lower()
        
        if more == 'y':
            tickers_input = input("Enter tickers (comma-separated, e.g., AAPL,MSFT,NVDA): ")
            tickers = [t.strip().upper() for t in tickers_input.split(',')]
            
            all_opportunities = []
            for ticker in tickers:
                opps = scanner.scan_ticker(ticker, threshold=0.4)
                all_opportunities.extend(opps)
            
            if all_opportunities:
                df = pd.DataFrame(all_opportunities)
                df = df.sort_values('ff_ratio', ascending=False)
                print("\n" + "=" * 140)
                print("ALL OPPORTUNITIES (FF > 0.4)".center(140))
                print("=" * 140)
                print()
                print_bordered_table(df)
                
                filename = f"forward_vol_IB_multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False)
                print(f"\nResults saved to {filename}")
    
    finally:
        scanner.disconnect()
        print("\nDisconnected from Interactive Brokers")


if __name__ == "__main__":
    main()
