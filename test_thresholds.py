#!/usr/bin/env python3
import pandas as pd
import sys
import statistics
sys.path.insert(0, 'code')

prices_file = 'data/prices_round_0_day_-1.csv'
df = pd.read_csv(prices_file, delimiter=';')

print("=== THRESHOLD TESTING ===")
for product in ['TOMATOES', 'EMERALDS']:
    prod_df = df[df['product'] == product].copy()
    prod_df = prod_df.reset_index(drop=True)
    prices = prod_df['mid_price'].tolist()
    
    print(f"\n{product}:")
    print(f"  Price range: {min(prices):.2f} - {max(prices):.2f}")
    print(f"  Std dev: {statistics.stdev(prices):.4f}")
    print(f"  Mean: {statistics.mean(prices):.2f}")
    
    # Test different threshold strategies
    ma = sum(prices[-20:]) / 20 if len(prices) >= 20 else sum(prices) / len(prices)
    std_dev = statistics.stdev(prices) if len(prices) >= 2 else 0
    
    print(f"\n  Current approach (0.98/1.02):")
    print(f"    Buy threshold: {0.98 * ma:.2f}")
    print(f"    Sell threshold: {1.02 * ma:.2f}")
    buy_count = sum(1 for p in prices if p < 0.98 * ma)
    sell_count = sum(1 for p in prices if p > 1.02 * ma)
    print(f"    Would trigger: {buy_count} buys, {sell_count} sells")
    
    print(f"\n  Better approach (mean ± 0.5*std):")
    buy_thresh = ma - 0.5 * std_dev
    sell_thresh = ma + 0.5 * std_dev
    print(f"    Buy threshold: {buy_thresh:.2f}")
    print(f"    Sell threshold: {sell_thresh:.2f}")
    buy_count = sum(1 for p in prices if p < buy_thresh)
    sell_count = sum(1 for p in prices if p > sell_thresh)
    print(f"    Would trigger: {buy_count} buys, {sell_count} sells")
    
    print(f"\n  Aggressive approach (mean ± 0.3*std):")
    buy_thresh = ma - 0.3 * std_dev
    sell_thresh = ma + 0.3 * std_dev
    print(f"    Buy threshold: {buy_thresh:.2f}")
    print(f"    Sell threshold: {sell_thresh:.2f}")
    buy_count = sum(1 for p in prices if p < buy_thresh)
    sell_count = sum(1 for p in prices if p > sell_thresh)
    print(f"    Would trigger: {buy_count} buys, {sell_count} sells")

    # Also check bid-ask spread impact
    print(f"\n  Bid-ask spread impact:")
    spreads = prod_df['ask_price_1'] - prod_df['bid_price_1']
    print(f"    Average spread: {spreads.mean():.2f}")
    print(f"    This means we always lose {spreads.mean() / 2:.2f} on entry+exit")
