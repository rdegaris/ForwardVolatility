"""
Simple test to fetch TSLA option data for specific DTEs
Tests Yahoo Finance API connection with a single ticker
"""

import yfinance as yf
from datetime import datetime, timedelta
import time


def calculate_dte(expiry_date_str):
    """Calculate days to expiration from date string."""
    try:
        expiry = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        today = datetime.now()
        dte = (expiry - today).days
        return max(0, dte)
    except:
        return 0


def get_atm_iv(ticker_obj, expiry_date, current_price):
    """Get ATM implied volatility for a specific expiry."""
    try:
        chain = ticker_obj.option_chain(expiry_date)
        calls = chain.calls
        puts = chain.puts
        
        if calls.empty or puts.empty:
            return None
        
        # Find ATM options
        calls['distance'] = abs(calls['strike'] - current_price)
        puts['distance'] = abs(puts['strike'] - current_price)
        
        atm_call = calls.nsmallest(1, 'distance')
        atm_put = puts.nsmallest(1, 'distance')
        
        # Get IVs
        call_iv = None
        put_iv = None
        
        if not atm_call.empty and 'impliedVolatility' in atm_call.columns:
            call_iv = atm_call.iloc[0]['impliedVolatility']
            if call_iv and call_iv > 0:
                call_iv = call_iv * 100
        
        if not atm_put.empty and 'impliedVolatility' in atm_put.columns:
            put_iv = atm_put.iloc[0]['impliedVolatility']
            if put_iv and put_iv > 0:
                put_iv = put_iv * 100
        
        # Average if both available
        if call_iv and put_iv:
            return (call_iv + put_iv) / 2
        return call_iv or put_iv
        
    except Exception as e:
        print(f"  Error getting IV for {expiry_date}: {e}")
        return None


def main():
    print("=" * 80)
    print("TSLA OPTION DATA TEST - Target DTEs: 7, 14, 21")
    print("=" * 80)
    print()
    
    # Add delay to avoid rate limit
    time.sleep(1)
    
    print("Fetching TSLA data...")
    ticker = yf.Ticker("TSLA")
    
    # Get current price
    print("Getting current price...")
    try:
        hist = ticker.history(period='1d')
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            print(f"  Current Price: ${current_price:.2f}")
        else:
            print("  ERROR: No price data available")
            return
    except Exception as e:
        print(f"  ERROR: Could not fetch price - {e}")
        return
    
    # Get available expiries
    print("\nFetching available expiration dates...")
    time.sleep(0.5)
    
    try:
        expiries = ticker.options
        print(f"  Found {len(expiries)} expiration dates")
    except Exception as e:
        print(f"  ERROR: Could not fetch expiries - {e}")
        return
    
    if not expiries:
        print("  ERROR: No option expiries available")
        return
    
    # Calculate DTEs and find closest to 7, 14, 21
    print("\nAnalyzing expiration dates...")
    expiry_data = []
    for exp in expiries:
        dte = calculate_dte(exp)
        expiry_data.append({'expiry': exp, 'dte': dte})
    
    # Sort by DTE
    expiry_data.sort(key=lambda x: x['dte'])
    
    print(f"\nAll available expiries (first 10):")
    for i, exp in enumerate(expiry_data[:10]):
        print(f"  {i+1}. {exp['expiry']} - DTE: {exp['dte']}")
    
    # Find closest to target DTEs
    targets = [7, 14, 21]
    selected = []
    
    print(f"\nSearching for DTEs closest to {targets}...")
    for target in targets:
        closest = min(expiry_data, key=lambda x: abs(x['dte'] - target))
        selected.append(closest)
        print(f"  Target DTE {target}: Found {closest['expiry']} (DTE={closest['dte']})")
    
    # Fetch IV for each selected expiry
    print("\n" + "=" * 80)
    print("FETCHING IMPLIED VOLATILITY DATA")
    print("=" * 80)
    
    results = []
    for exp_info in selected:
        expiry = exp_info['expiry']
        dte = exp_info['dte']
        
        print(f"\nExpiry: {expiry} (DTE={dte})")
        time.sleep(0.5)  # Rate limiting
        
        iv = get_atm_iv(ticker, expiry, current_price)
        
        if iv:
            print(f"  ATM IV: {iv:.2f}%")
            results.append({
                'expiry': expiry,
                'dte': dte,
                'iv': iv
            })
        else:
            print(f"  ATM IV: Not available")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Ticker: TSLA")
    print(f"Price: ${current_price:.2f}")
    print()
    
    if results:
        print("+------------+------+--------+")
        print("| Expiry     | DTE  | IV (%) |")
        print("+------------+------+--------+")
        for r in results:
            print(f"| {r['expiry']} | {r['dte']:4d} | {r['iv']:6.2f} |")
        print("+------------+------+--------+")
        
        print("\n[SUCCESS] Connection test passed!")
        print("Yahoo Finance API is working properly.")
    else:
        print("[WARNING] Could not fetch IV data.")
        print("API may be experiencing issues or rate limiting.")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
