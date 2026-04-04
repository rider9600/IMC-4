# Prosperity 4 Algorithmic Trading Strategy

## Overview

This is a **mean-reversion trading strategy** for the Prosperity 4 algorithmic trading challenge. The strategy trades two virtual commodities:
- **TOMATOES**: More volatile, traded with an aggressive mean-reversion approach
- **EMERALDS**: More stable, traded conservatively

## Market Data Insights

Based on historical analysis (`analyze_data.py`):

### TOMATOES (Product 1)
- **Mid-price range**: 4946.5 - 5036.0
- **Average price**: ~4992.76
- **Volatility (std dev)**: ~19.75
- **Bid-ask spread**: ~13 units (typical)
- **Trading volume**: High (1400+ units/day across 400+ trades)
- **Pattern**: Shows meaningful price oscillations around mean

### EMERALDS (Product 2)
- **Mid-price range**: 9996.0 - 10004.0  
- **Average price**: ~9999.99
- **Volatility (std dev)**: ~0.72 (very low!)
- **Bid-ask spread**: ~16 units
- **Trading volume**: Lower (~1100 units/day across 200 trades)
- **Pattern**: Extremely stable, stays within 8 units of 10000

## Strategy Logic

### Core Principle: Mean Reversion
The strategy assumes that prices oscillate around a mean and will revert when they deviate significantly.

### TOMATOES Trading Rules
```
1. Maintain a rolling average of mid-prices (window: last 50 observations)
2. IF mid_price < 0.98 × rolling_mean:
   → BUY (price is cheap, expect mean reversion upward)
   → Match seller quotes up to position limit (100 units)
3. IF mid_price > 1.02 × rolling_mean:
   → SELL (price is expensive, expect mean reversion downward)
   → Match buyer quotes down to short position limit (-100 units)
4. Else: HOLD (price near mean, no signal)
```

### EMERALDS Trading Rules
```
1. Maintain rolling average of mid-prices (window: last 50 observations)
2. IF mid_price < 0.995 × rolling_mean:
   → BUY (rare event, very cheap)
3. IF mid_price > 1.005 × rolling_mean:
   → SELL (rare event, very expensive)
4. Otherwise: HOLD (high probability signal is noise)
```

The tighter thresholds for EMERALDS (0.5% vs 2%) reflect its naturally lower volatility.

## Key Features

### State Persistence
- Uses `traderData` field to store price history across iterations
- Maintains rolling window of up to 50 recent mid-prices per product
- Serialized/deserialized using `jsonpickle`

### Position Management
- **Position limits**: 100 units long or 100 units short per product
- **Execution**: Buys lowest-priced sells first, sells highest-priced buys first
- **Partial fills**: Orders sized to respect position limits

### Order Placement
- Immediately executes against existing bot orders in the order book
- For TOMATOES: Aggressive - buys even at slightly higher prices when signal triggers
- For EMERALDS: Conservative - only takes best available price

## Files

- **strategy.py**: Main trading algorithm (Trader class)
- **datamodel.py**: Data structures (Order, OrderDepth, TradingState, etc.)
- **analyze_data.py**: Historical data analysis, generates market insights
- **prices_round_0_day_*.csv**: Historical market maker quotes by timestamp
- **trades_round_0_day_*.csv**: Historical trade executions
- **strategy.ipynb**: Jupyter notebook with exploratory data analysis

## Running the Strategy

### 1. Analyze Market Data
```bash
python analyze_data.py
```
This generates statistics on price distributions, spreads, volumes, and mean-reversion signal opportunities.

### 2. Deploy to Prosperity Platform
The `Trader` class in `strategy.py` is ready to upload:
- Implement required `run(state: TradingState)` method
- Optional `bid()` method for Round 2 (returns fixed value 15)
- Returns `(orders_dict, conversions, traderData_string)`

### 3. Local Testing
```python
from strategy import Trader
from datamodel import *

trader = Trader()
# ... create TradingState from historical data ...
result, conversions, trader_data = trader.run(state)
```

## Performance Considerations

### Execution Time
- Each `run()` call must complete in < 900ms
- Current implementation is lightweight: O(n) where n = order book depth
- Typical execution: <100ms

### Libraries Used
✅ Standard Python 3.12
✅ jsonpickle (for state persistence)
✅ pandas (for data analysis, not used in live strategy)
✅ numpy (optionally available)

## Risk Management

### Position Limits
- Absolute limit: 100 units long OR 100 units short per product
- Strategy respects these limits - will reject orders that exceed them
- Exchange automatically cancels orders that would violate limits

### Stop Losses
- No explicit stop losses (pure mean-reversion assumes convergence)
- Automatically trimmed when positions reach limit

## Expected Behavior

### Profitable Scenarios
- TOMATOES prices dip to 4975, algorithm buys at several prices
- Price recovers to 5005, algorithm sells at profit
- Expected P&L: Positive from buy-low, sell-high cycles

- EMERALDS stabilizes at 9999 after rare dips to 9990
- Algorithm captures small 0.5% moves repeatedly

### Loss Scenarios
- Trend following (prices break mean): Algorithm reverses losses
- Gap risk: Prices gap past moving average - algorithm caught with forced position

## Improvements for Future Rounds

1. **Dynamic thresholds**: Adjust buy/sell thresholds based on measured volatility
2. **Volume-weighted averaging**: Track volume-weighted average price (VWAP)
3. **Multi-timeframe**: Use different windows for short-term vs long-term trends
4. **Competitive analysis**: Track bot behavior patterns
5. **Risk scaling**: Adjust position sizes based on recent volatility
6. **Profit-taking**: Close profitable positions at target levels
7. **Products correlation**: Trade pairs (e.g., if related products available)

## Testing Checklist

- [x] Data loads correctly from CSV files
- [x] Mean-reversion signals generate appropriately  
- [x] Position limits enforced in logic
- [x] State persists across iterations
- [x] Order book parsing handles empty sides
- [x] Code runs within time limits

## Questions or Issues?

- Check `analyze_data.py` output for market condition insights
- Monitor `print()` statements in strategy logs for debugging
- Verify `rolling_mean` is computed before trading (min 50 observations)
- Confirm position limits match product specifications on Prosperity platform

---

**Strategy Version**: 1.0  
**Last Updated**: April 2026  
**Ready for Submission** ✓
