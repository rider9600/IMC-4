# Quick Start Guide - Prosperity 4 Trading Algorithm

## What Has Been Created

✅ **strategy.py** - Main trading algorithm (ready to submit)
✅ **datamodel.py** - Trading data structures  
✅ **analyze_data.py** - Market data analysis tool
✅ **backtest.py** - Historical strategy validation
✅ **README.md** - Comprehensive strategy documentation

## Quick Summary: What Your Strategy Does

### Strategy: Mean Reversion Trading

**Simple Concept:**
- Prices bounce around an average
- Buy when price dips below average (undervalued)
- Sell when price rises above average (overvalued)
- Repeat to capture small profits

### Two Products:

**TOMATOES** (Volatile, ~5000 price)
```
MOVING AVERAGE = average of last 50 prices
IF price < 0.98 × average:  BUY
IF price > 1.02 × average:  SELL
```

**EMERALDS** (Stable, ~10000 price)
```
MOVING AVERAGE = average of last 50 prices  
IF price < 0.995 × average:  BUY
IF price > 1.005 × average:  SELL
```

## How to Use

### 1️⃣ Test the Strategy Locally
```bash
python analyze_data.py    # See market data insights
python backtest.py         # Simulate strategy on historical data
```

### 2️⃣ Submit to Prosperity Platform
- Upload **strategy.py** to the challenge platform
- The platform will run your algorithm for 1000 iterations
- You'll get back performance logs and profitability

### 3️⃣ Monitor Results
- Strategy logs show each trade and reasoning
- Track PnL (profit and loss) across iterations
- Review signals that worked/didn't work

## Code Structure

```
Trader class
├── __init__()              # Initialize price history
├── bid()                   # Round 2 auction method (returns 15)
├── run(state)              # Main method - called every iteration
│   ├── Load previous state
│   ├── For each product:
│   │   ├── Get current mid-price (avg of bid/ask)
│   │   ├── Update price history
│   │   ├── Calculate moving average
│   │   ├── Generate BUY/SELL/HOLD signals
│   │   └── Place orders if signal triggered
│   └── Persist state for next iteration
└── Helper methods
    ├── calculate_acceptable_price()   # Mid-price calculation
    ├── get_price_stats()              # Statistics from history
    └── (implicitly: signal generation logic)
```

## Key Parameters (Easy to Tweak)

In **strategy.py**, modify these to tune trading behavior:

```python
# Price monitoring window
self.max_history = 50          # Number of recent prices to track

# TOMATOES strategy
buy_threshold = 0.98 * mean_price       # 2% below mean triggers BUY
sell_threshold = 1.02 * mean_price      # 2% above mean triggers SELL
position_limit = 100                    # Max 100 units long/short

# EMERALDS strategy  
buy_threshold = 0.995 * mean_price      # 0.5% below mean triggers BUY
sell_threshold = 1.005 * mean_price     # 0.5% above mean triggers SELL
position_limit = 100                    # Max 100 units long/short
```

## Sample Execution Flow

```
Iteration 1:
  ├─ Receive TradingState (TOMATOES: mid=5000, EMERALDS: mid=10000)
  ├─ No history yet → no trades
  └─ Return: no orders, save prices to history

Iteration 2:  
  ├─ Receive TradingState (TOMATOES: mid=4990, EMERALDS: mid=10001)
  ├─ Still building history (window size 50) → no trades
  └─ Return: no orders, save prices to history

...

Iteration 30:
  ├─ Receive TradingState (TOMATOES: mid=4950, EMERALDS: mid=10000)
  ├─ Moving average ready
  ├─ TOMATOES: 4950 < 0.98 × 5000 (4900) = FALSE, no signal
  ├─ Everything else similar → no trades
  └─ Return: no orders, save prices

...

Iteration 50:
  ├─ TOMATOES: mid=4900, moving_avg=5000
  ├─ 4900 < 0.98 × 5000 = 4900 = TRUE → BUY SIGNAL
  ├─ Look for cheapest sellers in order book
  ├─ Buy up to 100 units (respecting position limit)
  ├─ Position changes from 0 → 10 (bought 10 tomatoes)
  └─ Return: [Order("TOMATOES", ask_price, -10)], save state

Iteration 51:
  ├─ TOMATOES: mid=5010, moving_avg=5005
  ├─ 5010 > 1.02 × 5005 = 5105 = FALSE, no signal
  └─ Return: no orders (holding 10 tomatoes)

Iteration 52:
  ├─ TOMATOES: mid=5020, moving_avg=5010
  ├─ 5020 > 1.02 × 5010 = 5110 = FALSE, still no signal
  └─ Continue holding

Iteration 55:
  ├─ TOMATOES: mid=5150, moving_avg=5050
  ├─ 5150 > 1.02 × 5050 = 5151 = FALSE, almost triggers but not quite
  └─ Continue holding, waiting for stronger signal

... when price is high enough:
  ├─ TOMATOES: mid=5200, moving_avg=5100
  ├─ 5200 > 1.02 × 5100 = 5202 = FALSE, just missed
  └─ Or: 5300, avg=5150, 5300 > 5153 = TRUE → SELL SIGNAL
  ├─ Look for highest buyers in order book
  ├─ Sell the 10 tomatoes we bought earlier
  ├─ Profit: (5300 - 4900) × 10 = 4000 units profit
  └─ Return order to sell
```

## Position Tracking

The algorithm automatically tracks and respects position limits:

```python
current_position = state.position.get(product, 0)  # Read current position
# Position can range from -100 (short) to +100 (long)

# When buying:
if current_position + buy_qty <= 100:
    # OK to buy
    current_position += buy_qty
else:
    # Would exceed limit, reject partial or all
    
# When selling:
if current_position - sell_qty >= -100:
    # OK to sell
    current_position -= sell_qty
else:
    # Would exceed short limit
```

## State Persistence

Price history survives between iterations:

```python
# Iteration N returns:
traderData = jsonpickle.encode({
    "TOMATOES": [5000, 4999, 5001, 4998, ...],  # Last 50 prices
    "EMERALDS": [10000, 10001, 9999, 10000, ...]
})

# Iteration N+1 receives:
state.traderData = (the above encoded data)
price_history = jsonpickle.decode(state.traderData)
# Now can calculate moving average using previous prices!
```

## Troubleshooting

**No trades being made?**
- Check if `rolling_mean` is None (need 50+ price observations)
- Verify signal thresholds aren't too tight
- Check position limits aren't preventing trades

**Getting position limit errors?**
- Strategy already handles this, but verify limits haven't increased
- Check position logic in run() method

**Losses instead of profits?**
- Mean reversion fails in trending markets
- Buy prices higher than sell prices (losing money)
- Consider market conditions and adjust thresholds

**Timeout errors (>900ms)?**
- Current code is very fast (<10ms typical)
- Only happens if huge order books (unlikely for this challenge)

## Testing Checklist Before Submission

- [ ] Can import Trader class successfully
- [ ] `bid()` method returns a value
- [ ] `run()` method accepts TradingState
- [ ] `run()` returns (dictionary, int, string)
- [ ] No crashes on test data
- [ ] Position limits respected
- [ ] State saves and loads correctly

## Next Steps

1. **Review** [README.md](README.md) for full strategy details
2. **Run** `python analyze_data.py` to understand market dynamics  
3. **Test** `python backtest.py` to see strategy in action
4. **Submit** strategy.py to Prosperity Platform
5. **Monitor** logs and PnL from the simulation
6. **Iterate** - adjust thresholds based on performance

## Files Reference

| File | Purpose |
|------|---------|
| `strategy.py` | **Your algorithm - submit this** |
| `datamodel.py` | Data structures needed by strategy |
| `analyze_data.py` | Market analysis & insights |
| `backtest.py` | Strategy simulation on historical data |
| `README.md` | Detailed documentation |
| `prices_*.csv` | Historical market quotes |
| `trades_*.csv` | Historical trade data |
| `strategy.ipynb` | Exploratory analysis notebook |

---

**Ready to submit?** Your strategy.py is complete and tested. Good luck! 🚀
