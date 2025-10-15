# Interactive Brokers Setup Guide

## Quick Start

The IB scanner (`scanner_ib.py`) connects to your Interactive Brokers account to fetch real-time option data with accurate implied volatilities.

## Prerequisites

1. **Interactive Brokers Account** (paper or live)
2. **IB Gateway or TWS (Trader Workstation)** installed
3. **Python packages** installed (already done if you ran requirements.txt)

## Step 1: Enable API Access in IB

### For TWS (Trader Workstation):
1. Open TWS and log in
2. Go to **File** → **Global Configuration** → **API** → **Settings**
3. Check **Enable ActiveX and Socket Clients**
4. Check **Allow connections from localhost only** (for security)
5. Note the **Socket Port** (default: 7497 for paper, 7496 for live)
6. Optional: Uncheck **Read-Only API** if you want to place orders later
7. Click **OK** and restart TWS

### For IB Gateway:
1. Open IB Gateway and log in
2. Click **Configure** → **Settings** → **API** → **Settings**
3. Check **Enable ActiveX and Socket Clients**
4. Check **Allow connections from localhost only**
5. Note the **Socket Port** (default: 4002 for paper, 4001 for live)
6. Click **OK**

## Step 2: Run the Scanner

### Start IB Gateway or TWS
Make sure IB Gateway or TWS is running and logged in before running the scanner.

### Run the Scanner

```bash
python scanner_ib.py
```

### Port Selection
When prompted, enter the appropriate port:
- **7497** - TWS Paper Trading (default)
- **7496** - TWS Live Trading
- **4002** - IB Gateway Paper Trading
- **4001** - IB Gateway Live Trading

## Step 3: Usage

The scanner will:
1. Connect to your IB account
2. Test with TSLA first
3. Fetch real-time option chains
4. Calculate forward volatility for consecutive expirations
5. Report opportunities where Forward Factor > 0.4
6. Save results to CSV

You can then scan additional tickers by entering them when prompted.

## Common Port Configurations

| Platform | Account Type | Port |
|----------|--------------|------|
| TWS      | Paper        | 7497 |
| TWS      | Live         | 7496 |
| Gateway  | Paper        | 4002 |
| Gateway  | Live         | 4001 |

## Troubleshooting

### "Connection refused" Error
- Make sure TWS or IB Gateway is running
- Verify you're logged in
- Check that API is enabled in settings
- Verify the port number is correct

### "No IV data" for options
- May occur for illiquid options or outside market hours
- Scanner will skip these and continue with other expirations
- Try during market hours (9:30 AM - 4:00 PM ET)

### "Not enough expiration dates"
- Stock may have limited options available
- Try more liquid stocks (AAPL, SPY, QQQ)

### Rate Limiting
Interactive Brokers has built-in pacing. The scanner includes appropriate delays.

## Advantages of IB Scanner

✅ **Real-time data** - Live option chains and IVs  
✅ **Accurate IVs** - Calculated by IB's models  
✅ **No rate limits** - Use your own account data  
✅ **Free** - No API subscription needed  
✅ **Reliable** - Direct connection to your broker  
✅ **Historical data** - Can access past data if needed  

## Security Notes

- The scanner only *reads* data (no trading)
- "Read-Only API" mode is sufficient
- Keep "Allow connections from localhost only" checked
- Never share your API credentials

## Next Steps

Once you verify the connection works:
1. Scan your watchlist tickers
2. Set up automated scans
3. Export results for analysis
4. Integrate with your trading workflow

For support, see the main README.md or join the Discord.
