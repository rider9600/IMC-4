"""
Strategy Backtester
Simulates the trading strategy against historical data
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import json


class SimpleBacktester:
    """Simulates strategy execution on historical data."""

    def __init__(self, starting_balance: float = 100000):
        self.starting_balance = starting_balance
        self.position = {"TOMATOES": 0, "EMERALDS": 0}
        self.balance = starting_balance
        self.trades = []
        self.position_history = []
        self.price_history = {"TOMATOES": [], "EMERALDS": []}

    def calculate_moving_average(self, prices: List[float], window: int = 20) -> float:
        """Calculate moving average of last N prices."""
        if len(prices) < window:
            return sum(prices) / len(prices) if prices else None
        return sum(prices[-window:]) / window

    def get_signal(self, product: str, current_price: float, moving_avg: float) -> int:
        """
        Generate trading signal.
        Returns: 1 (buy), -1 (sell), 0 (hold)
        """
        if moving_avg is None:
            return 0

        if product == "TOMATOES":
            buy_threshold = 0.98 * moving_avg
            sell_threshold = 1.02 * moving_avg
        else:  # EMERALDS
            buy_threshold = 0.995 * moving_avg
            sell_threshold = 1.005 * moving_avg

        if current_price < buy_threshold:
            return 1  # BUY
        elif current_price > sell_threshold:
            return -1  # SELL
        else:
            return 0  # HOLD

    def backtest_day(self, prices_df: pd.DataFrame) -> Dict:
        """Run backtest for a single day."""

        results = {
            "trades": 0,
            "profit_loss": 0,
            "final_position": {"TOMATOES": 0, "EMERALDS": 0},
            "signals": {"BUY": 0, "SELL": 0, "HOLD": 0},
        }

        # Group by product and process chronologically
        for product in ["TOMATOES", "EMERALDS"]:
            df_prod = prices_df[prices_df["product"] == product].copy()
            df_prod = df_prod.sort_values("timestamp")

            for idx, row in df_prod.iterrows():
                mid_price = row["mid_price"]

                # Update price history
                self.price_history[product].append(mid_price)
                # Keep rolling window
                if len(self.price_history[product]) > 50:
                    self.price_history[product] = self.price_history[product][-50:]

                # Calculate moving average
                moving_avg = self.calculate_moving_average(
                    self.price_history[product], window=20
                )

                # Get trading signal
                signal = self.get_signal(product, mid_price, moving_avg)

                if signal == 1:  # BUY signal
                    results["signals"]["BUY"] += 1
                    # Simplified: buy up to 10 units if room
                    if self.position[product] < 100:
                        qty = min(10, 100 - self.position[product])
                        cost = qty * mid_price
                        if self.balance >= cost:
                            self.balance -= cost
                            self.position[product] += qty
                            self.trades.append(
                                {
                                    "action": "BUY",
                                    "product": product,
                                    "price": mid_price,
                                    "qty": qty,
                                    "timestamp": row["timestamp"],
                                }
                            )
                            results["trades"] += 1

                elif signal == -1:  # SELL signal
                    results["signals"]["SELL"] += 1
                    # Simplified: sell up to 10 units if held
                    if self.position[product] > -100:
                        qty = min(10, 100 + self.position[product])
                        revenue = qty * mid_price
                        self.balance += revenue
                        self.position[product] -= qty
                        self.trades.append(
                            {
                                "action": "SELL",
                                "product": product,
                                "price": mid_price,
                                "qty": qty,
                                "timestamp": row["timestamp"],
                            }
                        )
                        results["trades"] += 1
                else:
                    results["signals"]["HOLD"] += 1

        # Record final position and P&L
        results["final_position"] = dict(self.position)

        # Simple P&L calculation (positions at last known price)
        for product, qty in self.position.items():
            last_price = (
                self.price_history[product][-1] if self.price_history[product] else 0
            )
            results["profit_loss"] += qty * last_price

        return results

    def get_summary(self) -> Dict:
        """Get backtest summary."""
        portfolio_value = self.balance
        for product, qty in self.position.items():
            if self.price_history[product]:
                last_price = self.price_history[product][-1]
                portfolio_value += qty * last_price

        return {
            "starting_balance": self.starting_balance,
            "current_balance": self.balance,
            "portfolio_value": portfolio_value,
            "total_return": portfolio_value - self.starting_balance,
            "return_pct": (
                (portfolio_value - self.starting_balance) / self.starting_balance
            )
            * 100,
            "total_trades": len(self.trades),
            "positions": self.position,
            "price_history": {
                k: {"min": min(v), "max": max(v), "last": v[-1]}
                for k, v in self.price_history.items()
            },
        }


def main():
    """Run backtesting analysis."""
    print("=" * 80)
    print("STRATEGY BACKTEST AGAINST HISTORICAL DATA")
    print("=" * 80)

    # Load data
    data_path = Path(__file__).resolve().parent.parent / "data"
    prices_m2 = pd.read_csv(data_path / "prices_round_0_day_-2.csv", sep=";")
    prices_m1 = pd.read_csv(data_path / "prices_round_0_day_-1.csv", sep=";")

    # Test Day -2
    print("\n[*] Running backtest on Day -2...")
    backtest_m2 = SimpleBacktester(starting_balance=100000)
    results_m2 = backtest_m2.backtest_day(prices_m2)
    summary_m2 = backtest_m2.get_summary()

    print("\nDay -2 Results:")
    print(f"  Trades executed: {results_m2['trades']}")
    print(f"  BUY signals: {results_m2['signals']['BUY']}")
    print(f"  SELL signals: {results_m2['signals']['SELL']}")
    print(f"  HOLD signals: {results_m2['signals']['HOLD']}")
    print(f"\nFinal Portfolio Value: ${summary_m2['portfolio_value']:,.2f}")
    print(
        f"Total Return: ${summary_m2['total_return']:,.2f} ({summary_m2['return_pct']:.2f}%)"
    )
    print(f"Final Positions: {results_m2['final_position']}")
    print(f"Price Ranges: {results_m2}")

    # Test Day -1
    print("\n" + "=" * 80)
    print("[*] Running backtest on Day -1...")
    backtest_m1 = SimpleBacktester(starting_balance=100000)
    results_m1 = backtest_m1.backtest_day(prices_m1)
    summary_m1 = backtest_m1.get_summary()

    print("\nDay -1 Results:")
    print(f"  Trades executed: {results_m1['trades']}")
    print(f"  BUY signals: {results_m1['signals']['BUY']}")
    print(f"  SELL signals: {results_m1['signals']['SELL']}")
    print(f"  HOLD signals: {results_m1['signals']['HOLD']}")
    print(f"\nFinal Portfolio Value: ${summary_m1['portfolio_value']:,.2f}")
    print(
        f"Total Return: ${summary_m1['total_return']:,.2f} ({summary_m1['return_pct']:.2f}%)"
    )
    print(f"Final Positions: {results_m1['final_position']}")
    print(f"Price Ranges: {results_m1}")

    # Combined analysis
    print("\n" + "=" * 80)
    print("COMBINED 2-DAY BACKTEST")
    print("=" * 80)
    combined_return = summary_m2["total_return"] + summary_m1["total_return"]
    combined_trades = results_m2["trades"] + results_m1["trades"]
    total_portfolio = (
        summary_m2["portfolio_value"] + summary_m1["portfolio_value"] - 100000
    )

    print(f"\nTotal Trades (both days): {combined_trades}")
    print(f"Combined P&L: ${combined_return:,.2f}")
    print(f"Total Portfolio Value: ${total_portfolio:,.2f}")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print("""
This is a SIMPLIFIED backtest that:
✓ Uses the actual historical price data
✓ Generates mean-reversion signals
✓ Simulates basic buy/sell execution
✓ Tracks positions and portfolio value

However, it DOES NOT:
✗ Match real bot order book dynamics
✗ Include bid-ask spreads (uses mid price)
✗ Simulate actual match probabilities
✗ Account for position limit rejections
✗ Track PnL accurately during position holding

Results are INDICATIVE ONLY. Actual live trading will differ based on:
- Actual order book depths and prices
- Bot behavior and order matching
- Market microstructure effects
- Actual execution prices vs mid-price

For accurate testing: Upload strategy to Prosperity platform for 1000-iteration simulation.
    """)

    print("=" * 80)
    print("Backtest complete!")


if __name__ == "__main__":
    main()
