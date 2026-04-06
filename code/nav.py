from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import jsonpickle
import statistics


class Trader:
    def __init__(self):
        self.max_history = 50
        self.pos_limit = 10000
        self.base_size = 100

    # -------------------------
    # UTILS
    # -------------------------

    def mid_price(self, od: OrderDepth):
        return (max(od.buy_orders) + min(od.sell_orders)) / 2

    def vwap(self, orders: Dict[int, int]):
        total_qty, total_val = 0, 0
        for p, q in orders.items():
            q = abs(q)
            total_qty += q
            total_val += p * q
        return total_val / total_qty if total_qty > 0 else None

    def imbalance(self, buys, sells):
        b = sum(buys.values())
        s = sum(abs(v) for v in sells.values())
        return b / (b + s) if (b + s) > 0 else 0.5

    def take_asks(self, product, od, qty):
        orders = []
        for p, q in sorted(od.sell_orders.items()):
            take = min(qty, abs(q))
            orders.append(Order(product, p, take))
            qty -= take
            if qty <= 0:
                break
        return orders

    def hit_bids(self, product, od, qty):
        orders = []
        for p, q in sorted(od.buy_orders.items(), reverse=True):
            take = min(qty, q)
            orders.append(Order(product, p, -take))
            qty -= take
            if qty <= 0:
                break
        return orders

    # -------------------------
    # MAIN
    # -------------------------

    def run(self, state: TradingState):
        persisted = jsonpickle.decode(state.traderData) if state.traderData else {}
        price_history = persisted.get("price_history", {})

        result = {}

        for product, od in state.order_depths.items():
            orders: List[Order] = []

            if not od.buy_orders or not od.sell_orders:
                result[product] = orders
                continue

            # ---- PRICE ----
            best_bid = max(od.buy_orders)
            best_ask = min(od.sell_orders)
            mid = (best_bid + best_ask) / 2
            spread = best_ask - best_bid

            # ---- HISTORY ----
            price_history.setdefault(product, []).append(mid)
            price_history[product] = price_history[product][-self.max_history:]

            if len(price_history[product]) < 15:
                result[product] = orders
                continue

            mean = statistics.mean(price_history[product])
            std = statistics.stdev(price_history[product])
            if std == 0:
                result[product] = orders
                continue

            # ---- TREND (important) ----
            recent = price_history[product][-5:]
            older = price_history[product][-10:-5]
            trend = (sum(recent)/5) - (sum(older)/5)
            trend_strength = abs(trend) / std

            # ---- FAIR VALUE ----
            fair = mean + 0.5 * trend

            # ---- MICRO SIGNAL ----
            imb = self.imbalance(od.buy_orders, od.sell_orders)
            micro = imb - 0.5
            micro_strength = abs(micro)

            # ---- POSITION ----
            pos = state.position.get(product, 0)

            # -------------------------
            # DYNAMIC THRESHOLDS
            # -------------------------
            k = 0.6 + 0.4 * abs(pos)/self.pos_limit
            buy_th = fair - k * std
            sell_th = fair + k * std

            # -------------------------
            # CONFIDENCE SIZING
            # -------------------------
            confidence = min(1.0, micro_strength * 4)
            qty = int(self.base_size * confidence * (1 - abs(pos)/self.pos_limit))
            qty = max(1, qty)

            # -------------------------
            # 1. MARKET MAKING (CORE)
            # -------------------------
            if spread >= 2:
                mm_edge = max(1, int(0.25 * std))

                if pos < self.pos_limit:
                    orders.append(Order(product, int(fair - mm_edge), 100))
                if pos > -self.pos_limit:
                    orders.append(Order(product, int(fair + mm_edge), -100))

            # -------------------------
            # 2. DIRECTIONAL TRADES
            # -------------------------
            if (
                mid < buy_th
                and micro > 0
                and micro_strength > 0.1
                and trend_strength < 1.0
                and pos < self.pos_limit
                and spread >= 2
            ):
                orders += self.take_asks(product, od, min(qty, self.pos_limit - pos))

            elif (
                mid > sell_th
                and micro < 0
                and micro_strength > 0.1
                and trend_strength < 1.0
                and pos > -self.pos_limit
                and spread >= 2
            ):
                orders += self.hit_bids(product, od, min(qty, self.pos_limit + pos))

            # -------------------------
            # 3. EXIT LOGIC (VERY IMPORTANT)
            # -------------------------
            if abs(mid - fair) < 0.15 * std:
                reduce = min(abs(pos), 100)
                if pos > 0:
                    orders += self.hit_bids(product, od, reduce)
                elif pos < 0:
                    orders += self.take_asks(product, od, reduce)

            # emergency exit
            if abs(mid - fair) > 1.8 * std:
                reduce = min(abs(pos), 150)
                if pos > 0:
                    orders += self.hit_bids(product, od, reduce)
                elif pos < 0:
                    orders += self.take_asks(product, od, reduce)

            result[product] = orders

        trader_data = jsonpickle.encode({"price_history": price_history})
        return result, 0, trader_data