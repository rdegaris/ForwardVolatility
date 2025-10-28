# Setting Up Finnhub API for Earnings Dates

## Why Finnhub?
Finnhub provides real-time earnings calendar data through their free API tier, which is more reliable than manual calendar maintenance.

## Setup Steps

### 1. Get Your API Key
1. Visit https://finnhub.io/register
2. Create a free account
3. Copy your API key from the dashboard

### 2. Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:FINNHUB_API_KEY='your_api_key_here'
```

**Windows (Command Prompt):**
```cmd
set FINNHUB_API_KEY=your_api_key_here
```

**Mac/Linux:**
```bash
export FINNHUB_API_KEY='your_api_key_here'
```

### 3. Test the Connection
```bash
python test_finnhub.py
```

You should see earnings dates for MAG7 stocks fetched from Finnhub.

### 4. Run Your Scans
The scanners will now automatically use Finnhub API for earnings dates:
```bash
python run_mag7_scan.py
python run_nasdaq100_scan.py 0.2
```

## How It Works

The `earnings_checker.py` now follows this priority:

1. **Finnhub API** (if FINNHUB_API_KEY is set) - Real-time data
2. **Manual Calendar** (earnings_calendar.py) - Fallback if API fails

This means:
- ✅ Always get the latest earnings dates
- ✅ No need to manually update the calendar every quarter
- ✅ Falls back to manual calendar if API is unavailable

## API Rate Limits

Free Finnhub tier includes:
- 60 API calls per minute
- Unlimited requests per day

This is more than enough for scanning ~100 stocks.

## Troubleshooting

**"FINNHUB_API_KEY not set" warning?**
- Make sure you've set the environment variable in your current terminal session
- The variable needs to be set each time you open a new terminal

**No earnings data found?**
- Check that your API key is valid at https://finnhub.io/dashboard
- Verify you're using a valid stock ticker symbol
- Some stocks may not have earnings dates published yet

**Still want to use manual calendar?**
- Simply don't set the FINNHUB_API_KEY environment variable
- The system will automatically use the manual calendar from earnings_calendar.py
