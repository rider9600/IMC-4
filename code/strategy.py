"""
Algorithmic Trading Strategy for Prosperity 4
IMPROVED Mean-reversion trading with volatility-based thresholds
"""

from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import jsonpickle
import statistics
import math


class Trader:
    def __init__(self):
        """Initialize the trader with default parameters."""
        self.price_history = {}  # Track price history for each product
        self.max_history = 20  # Start trading after only 20 observations (was 50)

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
        """Get mean, std deviation, and range from price history."""
        if product not in price_history or len(price_history[product]) == 0:
            return {"mean": None, "std": None, "min": None, "max": None, "len": 0}

        prices = price_history[product]
        mean_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)

        # Calculate std dev only if we have 2+ prices
        std_price = None
        if len(prices) >= 2:
            std_price = statistics.stdev(prices)

        return {
            "mean": mean_price,
            "std": std_price,
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

            # ===== TOMATOES: Volatility-Based Mean-Reversion Strategy =====
            if product == "TOMATOES":
                position_limit = 100

                if stats["mean"] is not None:
                    mean_price = stats["mean"]
                    std_price = stats["std"]

                    # Use adaptive thresholds based on actual volatility
                    # If we have std dev, use it; otherwise use conservative fallback
                    if std_price is not None and std_price > 0:
                        # Volatility-based thresholds
                        buy_threshold = mean_price - 1.2 * std_price
                        sell_threshold = mean_price + 1.2 * std_price
                        signal_strength = min(
                            1.0, abs(acceptable_price - mean_price) / (2 * std_price)
                        )
                    else:
                        # Early trading - use tighter percentage thresholds
                        buy_threshold = (
                            0.97 * mean_price
                        )  # 3% below mean (tighter than 2%)
                        sell_threshold = 1.03 * mean_price  # 3% above mean
                        signal_strength = 0.5

                    # ===== INTELLIGENT BUY LOGIC =====
                    if acceptable_price < buy_threshold:
                        if len(order_depth.sell_orders) != 0:
                            sell_orders = sorted(order_depth.sell_orders.items())
                            orders_to_place = []

                            for ask_price, ask_amount in sell_orders:
                                qty_to_buy = abs(ask_amount)

                                # Strong signal: buy aggressively
                                if current_position + qty_to_buy <= position_limit:
                                    orders_to_place.append(
                                        Order(product, ask_price, qty_to_buy)
                                    )
                                    current_position += qty_to_buy
                                else:
                                    # Buy only what we can
                                    available_qty = position_limit - current_position
                                    if available_qty > 0:
                                        orders_to_place.append(
                                            Order(product, ask_price, available_qty)
                                        )
                                        current_position = position_limit
                                    break

                            # Also place market-making buy order slightly below best bid
                            if (
                                current_position < position_limit
                                and len(order_depth.buy_orders) > 0
                            ):
                                best_bid = max(order_depth.buy_orders.keys())
                                # Place order just below best bid to accumulate on weakness
                                mm_price = max(best_bid - 1, 1)
                                mm_qty = min(10, position_limit - current_position)
                                if mm_qty > 0:
                                    orders_to_place.append(
                                        Order(product, mm_price, mm_qty)
                                    )
                                    current_position += mm_qty

                            orders.extend(orders_to_place)

                    # ===== INTELLIGENT SELL LOGIC =====
                    elif acceptable_price > sell_threshold:
                        if len(order_depth.buy_orders) != 0:
                            buy_orders = sorted(
                                order_depth.buy_orders.items(), reverse=True
                            )
                            orders_to_place = []

                            for bid_price, bid_amount in buy_orders:
                                # sell_amount is positive in our convention
                                qty_to_sell = bid_amount

                                # Strong signal: sell aggressively
                                if current_position - qty_to_sell >= -position_limit:
                                    orders_to_place.append(
                                        Order(product, bid_price, -qty_to_sell)
                                    )
                                    current_position -= qty_to_sell
                                else:
                                    # Sell only what we can
                                    available_qty = position_limit + current_position
                                    if available_qty > 0:
                                        orders_to_place.append(
                                            Order(product, bid_price, -available_qty)
                                        )
                                        current_position = -position_limit
                                    break

                            # Also place market-making sell order slightly above best ask
                            if (
                                current_position > -position_limit
                                and len(order_depth.sell_orders) > 0
                            ):
                                best_ask = min(order_depth.sell_orders.keys())
                                # Place order just above best ask to sell on strength
                                mm_price = best_ask + 1
                                mm_qty = min(10, position_limit + current_position)
                                if mm_qty > 0:
                                    orders_to_place.append(
                                        Order(product, mm_price, -mm_qty)
                                    )
                                    current_position -= mm_qty

                            orders.extend(orders_to_place)

                    # ===== MEAN REVERSION: If near mean, take profits =====
                    elif abs(acceptable_price - mean_price) < 0.5 * (
                        sell_threshold - buy_threshold
                    ):
                        # Price is near mean - lock in profits
                        if current_position > 10:
                            # Sell some accumulated inventory
                            if len(order_depth.buy_orders) > 0:
                                best_bid = max(order_depth.buy_orders.keys())
                                qty_to_sell = min(10, current_position)
                                orders.append(Order(product, best_bid, -qty_to_sell))
                                current_position -= qty_to_sell
                        elif current_position < -10:
                            # Buy back short positions
                            if len(order_depth.sell_orders) > 0:
                                best_ask = min(order_depth.sell_orders.keys())
                                qty_to_buy = min(10, -current_position)
                                orders.append(Order(product, best_ask, qty_to_buy))
                                current_position += qty_to_buy

            # ===== EMERALDS: Volatility-Based Conservative Strategy =====
            elif product == "EMERALDS":
                position_limit = 100

                if stats["mean"] is not None:
                    mean_price = stats["mean"]
                    std_price = stats["std"]

                    # EMERALDS is very stable (0.72 std), use tighter adaptive thresholds
                    if std_price is not None and std_price > 0:
                        # Use 1.5 std for tight but achievable thresholds
                        buy_threshold = mean_price - 1.5 * std_price
                        sell_threshold = mean_price + 1.5 * std_price
                    else:
                        # Early trading - very conservative
                        buy_threshold = 0.995 * mean_price  # 0.5% below mean
                        sell_threshold = 1.005 * mean_price  # 0.5% above mean

                    # BUY when significantly undervalued
                    if acceptable_price < buy_threshold:
                        if len(order_depth.sell_orders) != 0:
                            sell_orders = sorted(order_depth.sell_orders.items())

                            for ask_price, ask_amount in sell_orders:
                                qty_to_buy = abs(ask_amount)
                                if current_position + qty_to_buy <= position_limit:
                                    orders.append(Order(product, ask_price, qty_to_buy))
                                    current_position += qty_to_buy
                                else:
                                    available_qty = position_limit - current_position
                                    if available_qty > 0:
                                        orders.append(
                                            Order(product, ask_price, available_qty)
                                        )
                                        current_position = position_limit
                                    break

                    # SELL when significantly overvalued
                    elif acceptable_price > sell_threshold:
                        if len(order_depth.buy_orders) != 0:
                            buy_orders = sorted(
                                order_depth.buy_orders.items(), reverse=True
                            )

                            for bid_price, bid_amount in buy_orders:
                                qty_to_sell = bid_amount
                                if current_position - qty_to_sell >= -position_limit:
                                    orders.append(
                                        Order(product, bid_price, -qty_to_sell)
                                    )
                                    current_position -= qty_to_sell
                                else:
                                    available_qty = position_limit + current_position
                                    if available_qty > 0:
                                        orders.append(
                                            Order(product, bid_price, -available_qty)
                                        )
                                        current_position = -position_limit
                                    break

            result[product] = orders

        # Persist state to next iteration
        traderData = jsonpickle.encode(price_history)

        # No conversion requests in this strategy
        conversions = 0

        return result, conversions, traderData
