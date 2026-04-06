"""
Algorithmic Trading Strategy for Prosperity 4
IMPROVED Mean-reversion with proper std-deviation based thresholds
"""

from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import jsonpickle
import statistics


class Trader:
    def __init__(self):
        """Initialize the trader with default parameters."""
        self.price_history = {}  # Track price history for each product
        self.max_history = 50  # Keep 50 observations for statistics

    def bid(self) -> int:
        """Required for Round 2, returning a fixed bid value."""
        return 15

    def get_mid_price(self, order_depth: OrderDepth) -> int:
        """Calculate mid-price from best bid and ask."""
        best_bid = None
        best_ask = None

        if len(order_depth.buy_orders) > 0:
            best_bid = max(order_depth.buy_orders.keys())

        if len(order_depth.sell_orders) > 0:
            best_ask = min(order_depth.sell_orders.keys())

        # Calculate mid-price
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) // 2
        elif best_bid is not None:
            return best_bid
        elif best_ask is not None:
            return best_ask
        else:
            # Fallback if no orders exist
            return 5000 if best_bid is None and best_ask is None else max(best_bid or 0, best_ask or 0)

    def get_price_stats(self, prices: List[float]) -> Dict:
        """Get mean and std deviation from price history."""
        if len(prices) < 2:
            return {"mean": None, "std": None}

        mean_price = sum(prices) / len(prices)
        std_price = statistics.stdev(prices)

        return {"mean": mean_price, "std": std_price}

    def run(self, state: TradingState) -> tuple:
        """
        Main trading logic. Called every iteration with current market state.

        Returns:
            (result, conversions, traderData)
        """

        # Load price history from previous iteration
        price_history = {}
        if state.traderData:
            try:
                price_history = jsonpickle.decode(state.traderData)
            except:
                price_history = {}

        result = {}

        # Process each product
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # Get current position
            current_position = state.position.get(product, 0)

            # Get mid-price
            mid_price = self.get_mid_price(order_depth)

            # Update price history
            if product not in price_history:
                price_history[product] = []
            price_history[product].append(mid_price)
            if len(price_history[product]) > self.max_history:
                price_history[product] = price_history[product][-self.max_history:]

            # Get stats
            stats = self.get_price_stats(price_history[product])

            if stats["mean"] is None or stats["std"] is None or stats["std"] == 0:
                # Not enough data for signal
                result[product] = orders
                continue

            mean_price = stats["mean"]
            std_price = stats["std"]

            # ===== DETERMINE THRESHOLDS =====
            if product == "TOMATOES":
                # TOMATOES: more volatile, use 0.4 std thresholds
                buy_threshold = mean_price - 0.4 * std_price
                sell_threshold = mean_price + 0.4 * std_price
                position_limit = 100
                order_size = 5  # Smaller orders to avoid overcommitting
            else:  # EMERALDS
                # EMERALDS: very stable, use 0.5 std thresholds
                buy_threshold = mean_price - 0.5 * std_price
                sell_threshold = mean_price + 0.5 * std_price
                position_limit = 100
                order_size = 5

            # ===== TRADING LOGIC =====

            # BUY SIGNAL: Price below buy threshold
            if mid_price < buy_threshold and current_position < position_limit:
                if len(order_depth.sell_orders) > 0:
                    # Get best ask prices
                    best_asks = sorted(order_depth.sell_orders.items())
                    
                    for ask_price, ask_amount in best_asks:
                        qty_to_buy = min(order_size, abs(ask_amount), position_limit - current_position)
                        
                        if qty_to_buy > 0:
                            orders.append(Order(product, ask_price, qty_to_buy))
                            current_position += qty_to_buy
                        
                        if current_position >= position_limit:
                            break

            # SELL SIGNAL: Price above sell threshold
            elif mid_price > sell_threshold and current_position > -position_limit:
                if len(order_depth.buy_orders) > 0:
                    # Get best bid prices (highest first)
                    best_bids = sorted(order_depth.buy_orders.items(), reverse=True)
                    
                    for bid_price, bid_amount in best_bids:
                        qty_to_sell = min(order_size, bid_amount, position_limit + current_position)
                        
                        if qty_to_sell > 0:
                            orders.append(Order(product, bid_price, -qty_to_sell))
                            current_position -= qty_to_sell
                        
                        if current_position <= -position_limit:
                            break

            # PROFIT TAKING: If holding position and price near mean, close some
            elif abs(mid_price - mean_price) < 0.25 * (sell_threshold - buy_threshold):
                if current_position > 10:
                    # Sell some longs to take profit
                    if len(order_depth.buy_orders) > 0:
                        best_bid = max(order_depth.buy_orders.keys())
                        qty_to_sell = min(order_size, current_position)
                        orders.append(Order(product, best_bid, -qty_to_sell))
                        current_position -= qty_to_sell
                
                elif current_position < -10:
                    # Buy back some shorts to take profit
                    if len(order_depth.sell_orders) > 0:
                        best_ask = min(order_depth.sell_orders.keys())
                        qty_to_buy = min(order_size, -current_position)
                        orders.append(Order(product, best_ask, qty_to_buy))
                        current_position += qty_to_buy

            result[product] = orders

        # Persist state
        traderData = jsonpickle.encode(price_history)
        conversions = 0

        return result, conversions, traderData
