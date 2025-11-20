# Scanner Performance Optimization Guide

## Speed Improvements Implemented

### 1. Reduced IV Ranking Scope
- **NASDAQ 100**: Now ranks first 50 tickers (down from 104) → **52% faster**
- **MidCap 400**: Now ranks first 150 tickers (down from 400+) → **62% faster**
- Still scans top 30 NASDAQ and top 100 MidCap by IV

### 2. Reduced Sleep Times
- IV data wait time: 1 second (down from 2) → **50% faster per ticker**

### 3. Time Estimates

**Before optimization:**
- NASDAQ 100: ~30-45 minutes (rank all 104, scan top 30)
- MidCap 400: ~60-90 minutes (rank all 400+, scan top 100)
- **Total: 1.5-2 hours**

**After optimization:**
- NASDAQ 100: ~15-20 minutes (rank first 50, scan top 30)
- MidCap 400: ~25-35 minutes (rank first 150, scan top 100)
- **Total: 40-55 minutes** → **60% faster!**

## Further Speed Options

### Option 1: Skip IV Rankings Completely (Fastest)
Edit the scan scripts to set `rank_by_iv=False`:

**In run_nasdaq100_scan.py:**
```python
run_nasdaq100_scan(threshold=0.2, rank_by_iv=False)
```

**In run_midcap400_scan.py:**
```python
run_midcap400_scan(threshold=0.2, rank_by_iv=False)
```

**Effect:** Scans tickers in alphabetical order without IV ranking
**Time:** ~20-30 minutes total (but may miss high IV opportunities)

### Option 2: Reduce Top N Scanned
Scan fewer tickers:

**NASDAQ 100:**
```python
run_nasdaq100_scan(threshold=0.2, rank_by_iv=True, top_n_iv=20, rank_n_iv=40)
```

**MidCap 400:**
```python
run_midcap400_scan(threshold=0.2, rank_by_iv=True, top_n_iv=50, rank_n_iv=100)
```

**Effect:** Rank 40 NASDAQ/100 MidCap, scan top 20/50
**Time:** ~25-35 minutes total

### Option 3: NASDAQ 100 Only
Skip MidCap 400 entirely:

```bash
python daily_run.py --nasdaq100
```

**Time:** ~15-20 minutes

### Option 4: Parallel Processing (Advanced)
Would require code refactoring to rank multiple tickers simultaneously.
**Potential speedup:** 2-3x faster but more complex

## Recommended Settings

**For Daily Production:**
- Current settings (rank 50 NASDAQ, 150 MidCap)
- ~45 minutes total
- Good balance of speed and coverage

**For Quick Check:**
```bash
python daily_run.py --nasdaq100
```
- ~15 minutes
- Just the most liquid names

**For Full Coverage:**
Edit scripts to rank all tickers (slower but comprehensive)

## IB Connection Tips

1. **Use IB Gateway instead of TWS** - lighter weight, faster
2. **Paper trading account** - faster data, no real $ risk
3. **Run during market hours** - fresher data, fewer timeouts
4. **Stable internet** - reduces retry delays

## Current Configuration

Files modified for speed:
- `run_nasdaq100_scan.py` - ranks first 50 (was 104)
- `run_midcap400_scan.py` - ranks first 150 (was 400+)  
- `scanner_ib.py` - 1 sec IV wait (was 2 sec)

These changes are already in effect!
