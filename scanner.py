"""
Forward Volatility Scanner
Scans option chains for forward volatility opportunities where FF > 0.4
"""

import math
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Tuple, Optional
import time


# Nasdaq 100 stocks (subset - you can expand this list)
NASDAQ_100 = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST', 'ASML',
    'NFLX', 'AMD', 'PEP', 'ADBE', 'CSCO', 'TMUS', 'INTC', 'CMCSA', 'TXN', 'QCOM',
    'INTU', 'HON', 'AMGN', 'AMAT', 'SBUX', 'ISRG', 'BKNG', 'GILD', 'ADI', 'VRTX',
    'ADP', 'MDLZ', 'REGN', 'PANW', 'LRCX', 'MU', 'PYPL', 'SNPS', 'CDNS', 'MELI',
    'KLAC', 'ABNB', 'CRWD', 'MAR', 'CTAS', 'MRVL', 'ORLY', 'CSX', 'ADSK', 'DASH',
    'FTNT', 'NXPI', 'WDAY', 'MNST', 'CHTR', 'PCAR', 'AEP', 'CPRT', 'ROST', 'PAYX',
    'ODFL', 'KDP', 'FAST', 'CEG', 'EA', 'DXCM', 'GEHC', 'BKR', 'EXC', 'CTSH',
    'TEAM', 'IDXX', 'KHC', 'LULU', 'CCEP', 'XEL', 'VRSK', 'FANG', 'TTWO', 'ZS',
    'CSGP', 'ANSS', 'ON', 'DDOG', 'CDW', 'GFS', 'BIIB', 'WBD', 'MDB', 'ILMN',
    'ARM', 'MRNA', 'SMCI', 'WBA', 'DLTR', 'PDD', 'ALGN', 'RIVN', 'LCID', 'ZM'
]


def calculate_forward_vol(dte1: float, iv1: float, dte2: float, iv2: float) -> Optional[Dict]:
    """
    Calculate forward volatility and forward factor.
    
    Args:
        dte1: Days to expiration for near-term option
        iv1: Implied volatility for near-term (as percentage, e.g., 25.0 for 25%)
        dte2: Days to expiration for far-term option
        iv2: Implied volatility for far-term (as percentage)
    
    Returns:
        Dictionary with results or None if calculation is invalid
    """
    # Validate inputs
    if dte1 < 0 or dte2 < 0 or iv1 < 0 or iv2 < 0:
        return None
    if dte2 <= dte1:
        return None
    
    # Convert to annualized terms
    T1 = dte1 / 365.0
    T2 = dte2 / 365.0
    s1 = iv1 / 100.0  # Convert percentage to decimal
    s2 = iv2 / 100.0
    
    # Calculate total variances
    tv1 = (s1 ** 2) * T1
    tv2 = (s2 ** 2) * T2
    
    # Calculate forward variance
    denom = T2 - T1
    if denom <= 0:
        return None
    
    fwd_var = (tv2 - tv1) / denom
    
    # Check for negative forward variance
    if fwd_var < 0:
        return None
    
    # Calculate forward volatility (annualized)
    fwd_sigma = math.sqrt(fwd_var)
    
    # Calculate Forward Factor
    if fwd_sigma == 0.0:
        ff_ratio = None
    else:
        ff_ratio = (s1 - fwd_sigma) / fwd_sigma
    
    return {
        'T1': T1,
        'T2': T2,
        's1': s1,
        's2': s2,
        'tv1': tv1,
        'tv2': tv2,
        'fwd_var': fwd_var,
        'fwd_sigma': fwd_sigma,
        'fwd_sigma_pct': fwd_sigma * 100,
        'ff_ratio': ff_ratio,
        'ff_pct': ff_ratio * 100 if ff_ratio is not None else None
    }


def get_atm_iv(ticker: str, expiry_date: str, stock_obj=None) -> Optional[float]:
    """
    Get ATM (at-the-money) implied volatility for a given ticker and expiry.
    
    Args:
        ticker: Stock ticker symbol
        expiry_date: Expiration date string in format returned by yfinance
        stock_obj: Optional yf.Ticker object to reuse
    
    Returns:
        ATM implied volatility as percentage, or None if not found
    """
    try:
        if stock_obj is None:
            stock_obj = yf.Ticker(ticker)
        
        # Get option chain for the expiry
        opt_chain = stock_obj.option_chain(expiry_date)
        
        # Get current price from fast_info or info
        try:
            current_price = stock_obj.fast_info.get('lastPrice') or stock_obj.fast_info.get('regularMarketPrice')
        except:
            current_price = stock_obj.info.get('regularMarketPrice') or stock_obj.info.get('currentPrice')
        
        if current_price is None:
            return None
        
        # Combine calls and puts
        calls = opt_chain.calls
        puts = opt_chain.puts
        
        if calls.empty or puts.empty:
            return None
        
        # Find ATM options (closest to current price)
        calls['distance'] = abs(calls['strike'] - current_price)
        puts['distance'] = abs(puts['strike'] - current_price)
        
        atm_call = calls.nsmallest(1, 'distance')
        atm_put = puts.nsmallest(1, 'distance')
        
        # Get IVs (impliedVolatility is already in decimal form, need to convert to percentage)
        call_iv = None
        put_iv = None
        
        if not atm_call.empty and 'impliedVolatility' in atm_call.columns:
            call_iv = atm_call.iloc[0]['impliedVolatility']
            if pd.notna(call_iv) and call_iv > 0:
                call_iv = call_iv * 100  # Convert to percentage
        
        if not atm_put.empty and 'impliedVolatility' in atm_put.columns:
            put_iv = atm_put.iloc[0]['impliedVolatility']
            if pd.notna(put_iv) and put_iv > 0:
                put_iv = put_iv * 100  # Convert to percentage
        
        # Average call and put IV if both available
        if call_iv is not None and put_iv is not None:
            return (call_iv + put_iv) / 2
        elif call_iv is not None:
            return call_iv
        elif put_iv is not None:
            return put_iv
        else:
            return None
            
    except Exception as e:
        # Silently fail for individual expiries
        return None


def calculate_dte(expiry_date_str: str) -> int:
    """Calculate days to expiration from date string."""
    try:
        expiry = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        today = datetime.now()
        dte = (expiry - today).days
        return max(0, dte)  # Don't return negative DTEs
    except:
        return 0


def scan_ticker(ticker: str, threshold: float = 0.4) -> List[Dict]:
    """
    Scan a single ticker for forward volatility opportunities.
    
    Args:
        ticker: Stock ticker symbol
        threshold: Minimum FF ratio to flag (default 0.4)
    
    Returns:
        List of opportunities found
    """
    opportunities = []
    
    try:
        stock = yf.Ticker(ticker)
        
        # Small delay to avoid rate limits
        time.sleep(0.5)
        
        # Get current price using history (more reliable)
        try:
            hist = stock.history(period='1d')
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
            else:
                current_price = None
        except:
            current_price = None
        
        if current_price is None:
            print(f"{ticker}: Could not fetch current price")
            return opportunities
        
        # Get expiries
        try:
            expiries = stock.options
        except Exception as e:
            print(f"{ticker}: Could not fetch options data - {str(e)[:100]}")
            return opportunities
        
        if len(expiries) < 2:
            print(f"{ticker}: Not enough expiry dates available (found {len(expiries)})")
            return opportunities
        
        print(f"\nScanning {ticker} (Price: ${current_price:.2f})...")
        
        # Compare consecutive expiries
        for i in range(len(expiries) - 1):
            expiry1 = expiries[i]
            expiry2 = expiries[i + 1]
            
            dte1 = calculate_dte(expiry1)
            dte2 = calculate_dte(expiry2)
            
            # Skip if DTEs are too close or invalid
            if dte1 < 1 or dte2 < 1 or (dte2 - dte1) < 5:
                continue
            
            # Small delay between option chain calls
            time.sleep(0.3)
            
            # Get ATM IVs
            iv1 = get_atm_iv(ticker, expiry1, stock)
            iv2 = get_atm_iv(ticker, expiry2, stock)
            
            if iv1 is None or iv2 is None:
                continue
            
            # Calculate forward vol
            result = calculate_forward_vol(dte1, iv1, dte2, iv2)
            
            if result is None:
                continue
            
            ff_ratio = result.get('ff_ratio')
            
            # Check if it meets threshold
            if ff_ratio is not None and ff_ratio >= threshold:
                opportunity = {
                    'ticker': ticker,
                    'price': current_price,
                    'expiry1': expiry1,
                    'expiry2': expiry2,
                    'dte1': dte1,
                    'dte2': dte2,
                    'iv1': iv1,
                    'iv2': iv2,
                    'fwd_vol_pct': result['fwd_sigma_pct'],
                    'ff_ratio': ff_ratio,
                    'ff_pct': result['ff_pct']
                }
                opportunities.append(opportunity)
                print(f"  ✓ FOUND: {expiry1} (DTE={dte1}, IV={iv1:.1f}%) → {expiry2} (DTE={dte2}, IV={iv2:.1f}%) | FF={ff_ratio:.3f} ({result['ff_pct']:.1f}%)")
        
        if not opportunities:
            print(f"  No opportunities above threshold {threshold}")
            
    except Exception as e:
        print(f"Error scanning {ticker}: {str(e)[:100]}")
    
    return opportunities


def scan_multiple_tickers(tickers: List[str], threshold: float = 0.4) -> pd.DataFrame:
    """
    Scan multiple tickers for forward volatility opportunities.
    
    Args:
        tickers: List of ticker symbols
        threshold: Minimum FF ratio to flag
    
    Returns:
        DataFrame of all opportunities found
    """
    all_opportunities = []
    
    for idx, ticker in enumerate(tickers, 1):
        print(f"\n[{idx}/{len(tickers)}] ", end="")
        opps = scan_ticker(ticker, threshold)
        all_opportunities.extend(opps)
        
        # Add delay between tickers to avoid rate limits
        if idx < len(tickers):
            time.sleep(1.0)
    
    if not all_opportunities:
        print("\nNo opportunities found above threshold.")
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(all_opportunities)
    
    # Sort by FF ratio descending
    df = df.sort_values('ff_ratio', ascending=False)
    
    return df


def main():
    """Main function to run the scanner."""
    print("=" * 80)
    print("FORWARD VOLATILITY SCANNER")
    print("=" * 80)
    print(f"Scanning for opportunities where Forward Factor (FF) > 0.4")
    print()
    
    # Start with AAPL as an example
    print("\n" + "=" * 80)
    print("SCANNING AAPL")
    print("=" * 80)
    aapl_opps = scan_ticker('AAPL', threshold=0.4)
    
    if aapl_opps:
        df_aapl = pd.DataFrame(aapl_opps)
        print("\n" + "=" * 80)
        print("AAPL OPPORTUNITIES")
        print("=" * 80)
        print(df_aapl.to_string(index=False))
    
    # Ask if user wants to scan more
    print("\n" + "=" * 80)
    response = input("\nScan Nasdaq 100 stocks? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n" + "=" * 80)
        print("SCANNING NASDAQ 100")
        print("=" * 80)
        print(f"This may take a while... scanning {len(NASDAQ_100)} tickers\n")
        
        df_all = scan_multiple_tickers(NASDAQ_100, threshold=0.4)
        
        if not df_all.empty:
            print("\n" + "=" * 80)
            print("ALL OPPORTUNITIES (FF > 0.4)")
            print("=" * 80)
            print(df_all.to_string(index=False))
            
            # Save to CSV
            filename = f"forward_vol_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_all.to_csv(filename, index=False)
            print(f"\nResults saved to {filename}")


if __name__ == "__main__":
    main()
