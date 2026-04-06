"""
Algorithmic Trading Strategy for Prosperity 4
Mean-reversion with explicit stop-loss, cooldown, and end-of-day de-risking.
"""

from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple
import jsonpickle
import statistics


class Trader:
    def __init__(self):
        self.max_history = 40

    def bid(self) -> int:
        return 15

    def _load_state(self, trader_data: str) -> Dict:
        state = {
            "price_history": {},
            "entry_ts": {},
            "cooldown_until": {},
            "last_pos": {},
        }
        if not trader_data:
            return state

        try:
            decoded = jsonpickle.decode(trader_data)
            if isinstance(decoded, dict) and "price_history" in decoded:
                state.update(decoded)
            elif isinstance(decoded, dict):
                # Backward compatibility with previous saved format.
                state["price_history"] = decoded
        except Exception:
            pass
        return state

    def _mid_price(self, order_depth: OrderDepth, product: str) -> int:
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) // 2
        if best_bid is not None:
            return best_bid
        if best_ask is not None:
            return best_ask
        return 5000 if product == "TOMATOES" else 10000

    def _stats(self, prices: List[float]) -> Tuple[float, float]:
        if len(prices) < 8:
            return None, None
        mean_price = sum(prices) / len(prices)
        std_price = statistics.stdev(prices)
        if std_price <= 0:
            return None, None
        return mean_price, std_price

    def _buy_from_asks(
        self,
        product: str,
        order_depth: OrderDepth,
        max_qty: int,
        price_cap: int = None,
    ) -> List[Order]:
        orders: List[Order] = []
        remaining = max(0, max_qty)
        for ask_price, ask_amount in sorted(order_depth.sell_orders.items()):
            if remaining <= 0:
                break
            if price_cap is not None and ask_price > price_cap:
                break
            qty = min(remaining, abs(ask_amount))
            if qty > 0:
                orders.append(Order(product, ask_price, qty))
                remaining -= qty
        return orders

    def _sell_to_bids(
        self,
        product: str,
        order_depth: OrderDepth,
        max_qty: int,
        price_floor: int = None,
    ) -> List[Order]:
        orders: List[Order] = []
        remaining = max(0, max_qty)
        for bid_price, bid_amount in sorted(order_depth.buy_orders.items(), reverse=True):
            if remaining <= 0:
                break
            if price_floor is not None and bid_price < price_floor:
                break
            qty = min(remaining, bid_amount)
            if qty > 0:
                orders.append(Order(product, bid_price, -qty))
                remaining -= qty
        return orders

    def run(self, state: TradingState) -> tuple:
        persisted = self._load_state(state.traderData)
        price_history = persisted["price_history"]
        entry_ts = persisted["entry_ts"]
        cooldown_until = persisted["cooldown_until"]
        last_pos = persisted["last_pos"]

        result: Dict[str, List[Order]] = {}

        params = {
            "TOMATOES": {
                "pos_limit": 60,
                "order_size": 8,
                "entry_k": 0.60,
                "exit_k": 0.20,
                "stop_k": 1.15,
                "max_hold_ms": 3500,
                "cooldown_ms": 700,
                "near_close_ts": 188000,
                "hard_close_ts": 196000,
            },
            "EMERALDS": {
                "pos_limit": 40,
                "order_size": 6,
                "entry_k": 0.70,
                "exit_k": 0.25,
                "stop_k": 1.00,
                "max_hold_ms": 5000,
                "cooldown_ms": 900,
                "near_close_ts": 188000,
                "hard_close_ts": 196000,
            },
        }

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            p = params.get(product, params["TOMATOES"])

            current_pos = state.position.get(product, 0)
            prev_pos = last_pos.get(product, 0)
            mid = self._mid_price(order_depth, product)

            if product not in price_history:
                price_history[product] = []
            price_history[product].append(mid)
            if len(price_history[product]) > self.max_history:
                price_history[product] = price_history[product][-self.max_history :]

            mean_price, std_price = self._stats(price_history[product])
            if mean_price is None:
                result[product] = orders
                last_pos[product] = current_pos
                continue

            # Track time when a fresh position is opened or direction flips.
            if current_pos != 0 and (prev_pos == 0 or (prev_pos > 0) != (current_pos > 0)):
                entry_ts[product] = state.timestamp
            if current_pos == 0:
                entry_ts[product] = state.timestamp

            # End-of-day inventory risk reduction.
            if state.timestamp >= p["hard_close_ts"] and current_pos != 0:
                close_qty = abs(current_pos)
                if current_pos > 0:
                    orders.extend(self._sell_to_bids(product, order_depth, close_qty))
                else:
                    orders.extend(self._buy_from_asks(product, order_depth, close_qty))
                result[product] = orders
                last_pos[product] = current_pos
                continue

            if state.timestamp >= p["near_close_ts"] and abs(current_pos) > p["order_size"]:
                reduce_qty = min(abs(current_pos), p["order_size"] * 2)
                if current_pos > 0:
                    orders.extend(self._sell_to_bids(product, order_depth, reduce_qty))
                else:
                    orders.extend(self._buy_from_asks(product, order_depth, reduce_qty))
                result[product] = orders
                last_pos[product] = current_pos
                continue

            # Stop-loss based on adverse move relative to rolling mean.
            stop_loss_triggered = False
            if current_pos > 0 and mid < mean_price - p["stop_k"] * std_price:
                reduce_qty = min(abs(current_pos), p["order_size"] * 2)
                orders.extend(self._sell_to_bids(product, order_depth, reduce_qty))
                cooldown_until[product] = state.timestamp + p["cooldown_ms"]
                stop_loss_triggered = True
            elif current_pos < 0 and mid > mean_price + p["stop_k"] * std_price:
                reduce_qty = min(abs(current_pos), p["order_size"] * 2)
                orders.extend(self._buy_from_asks(product, order_depth, reduce_qty))
                cooldown_until[product] = state.timestamp + p["cooldown_ms"]
                stop_loss_triggered = True

            if stop_loss_triggered:
                result[product] = orders
                last_pos[product] = current_pos
                continue

            # Time stop: do not hold one-direction inventory for too long.
            hold_time = state.timestamp - entry_ts.get(product, state.timestamp)
            if current_pos != 0 and hold_time > p["max_hold_ms"]:
                reduce_qty = min(abs(current_pos), p["order_size"])
                if current_pos > 0:
                    orders.extend(self._sell_to_bids(product, order_depth, reduce_qty))
                else:
                    orders.extend(self._buy_from_asks(product, order_depth, reduce_qty))
                result[product] = orders
                last_pos[product] = current_pos
                continue

            in_cooldown = state.timestamp < cooldown_until.get(product, -1)
            buy_threshold = mean_price - p["entry_k"] * std_price
            sell_threshold = mean_price + p["entry_k"] * std_price
            flat_band = p["exit_k"] * std_price

            # Mean reversion exits first when close to fair value.
            if abs(mid - mean_price) <= flat_band and current_pos != 0:
                reduce_qty = min(abs(current_pos), p["order_size"])
                if current_pos > 0:
                    orders.extend(self._sell_to_bids(product, order_depth, reduce_qty))
                else:
                    orders.extend(self._buy_from_asks(product, order_depth, reduce_qty))
            elif not in_cooldown:
                # New entries only outside cooldown.
                if mid < buy_threshold and current_pos < p["pos_limit"]:
                    qty = min(p["order_size"], p["pos_limit"] - current_pos)
                    orders.extend(self._buy_from_asks(product, order_depth, qty))
                elif mid > sell_threshold and current_pos > -p["pos_limit"]:
                    qty = min(p["order_size"], p["pos_limit"] + current_pos)
                    orders.extend(self._sell_to_bids(product, order_depth, qty))

            result[product] = orders
            last_pos[product] = current_pos

        trader_data = jsonpickle.encode(
            {
                "price_history": price_history,
                "entry_ts": entry_ts,
                "cooldown_until": cooldown_until,
                "last_pos": last_pos,
            }
        )
        return result, 0, trader_data