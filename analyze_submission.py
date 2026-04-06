#!/usr/bin/env python3
import json

# Read the JSON submission
with open('submissions/54677/54677.json', 'r') as f:
    data = json.load(f)

# Extract key metrics
print("="*60)
print("SUBMISSION 54677 ANALYSIS")
print("="*60)

if isinstance(data, dict):
    for key in ['product_profits', 'total', 'net_pnl', 'status', 'summary']:
        if key in data:
            print(f"\n{key}:")
            if isinstance(data[key], dict):
                for k, v in data[key].items():
                    print(f"  {k}: {v}")
            else:
                print(f"  {data[key]}")
else:
    print(type(data))
    print(data[:100] if isinstance(data, (list, str)) else data)

# Try to parse trades from the log
import re
trades_match = re.search(r'"trades":\[(.*?)\]', str(data))
if trades_match:
    trades_str = '[' + trades_match.group(1) + ']'
    try:
        trades = json.loads(trades_str)
        print(f"\nTotal trades recorded: {len(trades)}")
    except:
        pass

# Look for profit/loss info
pnl_match = re.search(r'"profit_and_loss"', str(data))
print(f"\nFound profit_and_loss field: {pnl_match is not None}")

# Print sample of data structure
print(f"\nData type: {type(data)}")
if isinstance(data, dict):
    print(f"Keys in data: {list(data.keys())[:10]}")
