#!/usr/bin/env python3
import pandas as pd
import sys
sys.path.insert(0, 'code')
from backtest import SimpleBacktester

prices_file = 'data/prices_round_0_day_-1.csv'
df = pd.read_csv(prices_file, delimiter=';')

tester = SimpleBacktester(100000)
results = tester.backtest_day(df)
summary = tester.get_summary()

print('=== BACKTEST RESULTS ===')
print(f'Starting Balance: {summary["starting_balance"]:,.0f}')
print(f'Current Balance: {summary["current_balance"]:,.0f}')
print(f'Portfolio Value: {summary["portfolio_value"]:,.0f}')
print(f'Total Return/PnL: {summary["total_return"]:,.0f}')
print(f'Return %: {summary["return_pct"]:.2f}%')
print(f'\nTrades Executed: {results["trades"]}')
print(f'Final Positions: {results["final_position"]}')
print(f'Signal Stats - BUY: {results["signals"]["BUY"]}, SELL: {results["signals"]["SELL"]}, HOLD: {results["signals"]["HOLD"]}')
print(f'\nDetailed Trades:')
for trade in tester.trades[:10]:
    print(f'  {trade}')
if len(tester.trades) > 10:
    print(f'  ... and {len(tester.trades) - 10} more trades')
