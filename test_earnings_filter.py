"""
Test earnings filter with the scanner
"""

import sys
sys.path.insert(0, '.')

from scanner_ib import IBScanner

def main():
    print("=" * 80)
    print("SCANNER WITH EARNINGS FILTER TEST")
    print("=" * 80)
    print()
    
    # Test with earnings filtering ON
    print("TEST 1: Scanner WITH earnings filtering (default)")
    print("-" * 80)
    scanner = IBScanner(port=7497, check_earnings=True)
    
    if not scanner.connect():
        print("Could not connect to IB")
        return
    
    try:
        opportunities = scanner.scan_ticker('TSLA', threshold=0.2)
        
        print(f"\nFound {len(opportunities)} opportunities after earnings filter")
        
    finally:
        scanner.disconnect()
    
    print("\n" + "=" * 80)
    print("\nTEST 2: Scanner WITHOUT earnings filtering")
    print("-" * 80)
    
    scanner2 = IBScanner(port=7497, check_earnings=False)
    
    if not scanner2.connect():
        return
    
    try:
        opportunities2 = scanner2.scan_ticker('TSLA', threshold=0.2)
        
        print(f"\nFound {len(opportunities2)} opportunities without earnings filter")
        
    finally:
        scanner2.disconnect()
    
    print("\n" + "=" * 80)
    print(f"\nCOMPARISON:")
    print(f"  Without filter: {len(opportunities2)} opportunities")
    print(f"  With filter:    {len(opportunities)} opportunities")
    print(f"  Excluded:       {len(opportunities2) - len(opportunities)} due to earnings")
    print("=" * 80)


if __name__ == "__main__":
    main()
