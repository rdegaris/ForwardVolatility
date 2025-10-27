"""
Forward Volatility Scanner using Interactive Brokers API
Requires: ib_insync library and IB Gateway/TWS running
"""

import math
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

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
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1, check_earnings=True):
        """
        Initialize IB connection.
        
        Args:
            host: IB Gateway/TWS host (default: localhost)
            port: 7497 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
            client_id: Unique client ID
            check_earnings: Filter out tickers with earnings in trading window (default: True)
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.check_earnings = check_earnings and EARNINGS_CHECKER_AVAILABLE
        self.earnings_checker = EarningsChecker() if self.check_earnings else None
    
    def connect(self):
        """Connect to IB Gateway or TWS."""
        try:
            print(f"Connecting to Interactive Brokers at {self.host}:{self.port}...")
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            print("  Connected successfully!")
            return True
        except Exception as e:
            print(f"  Connection failed: {e}")
            print("\nMake sure:")
            print("  1. IB Gateway or TWS is running")
            print("  2. API connections are enabled in settings")
            print("  3. Port number is correct:")
            print("     - TWS Paper: 7497")
            print("     - TWS Live: 7496")
            print("     - Gateway Paper: 4002")
            print("     - Gateway Live: 4001")
            return False
    
    def disconnect(self):
        """Disconnect from IB."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
    
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """Get current stock price."""
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            ticker_data = self.ib.reqMktData(stock, '', False, False)
            self.ib.sleep(2)  # Wait for data
            
            price = ticker_data.marketPrice()
            if price and price > 0:
                return price
            
            # Try last price if market price not available
            if ticker_data.last and ticker_data.last > 0:
                return ticker_data.last
            
            return None
        except Exception as e:
            print(f"  Error getting price: {e}")
            return None
    
    def get_option_chains(self, ticker: str) -> List[str]:
        """Get available option expiration dates."""
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            
            if not chains:
                return []
            
            # Get expirations from first chain
            expirations = sorted(chains[0].expirations)
            return expirations
        except Exception as e:
            print(f"  Error getting option chains: {e}")
            return []
    
    def get_atm_iv(self, ticker: str, expiry: str, current_price: float, debug: bool = False) -> Optional[Dict]:
        """Get ATM implied volatility for specific expiry.
        
        Returns:
            Dict with 'call_iv', 'put_iv', 'avg_iv' or None
        """
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            if not chains:
                if debug:
                    print(f"\n    [DEBUG] No chains found")
                return None
            
            strikes = chains[0].strikes
            
            # Find ATM strike
            atm_strike = min(strikes, key=lambda x: abs(x - current_price))
            
            if debug:
                print(f"\n    [DEBUG] ATM Strike: {atm_strike} (Price: {current_price})")
            
            # Get call and put
            call = Option(ticker, expiry, atm_strike, 'C', 'SMART')
            put = Option(ticker, expiry, atm_strike, 'P', 'SMART')
            
            self.ib.qualifyContracts(call, put)
            
            if debug:
                print(f"    [DEBUG] Call: {call.localSymbol if hasattr(call, 'localSymbol') else 'qualified'}")
                print(f"    [DEBUG] Put: {put.localSymbol if hasattr(put, 'localSymbol') else 'qualified'}")
            
            # Request market data with generic tick for IV
            call_ticker = self.ib.reqMktData(call, '106', False, False)  # 106 = option IV
            put_ticker = self.ib.reqMktData(put, '106', False, False)
            
            self.ib.sleep(3)  # Wait for data
            
            # Try multiple methods to get IV
            call_iv = None
            put_iv = None
            
            # Method 1: modelGreeks
            if call_ticker.modelGreeks and call_ticker.modelGreeks.impliedVol:
                call_iv = call_ticker.modelGreeks.impliedVol * 100  # Convert to percentage
                if debug:
                    print(f"    [DEBUG] Call IV (modelGreeks): {call_iv:.2f}%")
            
            if put_ticker.modelGreeks and put_ticker.modelGreeks.impliedVol:
                put_iv = put_ticker.modelGreeks.impliedVol * 100  # Convert to percentage
                if debug:
                    print(f"    [DEBUG] Put IV (modelGreeks): {put_iv:.2f}%")
            
            # Method 2: Try last price if IV not available (for very ITM/OTM)
            if not call_iv and call_ticker.last and call_ticker.last > 0:
                if debug:
                    print(f"    [DEBUG] Call has price but no IV: ${call_ticker.last}")
            
            if not put_iv and put_ticker.last and put_ticker.last > 0:
                if debug:
                    print(f"    [DEBUG] Put has price but no IV: ${put_ticker.last}")
            
            # Cancel market data subscriptions
            self.ib.cancelMktData(call)
            self.ib.cancelMktData(put)
            
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
                'avg_iv': avg_iv
            }
            
        except Exception as e:
            if debug:
                print(f"\n    [DEBUG] Exception: {e}")
            return None
    
    def scan_ticker(self, ticker: str, threshold: float = 0.4) -> List[Dict]:
        """Scan a ticker for forward volatility opportunities."""
        opportunities = []
        
        print(f"\nScanning {ticker}...")
        
        # Get current price
        current_price = self.get_stock_price(ticker)
        if not current_price:
            print(f"  Could not get price for {ticker}")
            return opportunities
        
        print(f"  Price: ${current_price:.2f}")
        
        # Get option chains
        expirations = self.get_option_chains(ticker)
        if len(expirations) < 2:
            print(f"  Not enough expiration dates")
            return opportunities
        
        print(f"  Found {len(expirations)} expiration dates")
        
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
            
            print(f"  Checking {expiry1} (DTE={dte1}) vs {expiry2} (DTE={dte2}) [Target: {target_dte1}/{target_dte2}]...")
            
            iv_data1 = self.get_atm_iv(ticker, expiry1, current_price, debug=True)
            time.sleep(0.5)
            iv_data2 = self.get_atm_iv(ticker, expiry2, current_price, debug=True)
            
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
            
            if max_ff is not None and max_ff >= threshold:
                # Get earnings date if available
                next_earnings = None
                if self.check_earnings and self.earnings_checker:
                    earnings_date = self.earnings_checker.cache.get(ticker)
                    if not earnings_date:
                        # Try to fetch it from IB
                        earnings_date = self.earnings_checker.get_earnings_date(ticker)
                    if earnings_date:
                        next_earnings = earnings_date.strftime('%Y-%m-%d')
                
                opportunity = {
                    'ticker': ticker,
                    'price': current_price,
                    'expiry1': expiry1,
                    'expiry2': expiry2,
                    'dte1': dte1,
                    'dte2': dte2,
                    'call_iv1': round(iv_data1['call_iv'], 2) if iv_data1['call_iv'] else None,
                    'call_iv2': round(iv_data2['call_iv'], 2) if iv_data2['call_iv'] else None,
                    'put_iv1': round(iv_data1['put_iv'], 2) if iv_data1['put_iv'] else None,
                    'put_iv2': round(iv_data2['put_iv'], 2) if iv_data2['put_iv'] else None,
                    'avg_iv1': round(iv_data1['avg_iv'], 2),
                    'avg_iv2': round(iv_data2['avg_iv'], 2),
                    'ff_call': round(ff_ratio_call, 3) if ff_ratio_call else None,
                    'ff_put': round(ff_ratio_put, 3) if ff_ratio_put else None,
                    'ff_avg': round(ff_ratio_avg, 3) if ff_ratio_avg else None,
                    'next_earnings': next_earnings
                }
                opportunities.append(opportunity)
                
                print(f"  -> FOUND!")
                if ff_ratio_call:
                    print(f"     Call FF = {ff_ratio_call:.3f}")
                if ff_ratio_put:
                    print(f"     Put FF  = {ff_ratio_put:.3f}")
                print(f"     Avg FF  = {ff_ratio_avg:.3f}\n")
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
