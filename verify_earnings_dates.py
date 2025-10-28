"""
Compare Finnhub earnings dates with known dates
"""
import requests
from datetime import datetime, timedelta

finnhub_api_key = 'd3rcvl1r01qopgh82hs0d3rcvl1r01qopgh82hsg'

# Known earnings dates from reliable sources (MarketBeat, etc.)
known_earnings = {
    'SNPS': '2025-12-03',  # MarketBeat
    'MRVL': '2025-12-02',  # MarketBeat
    'NVDA': '2025-11-19',  # Should verify
    'AMAT': '2025-11-13',  # Verified correct
}

print("=" * 80)
print("EARNINGS DATE COMPARISON - Finnhub vs Known Dates")
print("=" * 80)

for ticker, known_date in known_earnings.items():
    print(f"\n{ticker}:")
    print("-" * 60)
    print(f"Known/Expected: {known_date} ({datetime.strptime(known_date, '%Y-%m-%d').strftime('%A')})")
    
    # Query Finnhub
    from_date = datetime.now().strftime('%Y-%m-%d')
    to_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
    url = f'https://finnhub.io/api/v1/calendar/earnings?from={from_date}&to={to_date}&symbol={ticker}&token={finnhub_api_key}'
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data and 'earningsCalendar' in data and len(data['earningsCalendar']) > 0:
            finnhub_date = data['earningsCalendar'][0].get('date')
            hour = data['earningsCalendar'][0].get('hour', 'N/A')
            
            print(f"Finnhub:        {finnhub_date} ({datetime.strptime(finnhub_date, '%Y-%m-%d').strftime('%A')}) {hour}")
            
            # Calculate difference
            known_dt = datetime.strptime(known_date, '%Y-%m-%d')
            finnhub_dt = datetime.strptime(finnhub_date, '%Y-%m-%d')
            diff_days = (known_dt - finnhub_dt).days
            
            if diff_days == 0:
                print("✅ MATCH")
            else:
                print(f"⚠️  MISMATCH: {diff_days} day(s) difference")
        else:
            print("Finnhub:        No data")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 80)
print("ANALYSIS:")
print("If Finnhub consistently shows 1 day earlier, it may be a timezone issue")
print("or difference in how 'after market close' dates are reported.")
print("=" * 80)
