import importlib.util
from pathlib import Path
import pandas as pd
import math
import sys

ROOT = Path(__file__).resolve().parent
CODE_DIR = ROOT / "code"
SUBMISSION_FILE = ROOT / "submissions" / "54949" / "54949.py"
CURRENT_FILE = CODE_DIR / "strategy.py"

sys.path.insert(0, str(CODE_DIR))
from datamodel import TradingState, OrderDepth, Listing, Observation  # noqa: E402


def load_trader(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Trader()


def get_levels(row, side: str):
    levels = []
    if side == "buy":
        pcols = ["bid_price_1", "bid_price_2", "bid_price_3"]
        vcols = ["bid_volume_1", "bid_volume_2", "bid_volume_3"]
    else:
        pcols = ["ask_price_1", "ask_price_2", "ask_price_3"]
        vcols = ["ask_volume_1", "ask_volume_2", "ask_volume_3"]

    for pc, vc in zip(pcols, vcols):
        p = row.get(pc)
        v = row.get(vc)
        if pd.isna(p) or pd.isna(v):
            continue
        p = int(p)
        v = int(v)
        if side == "sell":
            v = -abs(v)
        else:
            v = abs(v)
        levels.append((p, v))

    if side == "buy":
        levels.sort(reverse=True)
    else:
        levels.sort()
    return levels


def build_order_depth(row):
    od = OrderDepth()
    od.buy_orders = {p: v for p, v in get_levels(row, "buy")}
    od.sell_orders = {p: v for p, v in get_levels(row, "sell")}
    return od


def fill_order(order, row):
    qty_left = abs(order.quantity)
    if qty_left == 0:
        return 0, 0.0

    filled = 0
    cash = 0.0

    if order.quantity > 0:
        asks = get_levels(row, "sell")
        for price, vol in asks:
            avail = abs(vol)
            if price > order.price or qty_left <= 0:
                break
            take = min(qty_left, avail)
            filled += take
            cash -= take * price
            qty_left -= take
    else:
        bids = get_levels(row, "buy")
        for price, vol in bids:
            avail = abs(vol)
            if price < order.price or qty_left <= 0:
                break
            take = min(qty_left, avail)
            filled += take
            cash += take * price
            qty_left -= take

    if order.quantity < 0:
        filled = -filled

    return filled, cash


def run_replay(trader, prices_df):
    positions = {"TOMATOES": 0, "EMERALDS": 0}
    cash = 0.0
    trader_data = ""

    listings = {
        "TOMATOES": Listing("TOMATOES", "TOMATOES", "XIRECS"),
        "EMERALDS": Listing("EMERALDS", "EMERALDS", "XIRECS"),
    }

    grouped = prices_df.sort_values(["timestamp", "product"]).groupby("timestamp")

    for ts, g in grouped:
        order_depths = {}
        row_by_product = {}
        for _, row in g.iterrows():
            product = row["product"]
            row_by_product[product] = row
            order_depths[product] = build_order_depth(row)

        state = TradingState(
            traderData=trader_data,
            timestamp=int(ts),
            listings=listings,
            order_depths=order_depths,
            own_trades={"TOMATOES": [], "EMERALDS": []},
            market_trades={"TOMATOES": [], "EMERALDS": []},
            position=positions.copy(),
            observations=Observation({}, {}),
        )

        result, _, trader_data = trader.run(state)

        for product, orders in result.items():
            row = row_by_product.get(product)
            if row is None:
                continue
            for order in orders:
                filled, d_cash = fill_order(order, row)
                if filled != 0:
                    positions[product] += filled
                    cash += d_cash

    last_rows = prices_df.sort_values("timestamp").groupby("product").tail(1)
    mtm = 0.0
    for _, row in last_rows.iterrows():
        mtm += positions[row["product"]] * float(row["mid_price"])

    return {
        "cash": cash,
        "positions": positions,
        "mtm": mtm,
        "pnl": cash + mtm,
    }


def main():
    df = pd.read_csv(ROOT / "data" / "prices_round_0_day_-1.csv", sep=";")

    old_trader = load_trader(SUBMISSION_FILE, "old_54949")
    new_trader = load_trader(CURRENT_FILE, "new_current")

    old_res = run_replay(old_trader, df)
    new_res = run_replay(new_trader, df)

    print("=== Approx Replay: Day -1 ===")
    print(f"Old 54949 pnl: {old_res['pnl']:.2f}, pos={old_res['positions']}")
    print(f"New current pnl: {new_res['pnl']:.2f}, pos={new_res['positions']}")
    print(f"Delta pnl: {new_res['pnl'] - old_res['pnl']:.2f}")


if __name__ == "__main__":
    main()
