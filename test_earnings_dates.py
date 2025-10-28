"""
Test script to verify earnings dates from Finnhub API
"""
import requests
from datetime import datetime, timedelta
import os

# API key
finnhub_api_key = os.environ.get('FINNHUB_API_KEY', 'd3rcvl1r01qopgh82hs0d3rcvl1r01qopgh82hsg')

# Test tickers with known earnings dates
test_tickers = ['NVDA', 'PYPL', 'CEG', 'RIVN', 'CCEP', 'CTSH', 'PDD']

print("=" * 80)
print("EARNINGS DATE VERIFICATION TEST")
print("=" * 80)
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")
print()

for ticker in test_tickers:
    print(f"\n{ticker}:")
    print("-" * 40)
    
    # Get earnings calendar for next 60 days
    from_date = datetime.now().strftime('%Y-%m-%d')
    to_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
    
    url = f"https://finnhub.io/api/v1/calendar/earnings?from={from_date}&to={to_date}&symbol={ticker}&token={finnhub_api_key}"
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data and 'earningsCalendar' in data:
                if len(data['earningsCalendar']) > 0:
                    print(f"  Found {len(data['earningsCalendar'])} earnings entries")
                    
                    # Show all entries
                    for i, entry in enumerate(data['earningsCalendar']):
                        date_str = entry.get('date')
                        hour = entry.get('hour', 'N/A')
                        quarter = entry.get('quarter', 'N/A')
                        year = entry.get('year', 'N/A')
                        
                        print(f"  Entry {i+1}:")
                        print(f"    Date: {date_str}")
                        print(f"    Hour: {hour}")
                        print(f"    Quarter: {quarter}")
                        print(f"    Year: {year}")
                        
                        # Parse and show day of week
                        if date_str:
                            try:
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                                day_name = dt.strftime('%A, %B %d, %Y')
                                print(f"    Day: {day_name}")
                            except:
                                pass
                else:
                    print("  No earnings data available")
            else:
                print("  No earnings calendar in response")
                print(f"  Response: {data}")
        else:
            print(f"  API Error: Status {response.status_code}")
            
    except Exception as e:
        print(f"  Exception: {e}")

print("\n" + "=" * 80)
