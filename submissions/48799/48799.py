"""
Algorithmic Trading Strategy for Prosperity 4
Mean-reversion based trading strategy for TOMATOES and EMERALDS
"""

from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import jsonpickle
import json


class Trader:
    def __init__(self):
        """Initialize the trader with default parameters."""
        self.price_history = {}  # Track price history for each product
        self.max_history = 50  # Maximum length of price history to maintain

    def bid(self) -> int:
        """Required for Round 2, returning a fixed bid value."""
        return 15

    def calculate_acceptable_price(self, product: str, order_depth: OrderDepth) -> int:
        """
        Calculate an acceptable price based on current order depth.
        Uses mid-price (average of best bid and best ask) if available.
        """
        best_bid = None
        best_ask = None

        if len(order_depth.buy_orders) > 0:
            best_bid = max(order_depth.buy_orders.keys())

        if len(order_depth.sell_orders) > 0:
            best_ask = min(order_depth.sell_orders.keys())

        # Calculate mid-price
        if best_bid is not None and best_ask is not None:
            acceptable_price = (best_bid + best_ask) // 2
        elif best_bid is not None:
            acceptable_price = best_bid
        elif best_ask is not None:
            acceptable_price = best_ask
        else:
            # Fallback if no orders exist
            acceptable_price = 5000 if product == "TOMATOES" else 10000

        return acceptable_price

    def get_price_stats(self, product: str, price_history: Dict) -> Dict:
        """Get mean and standard deviation from price history."""
        if product not in price_history or len(price_history[product]) == 0:
            return {"mean": None, "min": None, "max": None}

        prices = price_history[product]
        mean_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)

        return {
            "mean": mean_price,
            "min": min_price,
            "max": max_price,
            "len": len(prices),
        }

    def run(self, state: TradingState) -> tuple:
        """
        Main trading logic. Called every iteration with current market state.

        Args:
            state: TradingState object containing market data

        Returns:
            (result, conversions, traderData) where:
            - result: Dict of product -> List[Order]
            - conversions: int, number of conversion requests
            - traderData: str, state to persist to next iteration
        """

        # Load trader state from previous iteration
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

            # Get current position for this product
            current_position = state.position.get(product, 0)

            # Calculate acceptable price (mid-price)
            acceptable_price = self.calculate_acceptable_price(product, order_depth)

            # Update price history
            if product not in price_history:
                price_history[product] = []
            price_history[product].append(acceptable_price)
            # Keep only recent history
            if len(price_history[product]) > self.max_history:
                price_history[product] = price_history[product][-self.max_history :]

            # Get price statistics
            stats = self.get_price_stats(product, price_history)

            # ===== TOMATOES: Mean-Reversion Strategy =====
            if product == "TOMATOES":
                position_limit = 100  # Typical position limit for TOMATOES

                # Only trade if we have enough history
                if stats["mean"] is not None:
                    mean_price = stats["mean"]

                    # Buy when price is below mean (cheap), sell when above mean (expensive)
                    buy_threshold = 0.98 * mean_price  # 2% below mean
                    sell_threshold = 1.02 * mean_price  # 2% above mean

                    # BUY when cheap
                    if acceptable_price < buy_threshold:
                        # Look for best ask prices to buy from
                        if len(order_depth.sell_orders) != 0:
                            # Sort sell orders by price (ascending)
                            sell_orders = sorted(order_depth.sell_orders.items())

                            for ask_price, ask_amount in sell_orders:
                                # Check if we can still buy (position limit)
                                if current_position + abs(ask_amount) <= position_limit:
                                    orders.append(
                                        Order(product, ask_price, -ask_amount)
                                    )
                                    current_position += abs(ask_amount)
                                else:
                                    # Buy only up to position limit
                                    available_qty = position_limit - current_position
                                    if available_qty > 0:
                                        orders.append(
                                            Order(product, ask_price, available_qty)
                                        )
                                        current_position = position_limit
                                    break

                    # SELL when expensive
                    elif acceptable_price > sell_threshold:
                        # Look for best bid prices to sell to
                        if len(order_depth.buy_orders) != 0:
                            # Sort buy orders by price (descending)
                            buy_orders = sorted(
                                order_depth.buy_orders.items(), reverse=True
                            )

                            for bid_price, bid_amount in buy_orders:
                                # Check if we can still sell (position limit)
                                if current_position - bid_amount >= -position_limit:
                                    orders.append(
                                        Order(product, bid_price, -bid_amount)
                                    )
                                    current_position -= bid_amount
                                else:
                                    # Sell only down to short position limit
                                    available_qty = position_limit + current_position
                                    if available_qty > 0:
                                        orders.append(
                                            Order(product, bid_price, -available_qty)
                                        )
                                        current_position = -position_limit
                                    break

            # ===== EMERALDS: Conservative Strategy =====
            elif product == "EMERALDS":
                position_limit = 100  # Position limit for EMERALDS

                # More conservative: only trade on larger deviations
                if stats["mean"] is not None:
                    mean_price = stats["mean"]

                    # Use wider thresholds for EMERALDS (more stable)
                    buy_threshold = 0.995 * mean_price  # 0.5% below mean
                    sell_threshold = 1.005 * mean_price  # 0.5% above mean

                    # BUY when price dips significantly
                    if acceptable_price < buy_threshold:
                        if len(order_depth.sell_orders) != 0:
                            best_ask = min(order_depth.sell_orders.keys())
                            best_ask_amount = order_depth.sell_orders[best_ask]

                            if (
                                current_position + abs(best_ask_amount)
                                <= position_limit
                            ):
                                orders.append(
                                    Order(product, best_ask, -best_ask_amount)
                                )
                                current_position += abs(best_ask_amount)

                    # SELL when price rises significantly
                    elif acceptable_price > sell_threshold:
                        if len(order_depth.buy_orders) != 0:
                            best_bid = max(order_depth.buy_orders.keys())
                            best_bid_amount = order_depth.buy_orders[best_bid]

                            if current_position - best_bid_amount >= -position_limit:
                                orders.append(
                                    Order(product, best_bid, -best_bid_amount)
                                )
                                current_position -= best_bid_amount

            result[product] = orders

        # Persist state to next iteration
        traderData = jsonpickle.encode(price_history)

        # No conversion requests in this strategy
        conversions = 0

        return result, conversions, traderData