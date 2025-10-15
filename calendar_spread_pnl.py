"""
Calendar Spread P&L Calculator
Analyzes potential profit/loss for selling front month and buying back month
"""

import math
from datetime import datetime, timedelta

def black_scholes_price(S, K, T, r, sigma, option_type='call'):
    """
    Simple Black-Scholes option pricing.
    S: Stock price
    K: Strike price
    T: Time to expiration (in years)
    r: Risk-free rate
    sigma: Volatility (decimal)
    """
    if T <= 0:
        # At expiration
        if option_type == 'call':
            return max(S - K, 0)
        else:
            return max(K - S, 0)
    
    from math import log, sqrt, exp
    from scipy.stats import norm
    
    d1 = (log(S/K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
    else:
        price = K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price


def calculate_calendar_spread_pnl():
    """Calculate P&L for TSLA calendar spread."""
    
    print("=" * 80)
    print("CALENDAR SPREAD P&L ANALYSIS")
    print("=" * 80)
    print()
    print("Trade Setup from TSLA scan:")
    print("  Sell: Oct 24 (8 DTE) options at IV=71.23%")
    print("  Buy:  Oct 31 (15 DTE) options at IV=63.98%")
    print("  Current Price: $435.70")
    print("  ATM Strike: $435")
    print()
    print("Scenario: Front month sold 15 minutes before expiration (Oct 24)")
    print("=" * 80)
    print()
    
    # Trade parameters
    current_price = 435.70
    strike = 435.0
    
    # Entry (today - Oct 15)
    front_dte_entry = 8
    back_dte_entry = 15
    front_iv_entry = 0.7123
    back_iv_entry = 0.6398
    
    # Exit (Oct 24, 15 min before front expiry)
    # Front month: 15 minutes = 0.00001 years (essentially worthless)
    front_dte_exit = 0.00001  
    back_dte_exit = 7  # Back month still has 7 days
    
    r = 0.045  # Risk-free rate
    
    print("ENTRY PRICES (Oct 15):")
    print("-" * 80)
    
    # Calculate entry prices
    front_call_entry = black_scholes_price(current_price, strike, front_dte_entry/365, r, front_iv_entry, 'call')
    front_put_entry = black_scholes_price(current_price, strike, front_dte_entry/365, r, front_iv_entry, 'put')
    back_call_entry = black_scholes_price(current_price, strike, back_dte_entry/365, r, back_iv_entry, 'call')
    back_put_entry = black_scholes_price(current_price, strike, back_dte_entry/365, r, back_iv_entry, 'put')
    
    print(f"  Front Call (8 DTE, IV=71.23%): ${front_call_entry:.2f}")
    print(f"  Front Put  (8 DTE, IV=71.23%): ${front_put_entry:.2f}")
    print(f"  Back Call  (15 DTE, IV=63.98%): ${back_call_entry:.2f}")
    print(f"  Back Put   (15 DTE, IV=63.98%): ${back_put_entry:.2f}")
    print()
    
    # Net debit
    call_spread_debit = back_call_entry - front_call_entry
    put_spread_debit = back_put_entry - front_put_entry
    
    print(f"  Call Calendar Spread Debit: ${call_spread_debit:.2f}")
    print(f"  Put Calendar Spread Debit:  ${put_spread_debit:.2f}")
    print()
    
    print("\nEXIT PRICES (Oct 24, 15 min before expiration):")
    print("-" * 80)
    
    # Scenarios: stock price at different levels
    scenarios = [
        ("Down 5%", current_price * 0.95),
        ("Down 2%", current_price * 0.98),
        ("Unchanged", current_price),
        ("Up 2%", current_price * 1.02),
        ("Up 5%", current_price * 1.05),
    ]
    
    print()
    print("CALL CALENDAR SPREAD (Buy $435 Call, Sell $435 Call):")
    print("-" * 80)
    print(f"{'Scenario':<15} {'Price':<10} {'Front Worth':<12} {'Back Worth':<12} {'P&L':<10} {'Return':<10}")
    print("-" * 80)
    
    for scenario_name, exit_price in scenarios:
        # Front month: worthless or intrinsic only
        front_call_exit = max(exit_price - strike, 0)
        
        # Back month: still has time value (assume IV drops to 55% after event)
        back_iv_exit = 0.55
        back_call_exit = black_scholes_price(exit_price, strike, back_dte_exit/365, r, back_iv_exit, 'call')
        
        # P&L calculation
        front_pnl = front_call_entry - front_call_exit  # We sold this
        back_pnl = back_call_exit - back_call_entry      # We bought this
        total_pnl = front_pnl + back_pnl
        return_pct = (total_pnl / call_spread_debit) * 100
        
        print(f"{scenario_name:<15} ${exit_price:<9.2f} ${front_call_exit:<11.2f} ${back_call_exit:<11.2f} ${total_pnl:<9.2f} {return_pct:>6.1f}%")
    
    print()
    print("\nPUT CALENDAR SPREAD (Buy $435 Put, Sell $435 Put):")
    print("-" * 80)
    print(f"{'Scenario':<15} {'Price':<10} {'Front Worth':<12} {'Back Worth':<12} {'P&L':<10} {'Return':<10}")
    print("-" * 80)
    
    for scenario_name, exit_price in scenarios:
        # Front month: worthless or intrinsic only
        front_put_exit = max(strike - exit_price, 0)
        
        # Back month: still has time value
        back_iv_exit = 0.55
        back_put_exit = black_scholes_price(exit_price, strike, back_dte_exit/365, r, back_iv_exit, 'put')
        
        # P&L calculation
        front_pnl = front_put_entry - front_put_exit
        back_pnl = back_put_exit - back_put_entry
        total_pnl = front_pnl + back_pnl
        return_pct = (total_pnl / put_spread_debit) * 100
        
        print(f"{scenario_name:<15} ${exit_price:<9.2f} ${front_put_exit:<11.2f} ${back_put_exit:<11.2f} ${total_pnl:<9.2f} {return_pct:>6.1f}%")
    
    print()
    print("=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print(f"• Initial Investment (Call): ${call_spread_debit:.2f}")
    print(f"• Initial Investment (Put):  ${put_spread_debit:.2f}")
    print()
    print("• BEST CASE: Stock stays near ATM ($435)")
    print("  - Front month expires worthless (keep premium)")
    print("  - Back month retains most value")
    print("  - Maximum profit when realized vol < implied vol")
    print()
    print("• RISK: Large stock move")
    print("  - If stock moves far from strike, spread value decreases")
    print("  - Both options become ITM or OTM")
    print()
    print("• IV CRUSH BENEFIT:")
    print("  - If IV drops from 71% to 55% after front expiry")
    print("  - Front month sold at high IV (good)")
    print("  - Back month bought at lower IV (good)")
    print()
    print("• Greeks:")
    print("  - Positive Theta (time decay helps)")
    print("  - Negative Vega initially (IV drop helps)")
    print("  - Delta near zero (stock movement less important)")
    print("=" * 80)


if __name__ == "__main__":
    try:
        from scipy.stats import norm
        calculate_calendar_spread_pnl()
    except ImportError:
        print("Installing scipy for Black-Scholes calculation...")
        import subprocess
        subprocess.run(['pip', 'install', 'scipy'], check=False)
        print("\nPlease run the script again.")
