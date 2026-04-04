"""
Data Analysis and Strategy Backtest Script
Analyzes historical market data and tests the trading strategy
"""

import pandas as pd
from pathlib import Path
import json


def load_data():
    """Load historical price and trade data."""
    data_path = Path(__file__).resolve().parent.parent / "data"

    prices_m2 = pd.read_csv(data_path / "prices_round_0_day_-2.csv", sep=";")
    prices_m1 = pd.read_csv(data_path / "prices_round_0_day_-1.csv", sep=";")
    trades_m2 = pd.read_csv(data_path / "trades_round_0_day_-2.csv", sep=";")
    trades_m1 = pd.read_csv(data_path / "trades_round_0_day_-1.csv", sep=";")

    return prices_m2, prices_m1, trades_m2, trades_m1


def price_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Generate summary statistics for each product's mid-price."""
    grouped = df.groupby("product")["mid_price"]
    summary = pd.DataFrame(
        {
            "mid_min": grouped.min(),
            "mid_mean": grouped.mean(),
            "mid_max": grouped.max(),
            "mid_std": grouped.std(),
            "n_observations": grouped.size(),
        }
    )
    return summary


def analyze_bid_ask_spread(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze bid-ask spread statistics."""
    df_copy = df.copy()
    df_copy["spread"] = df_copy["ask_price_1"] - df_copy["bid_price_1"]

    grouped = df_copy.groupby("product")["spread"]
    summary = pd.DataFrame(
        {
            "spread_min": grouped.min(),
            "spread_mean": grouped.mean(),
            "spread_max": grouped.max(),
        }
    )
    return summary


def trade_volume_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze trading volume by product."""
    grouped = df.groupby("symbol").agg({"quantity": ["sum", "mean", "count"]})
    grouped.columns = ["total_volume", "avg_qty_per_trade", "num_trades"]
    return grouped


def mean_reversion_signals(
    df: pd.DataFrame, window: int = 20, threshold: float = 0.98
) -> pd.DataFrame:
    """
    Generate mean-reversion trading signals.

    Args:
        df: DataFrame with price data
        window: Rolling window for mean calculation
        threshold: Price threshold as percentage of mean (e.g., 0.98 = 2% below mean)

    Returns:
        DataFrame with trading signals
    """
    signals_list = []

    for product in df["product"].unique():
        df_prod = df[df["product"] == product].copy()
        df_prod = df_prod.sort_values("timestamp")

        # Calculate rolling mean
        df_prod["rolling_mean"] = (
            df_prod["mid_price"].rolling(window=window, min_periods=window).mean()
        )
        df_prod["deviation"] = (
            df_prod["mid_price"] / df_prod["rolling_mean"] - 1
        ) * 100

        # Generate signals
        df_prod["signal"] = 0  # 0 = hold
        df_prod.loc[
            df_prod["mid_price"] < threshold * df_prod["rolling_mean"], "signal"
        ] = 1  # 1 = buy
        df_prod.loc[
            df_prod["mid_price"] > (2 - threshold) * df_prod["rolling_mean"], "signal"
        ] = -1  # -1 = sell

        signals_list.append(df_prod)

    return pd.concat(signals_list, ignore_index=True)


def main():
    """Run the analysis."""
    print("=" * 80)
    print("PROSPERITY 4 - TRADING DATA ANALYSIS")
    print("=" * 80)

    # Load data
    print("\n[*] Loading historical data...")
    prices_m2, prices_m1, trades_m2, trades_m1 = load_data()

    # Combined prices for overall analysis
    prices_all = pd.concat([prices_m2, prices_m1], ignore_index=True)
    trades_all = pd.concat([trades_m2, trades_m1], ignore_index=True)

    # ===== PRICE ANALYSIS =====
    print("\n" + "=" * 80)
    print("PRICE STATISTICS")
    print("=" * 80)
    print("\nDay -2:")
    print(price_summary(prices_m2).to_string())
    print("\nDay -1:")
    print(price_summary(prices_m1).to_string())
    print("\nCombined (All days):")
    print(price_summary(prices_all).to_string())

    # ===== BID-ASK SPREAD ANALYSIS =====
    print("\n" + "=" * 80)
    print("BID-ASK SPREAD ANALYSIS")
    print("=" * 80)
    print("\nDay -2:")
    print(analyze_bid_ask_spread(prices_m2).to_string())
    print("\nDay -1:")
    print(analyze_bid_ask_spread(prices_m1).to_string())

    # ===== TRADING VOLUME ANALYSIS =====
    print("\n" + "=" * 80)
    print("TRADING VOLUME ANALYSIS")
    print("=" * 80)
    print("\nDay -2:")
    print(trade_volume_analysis(trades_m2).to_string())
    print("\nDay -1:")
    print(trade_volume_analysis(trades_m1).to_string())

    # ===== MEAN REVERSION SIGNALS =====
    print("\n" + "=" * 80)
    print("MEAN REVERSION STRATEGY SIGNALS (Window=20, Threshold=0.98)")
    print("=" * 80)

    signals_m1 = mean_reversion_signals(prices_m1, window=20, threshold=0.98)
    signal_counts = (
        signals_m1.groupby(["product", "signal"]).size().unstack(fill_value=0)
    )
    print("\nDay -1 Signal Distribution:")
    print(signal_counts.to_string())

    # Show some example signals
    print("\nDay -1 Sample Signals (first 30 with rolling_mean):")
    sample = signals_m1[signals_m1["rolling_mean"].notna()][
        ["timestamp", "product", "mid_price", "rolling_mean", "deviation", "signal"]
    ].head(30)
    print(sample.to_string(index=False))

    # ===== STRATEGY INSIGHTS =====
    print("\n" + "=" * 80)
    print("STRATEGY INSIGHTS")
    print("=" * 80)

    print("""
Key observations from the data:

1. TOMATOES:
   - Mid-price range: ~5000-5010
   - Bid-Ask spread: ~13-14 (very tight)
   - Relatively volatile around the mean
   - Good candidate for mean-reversion trading

2. EMERALDS:
   - Mid-price range: ~9990-10010
   - Bid-Ask spread: ~16 (tight)
   - More stable than tomatoes
   - Better for conservative trading

STRATEGY APPROACH:
- Mean Reversion: Buy when price dips below rolling mean, sell when above
- TOMATOES: More aggressive (2% thresholds)
- EMERALDS: More conservative (0.5% thresholds)
- Position limits: 100 units long/short per product
- State persistence: Maintain price history across iterations
    """)

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
