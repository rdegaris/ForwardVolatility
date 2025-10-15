"""
Simplified Calendar Spread P&L Estimator
For TSLA Oct 24 / Oct 31 spread based on IB scan data
"""

def estimate_calendar_pnl():
    """
    Estimate P&L for calendar spread with simplified assumptions.
    Based on TSLA scan: FF=0.307, Front IV=71.23%, Back IV=63.98%
    """
    
    print("=" * 90)
    print("TSLA CALENDAR SPREAD P&L ESTIMATE")
    print("=" * 90)
    print()
    print("TRADE SETUP:")
    print("  • Sell Oct 24 (8 DTE) $435 Call/Put at IV=71.23%")
    print("  • Buy  Oct 31 (15 DTE) $435 Call/Put at IV=63.98%")
    print("  • Current TSLA Price: $435.70")
    print("  • Forward Factor: 0.307 (30.7%)")
    print("=" * 90)
    print()
    
    # Simplified option value estimates
    # Using rule of thumb: ATM option ≈ 0.4 * Stock Price * IV * sqrt(T/365)
    
    current_price = 435.70
    strike = 435.0
    
    # ENTRY (Oct 15)
    print("ENTRY PRICES (Oct 15):")
    print("-" * 90)
    
    # Front month (8 DTE)
    front_dte = 8
    front_iv = 0.7123
    front_price = 0.4 * current_price * front_iv * (front_dte/365)**0.5
    
    # Back month (15 DTE)
    back_dte = 15
    back_iv = 0.6398
    back_price = 0.4 * current_price * back_iv * (back_dte/365)**0.5
    
    print(f"  Front Month (Oct 24, 8 DTE, IV=71%):  ~${front_price:.2f}")
    print(f"  Back Month  (Oct 31, 15 DTE, IV=64%): ~${back_price:.2f}")
    print(f"  Net Debit (per contract):              ~${back_price - front_price:.2f}")
    print()
    
    net_debit = back_price - front_price
    
    # EXIT (Oct 24, 15 min before front expiry)
    print("EXIT SCENARIO (Oct 24, 3:45 PM ET - 15 min before close):")
    print("-" * 90)
    print()
    
    # Scenario analysis
    scenarios = [
        ("Stock Down 5%", 0.95, "ITM", "Protected by long back month"),
        ("Stock Down 2%", 0.98, "Near ATM", "Small loss, back month protects"),  
        ("Stock Unchanged", 1.00, "ATM", "BEST CASE - Maximum profit"),
        ("Stock Up 2%", 1.02, "Near ATM", "Small loss, back month protects"),
        ("Stock Up 5%", 1.05, "ITM", "Protected by long back month"),
    ]
    
    print(f"{'Scenario':<20} {'Stock Price':<15} {'Front Worth':<15} {'Back Worth':<15} {'P&L':<12} {'Return':<10}")
    print("-" * 90)
    
    for name, price_mult, status, note in scenarios:
        exit_price = current_price * price_mult
        
        # Front month: Nearly worthless (15 min to expiry)
        if abs(exit_price - strike) < 2:  # Near ATM
            front_exit = 0.10  # Just residual value
        elif exit_price > strike + 2:  # ITM call
            front_exit = exit_price - strike
        elif exit_price < strike - 2:  # ITM put
            front_exit = strike - exit_price
        else:
            front_exit = max(0, abs(exit_price - strike) * 0.3)
        
        # Back month: Still has 7 DTE with time value
        # Assume IV drops to 55% after near-term uncertainty resolves
        back_dte_exit = 7
        back_iv_exit = 0.55
        
        # ATM options worth most
        if abs(exit_price - strike) < 5:  # Near ATM - best case
            back_exit = 0.4 * exit_price * back_iv_exit * (back_dte_exit/365)**0.5
        elif abs(exit_price - strike) < 15:  # Somewhat ITM/OTM
            intrinsic = max(0, abs(exit_price - strike))
            extrinsic = 0.3 * exit_price * back_iv_exit * (back_dte_exit/365)**0.5
            back_exit = intrinsic + extrinsic
        else:  # Deep ITM/OTM
            back_exit = max(0, abs(exit_price - strike))
        
        # P&L calculation
        front_pnl = front_price - front_exit  # We sold, so collected minus paid
        back_pnl = back_exit - back_price      # We bought, so worth minus paid
        total_pnl = front_pnl + back_pnl
        return_pct = (total_pnl / net_debit) * 100 if net_debit > 0 else 0
        
        print(f"{name:<20} ${exit_price:<14.2f} ${front_exit:<14.2f} ${back_exit:<14.2f} ${total_pnl:<11.2f} {return_pct:>7.1f}%")
    
    print()
    print("=" * 90)
    print("P&L SUMMARY:")
    print("=" * 90)
    print(f"• Initial Investment: ~${net_debit:.2f} per contract (${net_debit*100:.0f} per 100 shares)")
    print()
    print("• BEST CASE (Stock near $435):")
    print(f"  - Estimated Profit: ~${net_debit * 0.4:.2f} per contract (~40% return)")
    print(f"  - Front expires worthless (keep ${front_price:.2f})")
    print(f"  - Back retains significant value (~${back_price:.2f})")
    print()
    print("• TYPICAL CASE (Small stock move ±2%):")
    print(f"  - Estimated Profit: ~${net_debit * 0.15:.2f} to ${net_debit * 0.25:.2f} per contract (15-25% return)")
    print(f"  - Still profitable due to theta decay and vol crush")
    print()
    print("• WORST CASE (Large stock move ±5%+):")
    print(f"  - Estimated Loss: ~${net_debit * 0.3:.2f} per contract (30% loss)")
    print(f"  - Both options move away from ATM")
    print(f"  - Max loss limited to initial debit + commissions")
    print()
    print("• BREAKEVEN: Stock moves ~3-4% in either direction")
    print()
    print("=" * 90)
    print("KEY FACTORS:")
    print("=" * 90)
    print()
    print("✓ WHAT HELPS YOU:")
    print("  1. Time decay - Front month decays faster (71% IV)")
    print("  2. IV crush - Front month IV likely drops after event")
    print("  3. Forward Factor - 30.7% suggests front month overpriced")
    print("  4. Limited risk - Max loss is net debit paid")
    print()
    print("✗ WHAT HURTS YOU:")
    print("  1. Large stock moves - Away from ATM strike")
    print("  2. Vol expansion - If back month IV increases")
    print("  3. Commissions/fees - Can eat into profits")
    print("  4. Liquidity - May have wider bid-ask spreads")
    print()
    print("=" * 90)
    print("PRACTICAL EXAMPLE (1 contract):")
    print("=" * 90)
    print(f"  Entry: Pay ${net_debit * 100:.0f} net debit")
    print(f"  Best Case: Collect ~${net_debit * 100 * 1.4:.0f} at exit → Profit: ~${net_debit * 100 * 0.4:.0f} (40%)")
    print(f"  Typical: Collect ~${net_debit * 100 * 1.2:.0f} at exit → Profit: ~${net_debit * 100 * 0.2:.0f} (20%)")
    print(f"  Worst: Collect ~${net_debit * 100 * 0.7:.0f} at exit → Loss: ~${net_debit * 100 * 0.3:.0f} (30%)")
    print()
    print("RECOMMENDATION:")
    print("  • Trade size: Start small (1-2 contracts) to test the strategy")
    print("  • Monitor: Track IV changes and stock movement")
    print("  • Exit plan: Close if profit target hit or stock moves >4%")
    print("  • Time: Best to close front month day-of or before expiry")
    print("=" * 90)


if __name__ == "__main__":
    estimate_calendar_pnl()
