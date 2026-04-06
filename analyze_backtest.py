#!/usr/bin/env python3
import pandas as pd
import sys
import statistics
sys.path.insert(0, 'code')

prices_file = 'data/prices_round_0_day_-1.csv'
df = pd.read_csv(prices_file, delimiter=';')

print("=== DATA ANALYSIS ===")
print(f"Total rows: {len(df)}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst 5 rows:")
print(df.head())

print("\n=== PRODUCT STATISTICS ===")
for product in ['TOMATOES', 'EMERALDS']:
    prod_df = df[df['product'] == product]
    print(f"\n{product}:")
    print(f"  Observations: {len(prod_df)}")
    print(f"  Mid-price mean: {prod_df['mid_price'].mean():.2f}")
    print(f"  Mid-price std: {prod_df['mid_price'].std():.2f}")
    print(f"  Mid-price range: {prod_df['mid_price'].min():.2f} - {prod_df['mid_price'].max():.2f}")
    
    # Calculate moving averages for first 20 prices
    prices = prod_df['mid_price'].tolist()
    if len(prices) >= 20:
        ma20 = sum(prices[-20:]) / 20
        last_price = prices[-1]
        print(f"  Last 20-MA: {ma20:.2f}")
        print(f"  Last price: {last_price:.2f}")
        print(f"  Buy threshold (0.98 * MA): {0.98 * ma20:.2f}")
        print(f"  Sell threshold (1.02 * MA): {1.02 * ma20:.2f}")
        print(f"  Distance from MA: {last_price - ma20:.2f} ({(last_price/ma20 - 1)*100:.2f}%)")

print("\n=== BID-ASK ANALYSIS ===")
for product in ['TOMATOES', 'EMERALDS']:
    prod_df = df[df['product'] == product]
    # Sample a row to check bid-ask
    row = prod_df.iloc[0]
    print(f"\n{product} (sample row):")
    print(f"  Best bid: {row['bid_price_1']}")
    print(f"  Best ask: {row['ask_price_1']}")
    print(f"  Bid volume: {row['bid_volume_1']}")
    print(f"  Ask volume: {row['ask_volume_1']}")
    spread = row['ask_price_1'] - row['bid_price_1']
    print(f"  Spread: {spread}")
