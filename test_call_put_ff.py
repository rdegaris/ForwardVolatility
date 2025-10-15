"""
Quick test to show call vs put Forward Factor for TSLA
"""

import sys
sys.path.insert(0, '.')

from scanner_ib import IBScanner

def main():
    print("=" * 80)
    print("TSLA - CALL vs PUT FORWARD FACTOR COMPARISON")
    print("=" * 80)
    print()
    
    scanner = IBScanner(port=7497)
    
    if not scanner.connect():
        print("Could not connect to IB")
        return
    
    try:
        opportunities = scanner.scan_ticker('TSLA', threshold=0.2)
        
        if opportunities:
            print("\n" + "=" * 80)
            print("RESULTS - FORWARD FACTOR BY OPTION TYPE")
            print("=" * 80)
            print()
            
            for opp in opportunities:
                print(f"Expiry Pair: {opp['expiry1']} ({opp['dte1']}d) → {opp['expiry2']} ({opp['dte2']}d)")
                print("-" * 80)
                
                # Call spread
                if opp['ff_call']:
                    print(f"CALL CALENDAR SPREAD:")
                    print(f"  Front IV:  {opp['call_iv1']:.2f}%")
                    print(f"  Back IV:   {opp['call_iv2']:.2f}%")
                    print(f"  Forward Factor: {opp['ff_call']:.3f} ({opp['ff_call']*100:.1f}%)")
                else:
                    print(f"CALL CALENDAR SPREAD: No data")
                
                print()
                
                # Put spread
                if opp['ff_put']:
                    print(f"PUT CALENDAR SPREAD:")
                    print(f"  Front IV:  {opp['put_iv1']:.2f}%")
                    print(f"  Back IV:   {opp['put_iv2']:.2f}%")
                    print(f"  Forward Factor: {opp['ff_put']:.3f} ({opp['ff_put']*100:.1f}%)")
                else:
                    print(f"PUT CALENDAR SPREAD: No data")
                
                print()
                
                # Average (blended)
                print(f"BLENDED (AVG):")
                print(f"  Front IV:  {opp['avg_iv1']:.2f}%")
                print(f"  Back IV:   {opp['avg_iv2']:.2f}%")
                print(f"  Forward Factor: {opp['ff_avg']:.3f} ({opp['ff_avg']*100:.1f}%)")
                
                print()
                print("=" * 80)
                print()
                
                # Analysis
                if opp['ff_call'] and opp['ff_put']:
                    diff = opp['ff_put'] - opp['ff_call']
                    if abs(diff) > 0.05:
                        if diff > 0:
                            print(f"📊 PUT spread has {diff:.3f} higher FF → Better opportunity")
                        else:
                            print(f"📊 CALL spread has {abs(diff):.3f} higher FF → Better opportunity")
                    else:
                        print(f"📊 Call and Put spreads are similar (diff: {abs(diff):.3f})")
                    print()
        else:
            print("\nNo opportunities found with FF > 0.2")
    
    finally:
        scanner.disconnect()
        print("\nDisconnected")


if __name__ == "__main__":
    main()
