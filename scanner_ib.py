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
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        """
        Initialize IB connection.
        
        Args:
            host: IB Gateway/TWS host (default: localhost)
            port: 7497 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
            client_id: Unique client ID
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
    
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
    
    def get_atm_iv(self, ticker: str, expiry: str, current_price: float) -> Optional[float]:
        """Get ATM implied volatility for specific expiry."""
        try:
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            if not chains:
                return None
            
            strikes = chains[0].strikes
            
            # Find ATM strike
            atm_strike = min(strikes, key=lambda x: abs(x - current_price))
            
            # Get call and put
            call = Option(ticker, expiry, atm_strike, 'C', 'SMART')
            put = Option(ticker, expiry, atm_strike, 'P', 'SMART')
            
            self.ib.qualifyContracts(call, put)
            
            # Request market data
            call_ticker = self.ib.reqMktData(call, '', False, False)
            put_ticker = self.ib.reqMktData(put, '', False, False)
            
            self.ib.sleep(2)  # Wait for data
            
            # Get IVs
            call_iv = call_ticker.modelGreeks.impliedVol if call_ticker.modelGreeks else None
            put_iv = put_ticker.modelGreeks.impliedVol if put_ticker.modelGreeks else None
            
            # Convert to percentage
            ivs = []
            if call_iv and call_iv > 0:
                ivs.append(call_iv * 100)
            if put_iv and put_iv > 0:
                ivs.append(put_iv * 100)
            
            if ivs:
                return sum(ivs) / len(ivs)
            
            return None
        except Exception as e:
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
        
        # Compare consecutive expirations
        for i in range(min(len(expirations) - 1, 5)):  # Limit to first 5 pairs
            expiry1 = expirations[i]
            expiry2 = expirations[i + 1]
            
            dte1 = calculate_dte(expiry1)
            dte2 = calculate_dte(expiry2)
            
            if dte1 < 1 or dte2 < 1 or (dte2 - dte1) < 5:
                continue
            
            print(f"  Checking {expiry1} (DTE={dte1}) vs {expiry2} (DTE={dte2})...", end=' ')
            
            iv1 = self.get_atm_iv(ticker, expiry1, current_price)
            iv2 = self.get_atm_iv(ticker, expiry2, current_price)
            
            if iv1 is None or iv2 is None:
                print("No IV data")
                continue
            
            result = calculate_forward_vol(dte1, iv1, dte2, iv2)
            
            if result is None:
                print("Invalid")
                continue
            
            ff_ratio = result.get('ff_ratio')
            
            if ff_ratio is not None and ff_ratio >= threshold:
                opportunity = {
                    'ticker': ticker,
                    'price': current_price,
                    'expiry1': expiry1,
                    'expiry2': expiry2,
                    'dte1': dte1,
                    'dte2': dte2,
                    'iv1': round(iv1, 2),
                    'iv2': round(iv2, 2),
                    'fwd_vol_pct': round(result['fwd_sigma_pct'], 2),
                    'ff_ratio': round(ff_ratio, 3),
                    'ff_pct': round(result['ff_pct'], 1)
                }
                opportunities.append(opportunity)
                print(f"FOUND! FF={ff_ratio:.3f}")
            else:
                print(f"FF={ff_ratio:.3f if ff_ratio else 'N/A'}")
        
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
