# Troubleshooting Guide

## Yahoo Finance API Issues

If you encounter errors like:
- `429 Too Many Requests`
- `No price data found, symbol may be delisted`
- `Could not fetch options data`

### Causes:
1. **Rate Limiting**: Yahoo Finance limits requests from each IP address
2. **Temporary Blocks**: Making too many requests in a short time
3. **Network Issues**: Firewall, VPN, or connection problems
4. **API Downtime**: Yahoo Finance API may be temporarily unavailable

### Solutions:

#### 1. Wait and Retry
The simplest solution is to wait 5-10 minutes before trying again. Rate limits typically reset after a short period.

#### 2. Use a VPN or Different Network
If you're consistently blocked, try:
- Switching to a different network
- Using a VPN
- Running from a different location/IP

#### 3. Reduce Scan Frequency
- Scan fewer stocks at a time
- Increase delays in the code (already implemented)
- Focus on specific tickers instead of full Nasdaq 100

#### 4. Alternative Data Sources
Consider using:
- **CBOE DataShop** (paid)
- **Interactive Brokers API** (requires account)
- **TD Ameritrade API** (free with account)
- **Polygon.io** (freemium)
- **Alpha Vantage** (freemium)

### Modifying Rate Limits

Edit `scanner.py` to increase delays:

```python
# Line ~173 - delay between tickers
time.sleep(1.0)  # Increase to 2.0 or 3.0

# Line ~220 - delay between option chains
time.sleep(0.3)  # Increase to 0.5 or 1.0

# Line ~146 - initial delay
time.sleep(0.5)  # Increase to 1.0
```

### Testing API Availability

Run the test script:
```bash
python test_api.py
```

If this fails, wait before trying the scanner.

### Alternative: Manual Mode

Use the GUI calculator (`calculator.py`) with manually entered IV values from:
- Your broker's option chain
- CBOE quotes
- Financial terminals (Bloomberg, Reuters)

The GUI calculator works offline and doesn't require any API calls.

## Common Error Messages

### "Could not fetch current price"
- Stock may not have recent trading data
- API rate limit reached
- Wait and retry

### "Not enough expiry dates available"
- Stock may have limited options trading
- Try a more liquid stock (AAPL, SPY, QQQ)
- Check if options exist for this ticker

### "No opportunities above threshold"
- Normal result if volatility term structure is flat
- Try lowering threshold (e.g., 0.3 instead of 0.4)
- Try different stocks or wait for market conditions to change

## Recommended Testing

Start with highly liquid, popular tickers that definitely have options:
- SPY (S&P 500 ETF)
- QQQ (Nasdaq ETF)
- AAPL, MSFT, TSLA

These should work if the API is available.
