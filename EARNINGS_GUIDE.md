# Earnings Calendar Maintenance Guide

## Overview
The scanner now uses a **manually maintained earnings calendar** (`earnings_calendar.py`) to filter out trades with earnings before the front month expiry. This ensures reliable, accurate earnings filtering without depending on unreliable external APIs.

## Strict Filtering Rule
**ANY trade where earnings occurs BEFORE the front expiry date is EXCLUDED.**
- No buffer zones
- No tolerance
- If earnings is Oct 23 and front expiry is Oct 24, the trade is EXCLUDED
- Earnings filtering runs FIRST before any other analysis

## How to Update Earnings Dates

### 1. Open the earnings calendar file:
```
earnings_calendar.py
```

### 2. Update the dates in this format:
```python
EARNINGS_CALENDAR = {
    'TICKER': 'YYYY-MM-DD',   # Company - Quarter/Year
    ...
}
```

### 3. Sources for Earnings Dates:
- **Company Investor Relations pages** (most reliable)
- **Nasdaq Earnings Calendar**: https://www.nasdaq.com/market-activity/earnings
- **Yahoo Finance**: Search ticker → "Analysis" tab → "Earnings Date"
- **Company press releases**

### 4. Update Frequency:
- **Quarterly**: Update all MAG7 tickers after each earnings season
- **Before each scan**: Verify dates for tickers you're actively trading
- **When notified**: The scanner will warn if a date has passed

## Current MAG7 Earnings Schedule (Q3/Q4 2024)
```
AAPL:  2025-10-31  (Apple - Q4 2024)
MSFT:  2025-10-23  (Microsoft - Q1 2025)
GOOGL: 2025-10-29  (Alphabet - Q3 2024)
AMZN:  2025-10-31  (Amazon - Q3 2024)
NVDA:  2025-11-20  (NVIDIA - Q3 FY2025)
META:  2025-10-30  (Meta Platforms - Q3 2024)
TSLA:  2025-10-23  (Tesla - Q3 2024)
```

## Typical Earnings Schedule Patterns

### Tech companies (AAPL, MSFT, GOOGL, AMZN, META):
- **Q1 (Jan-Mar)**: Reports late April/early May
- **Q2 (Apr-Jun)**: Reports late July/early August  
- **Q3 (Jul-Sep)**: Reports late October/early November
- **Q4 (Oct-Dec)**: Reports late January/early February

### NVIDIA (fiscal year Feb-Jan):
- **Q1 FY (Feb-Apr)**: Reports late May
- **Q2 FY (May-Jul)**: Reports late August
- **Q3 FY (Aug-Oct)**: Reports late November
- **Q4 FY (Nov-Jan)**: Reports late February

### Tesla:
- Usually reports about 3 weeks after quarter end

## Warning Messages

### Date Has Passed:
```
⚠️  WARNING: AAPL earnings date 2025-10-31 has passed - update earnings_calendar.py!
```
**Action**: Update the ticker's earnings date to the next quarter

### Invalid Date Format:
```
⚠️  ERROR: Invalid date format for AAPL in earnings_calendar.py
```
**Action**: Fix the date format to YYYY-MM-DD

## Example Scan Output

When earnings filtering is working:
```
[2/7] MSFT...
  Found 3 opportunity(ies)

  Checking for earnings before front expiry...
  ⚠️  EXCLUDED MSFT: Earnings on 2025-10-23 (before front expiry 2025-10-31)
  ⚠️  EXCLUDED MSFT: Earnings on 2025-10-23 (before front expiry 2025-11-07)
  ⚠️  EXCLUDED MSFT: Earnings on 2025-10-23 (before front expiry 2025-11-14)

🚫 Excluded 3 ticker(s) due to earnings before front expiry: MSFT
  No opportunities
```

This shows the scanner:
1. Found 3 opportunities with good forward volatility
2. Checked earnings dates
3. Excluded ALL 3 because MSFT earnings (Oct 23) is before each front expiry

## Benefits of Manual Calendar

✅ **Reliable**: No API downtime or rate limits
✅ **Accurate**: You control the data source
✅ **Fast**: No network calls during scan
✅ **Transparent**: Easy to verify and audit dates
✅ **Simple**: Just update a Python dictionary

## Adding New Tickers

When scanning NASDAQ 100 or other lists:

1. Add the ticker to `earnings_calendar.py`:
```python
EARNINGS_CALENDAR = {
    # MAG7
    'AAPL': '2025-10-31',
    ...
    
    # Additional tickers
    'NFLX': '2025-10-19',  # Netflix - Q3 2024
    'CRM': '2025-11-30',   # Salesforce - Q3 FY2025
}
```

2. Run the scan - it will automatically use the earnings date

3. If a ticker is NOT in the calendar, the scanner will:
   - NOT exclude it (assume safe)
   - Still run forward volatility calculations
   - Include it in results if FF threshold is met

## Testing the Earnings Checker

Run the standalone test:
```bash
python earnings_checker.py
```

Output shows:
- All earnings dates in the calendar
- Which tickers would be excluded for a sample front expiry date

## Questions?

- Check if date has passed: Scanner will warn you
- Unsure about a date: Look it up on Nasdaq calendar before scanning
- Missing a ticker: Add it to earnings_calendar.py before scanning

**Remember**: Better to be safe and exclude a trade than risk trading through earnings!
