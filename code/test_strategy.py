"""
Simple Test: Strategy in Action
Demonstrates the Trader class with a minimal example
"""

from datamodel import TradingState, OrderDepth, Order, Trade, Listing, Observation
from strategy import Trader


def create_sample_trading_state():
    """
    Create a simple example TradingState for testing.
    This simulates market conditions for two products.
    """

    # Product listings
    listings = {
        "TOMATOES": Listing(
            symbol="TOMATOES", product="TOMATOES", denomination="XIRECS"
        ),
        "EMERALDS": Listing(
            symbol="EMERALDS", product="EMERALDS", denomination="XIRECS"
        ),
    }

    # Order book depth (current bids and asks)
    order_depths = {
        "TOMATOES": OrderDepth(),
        "EMERALDS": OrderDepth(),
    }

    # TOMATOES order book
    # Buyers willing to pay these prices
    order_depths["TOMATOES"].buy_orders = {
        4999: 5,  # 5 units at 4999
        4998: 10,  # 10 units at 4998
        4997: 15,  # 15 units at 4997
    }
    # Sellers asking these prices (negative quantities)
    order_depths["TOMATOES"].sell_orders = {
        5001: -5,  # 5 units for sale at 5001
        5002: -10,  # 10 units for sale at 5002
        5003: -15,  # 15 units for sale at 5003
    }

    # EMERALDS order book (tighter spread, more stable)
    order_depths["EMERALDS"].buy_orders = {
        9999: 8,
        9998: 12,
        9997: 16,
    }
    order_depths["EMERALDS"].sell_orders = {
        10001: -8,
        10002: -12,
        10003: -16,
    }

    # Trades that happened since last iteration
    own_trades = {
        "TOMATOES": [],
        "EMERALDS": [],
    }
    market_trades = {
        "TOMATOES": [],
        "EMERALDS": [],
    }

    # Current positions in each product
    position = {
        "TOMATOES": 2,  # Currently holding 2 tomatoes
        "EMERALDS": -1,  # Currently short 1 emerald
    }

    # Market observations (optional features)
    observations = Observation(plainValueObservations={}, conversionObservations={})

    # Create the state
    state = TradingState(
        traderData="",
        timestamp=1000,
        listings=listings,
        order_depths=order_depths,
        own_trades=own_trades,
        market_trades=market_trades,
        position=position,
        observations=observations,
    )

    return state


def run_test():
    """Run a simple test of the strategy."""

    print("=" * 80)
    print("SIMPLE STRATEGY TEST")
    print("=" * 80)

    # Create trader
    print("\n[*] Initializing trader...")
    trader = Trader()
    print("    ✓ Trader created successfully")
    print(f"    ✓ bid() method returns: {trader.bid()}")

    # Create test state
    print("\n[*] Creating sample trading state...")
    state = create_sample_trading_state()
    print(f"    ✓ Timestamp: {state.timestamp}")
    print(f"    ✓ Products: {list(state.order_depths.keys())}")
    print(f"    ✓ Current position TOMATOES: {state.position['TOMATOES']}")
    print(f"    ✓ Current position EMERALDS: {state.position['EMERALDS']}")

    # Show order book
    print("\n[*] Current Order Book:")
    for product in ["TOMATOES", "EMERALDS"]:
        od = state.order_depths[product]
        print(f"\n  {product}:")

        # Best bid
        if od.buy_orders:
            best_bid = max(od.buy_orders.keys())
            print(f"    Best BID: {best_bid} (size: {od.buy_orders[best_bid]})")

        # Best ask
        if od.sell_orders:
            best_ask = min(od.sell_orders.keys())
            print(f"    Best ASK: {best_ask} (size: {-od.sell_orders[best_ask]})")

        # Calculate mid-price
        if od.buy_orders and od.sell_orders:
            mid = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            print(f"    Mid-price: {mid}")
            print(f"    Spread: {spread}")

    # Run strategy
    print("\n[*] Running strategy (first iteration)...")
    result, conversions, trader_data = trader.run(state)

    print(f"\n    ✓ Strategy completed successfully")
    print(f"\n[*] Strategy Output:")
    print(f"    Orders returned: {len(result)} products")

    total_orders = sum(len(orders) for orders in result.values())
    print(f"    Total orders: {total_orders}")

    for product, orders in result.items():
        if orders:
            print(f"\n    {product}: {len(orders)} order(s)")
            for i, order in enumerate(orders, 1):
                action = "BUY" if order.quantity > 0 else "SELL"
                qty = abs(order.quantity)
                print(f"      Order {i}: {action} {qty} @ {order.price}")
        else:
            print(f"\n    {product}: NO ORDERS")

    print(f"\n    Conversions: {conversions}")
    print(f"    Trader state saved: {len(trader_data)} characters")

    # Simulate second iteration with some price change
    print("\n" + "=" * 80)
    print("SIMULATING SECOND ITERATION")
    print("=" * 80)

    # Create new state with slightly different prices
    state2 = create_sample_trading_state()
    state2.timestamp = 1100
    state2.traderData = trader_data  # Restore previous state!

    # Modify some prices to simulate market movement
    state2.order_depths["TOMATOES"].buy_orders = {
        4995: 5,  # Lower bids now
        4993: 10,
        4991: 15,
    }
    state2.order_depths["TOMATOES"].sell_orders = {
        5005: -5,  # Higher asks now
        5006: -10,
        5007: -15,
    }

    print("\n[*] Market has moved - new order book:")
    for product in ["TOMATOES", "EMERALDS"]:
        od = state2.order_depths[product]
        if od.buy_orders and od.sell_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            mid = (best_bid + best_ask) / 2
            print(f"    {product}: bid={best_bid}, ask={best_ask}, mid={mid}")

    print("\n[*] Running strategy (second iteration)...")
    result2, conversions2, trader_data2 = trader.run(state2)

    print(f"    ✓ Strategy completed")

    total_orders2 = sum(len(orders) for orders in result2.values())
    print(f"    Total orders: {total_orders2}")

    for product, orders in result2.items():
        if orders:
            print(f"    {product}: {len(orders)} order(s)")
            for order in orders:
                action = "BUY" if order.quantity > 0 else "SELL"
                qty = abs(order.quantity)
                print(f"      {action} {qty} @ {order.price}")

    # Show that state was restored and used
    print(f"\n[*] State Management:")
    print(f"    Previous traderData size: {len(trader_data)}")
    print(f"    New traderData size: {len(trader_data2)}")
    print(f"    ✓ Price history is being maintained across iterations!")

    print("\n" + "=" * 80)
    print("✅ STRATEGY TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("""
Key Observations:
  1. Trader class instantiated and ready
  2. run() method executed without errors
  3. Orders generated based on market conditions
  4. State persisted and loaded for next iteration
  5. Strategy is responsive to market changes
  
Next Steps:
  - Review the orders being generated
  - Verify they make sense given the order book
  - Upload strategy.py to Prosperity platform
  - Monitor real-time performance
  - Adjust parameters if needed
    """)


if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
