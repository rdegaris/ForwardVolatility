"""
Quick test script to verify yfinance API is working
"""
import yfinance as yf

print("Testing yfinance API connection...")
print("-" * 50)

try:
    # Test basic ticker data
    print("\n1. Testing basic ticker info for AAPL...")
    aapl = yf.Ticker("AAPL")
    
    # Try fast_info first
    try:
        price = aapl.fast_info.get('lastPrice')
        print(f"   Price (fast_info): ${price}")
    except Exception as e:
        print(f"   fast_info failed: {e}")
        price = aapl.info.get('currentPrice') or aapl.info.get('regularMarketPrice')
        print(f"   Price (info): ${price}")
    
    # Test options availability
    print("\n2. Testing options data...")
    options = aapl.options
    print(f"   Available expiries: {len(options)}")
    if len(options) > 0:
        print(f"   First expiry: {options[0]}")
        print(f"   Last expiry: {options[-1]}")
        
        # Test option chain for first expiry
        print(f"\n3. Testing option chain for {options[0]}...")
        chain = aapl.option_chain(options[0])
        print(f"   Calls: {len(chain.calls)} rows")
        print(f"   Puts: {len(chain.puts)} rows")
        
        if not chain.calls.empty:
            print(f"\n4. Sample call option data:")
            sample = chain.calls.iloc[0]
            print(f"   Strike: {sample['strike']}")
            print(f"   Last Price: {sample.get('lastPrice', 'N/A')}")
            print(f"   IV: {sample.get('impliedVolatility', 'N/A')}")
    
    print("\n" + "=" * 50)
    print("✓ API test completed successfully!")
    print("=" * 50)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
