# TRADE TICKET - PUT CALENDAR SPREAD

## TSLA $435 PUT CALENDAR SPREAD - October 2025

---

### ENTRY ORDERS (Open Position)

**DATE:** October 15, 2025  
**STRATEGY:** Calendar Spread (Time Spread)  
**UNDERLYING:** TSLA @ $435.61  
**CONTRACT SIZE:** 1 contract (100 shares)

---

#### LEG 1: BUY BACK MONTH
```
Action:      BUY TO OPEN
Quantity:    1 contract
Symbol:      TSLA
Expiration:  October 31, 2025 (15 DTE)
Strike:      $435.00
Option Type: PUT
Order Type:  LIMIT
Limit Price: $22.75 (or better - willing to pay up to $23.00)
TIF:         DAY
```

#### LEG 2: SELL FRONT MONTH
```
Action:      SELL TO OPEN
Quantity:    1 contract
Symbol:      TSLA
Expiration:  October 24, 2025 (8 DTE)
Strike:      $435.00
Option Type: PUT
Order Type:  LIMIT
Limit Price: $18.80 (or better - willing to accept down to $18.50)
TIF:         DAY
```

---

### NET POSITION
```
Net Debit Target:  $3.95 per share ($395 total)
Max Acceptable:    $4.00 per share ($400 total)
Net Greeks:        Long Vega, Short Theta (initially)
```

---

### IB TWS ENTRY STEPS

1. **Right-click TSLA** → Option Chain
2. Select **$435 Strike** row
3. Click **October 24 PUT** → Select **"Buy Calendar"** or **"Spread"**
4. In spread builder:
   - **Sell:** Oct 24 $435 PUT (1 contract)
   - **Buy:** Oct 31 $435 PUT (1 contract)
5. Set **Order Type:** LIMIT
6. Set **Net Debit:** $3.95 (adjust to $4.00 if no fill)
7. **Review:**
   - Cost: ~$395 (plus commissions)
   - Margin required: Check with IB (usually ~$400-500)
8. **Submit Order**

---

### EXIT PLAN

**TARGET EXIT DATE:** October 24, 2025 at 3:45 PM ET (15 min before close)

#### EXIT ORDERS (Close Position)

**LEG 1: SELL BACK MONTH**
```
Action:      SELL TO CLOSE
Quantity:    1 contract
Symbol:      TSLA
Expiration:  October 31, 2025
Strike:      $435.00
Option Type: PUT
Order Type:  MARKET or LIMIT (at profit target)
```

**LEG 2: BUY FRONT MONTH**
```
Action:      BUY TO CLOSE
Quantity:    1 contract
Symbol:      TSLA
Expiration:  October 24, 2025
Strike:      $435.00
Option Type: PUT
Order Type:  MARKET or LIMIT (at profit target)
```

---

### PROFIT/LOSS TARGETS

```
Entry Cost:           $395
Target Profit:        $158 (40% gain) - Exit at $553 net credit
Acceptable Profit:    $79 (20% gain) - Exit at $474 net credit
Stop Loss:            $119 (30% loss) - Exit at $276 net credit
Max Loss:             $395 (100% loss) - Don't let this happen!
```

#### Exit Triggers:
- ✅ **Take Profit:** Stock at $430-$440 on Oct 24 → Close for profit
- ⚠️ **Stop Loss:** Stock moves >4% (below $418 or above $453) → Close immediately
- 🕐 **Time Exit:** Oct 24 at 3:45 PM → Close regardless of P&L

---

### RISK MANAGEMENT CHECKLIST

- [ ] Verified account has $400+ available (for margin)
- [ ] Set calendar reminder for Oct 24, 3:30 PM
- [ ] Confirmed both legs filled at acceptable prices
- [ ] Position size: Only 1 contract (manageable risk)
- [ ] Stop loss plan: Exit if stock moves >4%
- [ ] Not holding through Oct 24 expiration
- [ ] Understand max loss: $395

---

### TRADE RATIONALE

**Forward Factor:** 0.281 (28.1%) - PUT spread  
**Front IV:** 71.05% (Oct 24)  
**Back IV:** 64.25% (Oct 31)  

**Thesis:** Front month IV is elevated relative to back month. Expecting front month IV to decay faster than back month, capturing the volatility differential.

---

### NOTES & JOURNAL

**Pre-Trade:**
- Scanner found FF = 0.281 for PUT spread
- TSLA price stable around $435
- Market conditions: [Add notes]

**Post-Entry:**
- Entry Date: ___________
- Actual Fill: $_______ net debit
- Entry Stock Price: $_______

**During Trade:**
- [Monitor daily - update notes]

**Post-Exit:**
- Exit Date: ___________
- Actual Exit: $_______ net credit
- Exit Stock Price: $_______
- **Final P&L: $_______**
- **Return: _______%**
- Lessons learned: [Add notes]

---

### COMMISSIONS (Estimate)

IB Options Commissions: ~$0.65 per contract
- Entry: $0.65 × 2 legs = **$1.30**
- Exit: $0.65 × 2 legs = **$1.30**
- **Total Commissions: ~$2.60**

**Net Investment: $395 + $2.60 = $397.60**

---

### EMERGENCY CONTACTS

- IB Customer Service: 877-442-2757
- Trading Desk: Available 24/5

---

**DISCLAIMER:** This is a trading template for record-keeping purposes only. Not investment advice.
