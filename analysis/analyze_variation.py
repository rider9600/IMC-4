"""
Analyze the actual price variation in CSV data
Shows why strategy made 0 trades and how to fix it
"""

import pandas as pd
import statistics
from pathlib import Path

# Read data files
data_path = Path(__file__).resolve().parent.parent / "data"
prices = pd.read_csv(data_path / "prices_round_0_day_-1.csv", sep=";")
trades = pd.read_csv(data_path / "trades_round_0_day_-1.csv", sep=";")

print("=" * 80)
print("📊 DATA ANALYSIS - Understanding Market Variation")
print("=" * 80)

# PRICES ANALYSIS
print("\n📈 PRICES DATA (Order Book Mid-Prices):")
print("-" * 80)

for product in ["TOMATOES", "EMERALDS"]:
    prod_prices = prices[prices["product"] == product]["mid_price"].values

    print(f"\n{product}:")
    print(f"  Minimum: {prod_prices.min():.2f}")
    print(f"  Maximum: {prod_prices.max():.2f}")
    print(f"  Mean: {prod_prices.mean():.2f}")
    print(f"  Std Dev: {statistics.stdev(prod_prices):.2f}")
    print(f"  Range (max - min): {prod_prices.max() - prod_prices.min():.2f}")
    print(
        f"  % Variation: {((prod_prices.max() - prod_prices.min()) / prod_prices.mean() * 100):.2f}%"
    )

# TRADES ANALYSIS
print("\n" + "=" * 80)
print("🔄 TRADES DATA (Executed Market Trades):")
print("-" * 80)

for product in ["TOMATOES", "EMERALDS"]:
    prod_trades = trades[trades["symbol"] == product]["price"].values

    if len(prod_trades) > 0:
        print(f"\n{product}:")
        print(f"  Number of trades: {len(prod_trades)}")
        print(f"  Min trade price: {prod_trades.min():.2f}")
        print(f"  Max trade price: {prod_trades.max():.2f}")
        print(f"  Mean trade price: {prod_trades.mean():.2f}")
        print(f"  Trade range: {prod_trades.max() - prod_trades.min():.2f}")
        print(
            f"  % Trade variation: {((prod_trades.max() - prod_trades.min()) / prod_trades.mean() * 100):.2f}%"
        )

# CRITICAL ANALYSIS
print("\n" + "=" * 80)
print("🎯 WHY DID YOUR STRATEGY MAKE 0 TRADES?")
print("=" * 80)

tom_prices = prices[prices["product"] == "TOMATOES"]["mid_price"].values
tom_mean = tom_prices.mean()
tom_std = statistics.stdev(tom_prices)

print(f"\nTOMATOES Analysis:")
print(f"  Mean price: {tom_mean:.2f}")
print(f"  Std deviation: {tom_std:.2f}")

print(f"\nYour Current Strategy Thresholds:")
print(f"  Buy threshold:  {0.98 * tom_mean:.2f} (when price < this)")
print(f"  Sell threshold: {1.02 * tom_mean:.2f} (when price > this)")

print(f"\nActual Market Prices:")
print(f"  Lowest:  {tom_prices.min():.2f}")
print(f"  Highest: {tom_prices.max():.2f}")

# Check if signals would trigger
buy_triggered = tom_prices.min() < 0.98 * tom_mean
sell_triggered = tom_prices.max() > 1.02 * tom_mean

print(f"\nSignal Analysis:")
print(
    f"  BUY signal triggered?  {'✓ YES' if buy_triggered else '✗ NO - prices never dropped to ' + str(0.98 * tom_mean)}"
)
print(
    f"  SELL signal triggered? {'✓ YES' if sell_triggered else '✗ NO - prices never rose to ' + str(1.02 * tom_mean)}"
)

if not buy_triggered and not sell_triggered:
    print(f"\n🔴 PROBLEM: Market stayed within ±2% of mean")
    print(f"   Price range: {tom_prices.min():.2f} to {tom_prices.max():.2f}")
    print(f"   Your thresholds: {0.98 * tom_mean:.2f} to {1.02 * tom_mean:.2f}")
    print(
        f"   Actual variation: ±{((tom_prices.max() - tom_mean) / tom_mean * 100):.2f}%"
    )

# RECOMMENDATIONS
print("\n" + "=" * 80)
print("✅ HOW TO FIX IT - Choose One Option:")
print("=" * 80)

print(f"\nOPTION 1: Use TIGHTER thresholds (1.5% instead of 2%)")
print(f"  Current: Buy < {0.98 * tom_mean:.2f}, Sell > {1.02 * tom_mean:.2f}")
print(f"  New:     Buy < {0.985 * tom_mean:.2f}, Sell > {1.015 * tom_mean:.2f}")
option_1_works = not (
    tom_prices.min() >= 0.985 * tom_mean and tom_prices.max() <= 1.015 * tom_mean
)
print(
    f"  Status: {"✗ Still won't work (prices stay within ±2%)" if not option_1_works else '✓ Should work'}"
)

print(f"\nOPTION 2: Use VOLATILITY-BASED thresholds (standard deviation)")
print(f"  Buy if  < mean - 1×std = {tom_mean - tom_std:.2f}")
print(f"  Sell if > mean + 1×std = {tom_mean + tom_std:.2f}")
print(f"  This adapts to actual market volatility")

print(f"\nOPTION 3: Start trading EARLIER (don't wait for 50 prices)")
print(f"  Current: self.max_history = 50 (waits ~50 iterations)")
print(f"  New:     self.max_history = 20 (starts trading sooner)")
print(f"  Trades: Earlier signals might catch moves before mean stabilizes")

print(f"\nOPTION 4: COMBINE strategies (most aggressive)")
print(f"  Use 1.5% thresholds AND trade after 20 prices")
print(f"  This increases chances of finding opportunities")

print("\n" + "=" * 80)
print("📋 IMPLEMENTATION GUIDE")
print("=" * 80)

print("""
In your strategy.py, find these lines around line 90-100:

    if product == "TOMATOES":
        buy_threshold = 0.98 * mean_price
        sell_threshold = 1.02 * mean_price

CHANGE TO (Option 1 - Tighter Thresholds):
    if product == "TOMATOES":
        buy_threshold = 0.985 * mean_price    # Changed from 0.98
        sell_threshold = 1.015 * mean_price   # Changed from 1.02

OR (Option 2 - Volatility Based):
    if product == "TOMATOES":
        buy_threshold = mean_price - 1.5 * stdev
        sell_threshold = mean_price + 1.5 * stdev

OR (Option 3 - Earlier Start):
    self.max_history = 20    # Changed from 50

Then resubmit and you should get profitable trades!
""")

print("=" * 80)
