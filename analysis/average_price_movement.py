import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_prices(data_dir: Path) -> pd.DataFrame:
    day_m1 = pd.read_csv(data_dir / "prices_round_0_day_-1.csv", sep=";")
    day_m2 = pd.read_csv(data_dir / "prices_round_0_day_-2.csv", sep=";")
    return pd.concat([day_m1, day_m2], ignore_index=True)


def build_profiles(df: pd.DataFrame):
    # Average mid-price per product and timestamp across days.
    avg_profile = (
        df.groupby(["product", "timestamp"], as_index=False)["mid_price"]
        .mean()
        .sort_values(["product", "timestamp"])
    )

    # Normalized movement index per product (start = 100).
    normalized = []
    for product, grp in avg_profile.groupby("product"):
        grp = grp.copy()
        start = grp["mid_price"].iloc[0]
        grp["index_100"] = 100.0 * grp["mid_price"] / start
        grp["delta_from_start"] = grp["mid_price"] - start
        normalized.append(grp)

    normalized_df = pd.concat(normalized, ignore_index=True)
    return avg_profile, normalized_df


def summarize_trend(normalized_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product, grp in normalized_df.groupby("product"):
        grp = grp.sort_values("timestamp").copy()

        total_move = grp["mid_price"].iloc[-1] - grp["mid_price"].iloc[0]
        pct_move = (grp["index_100"].iloc[-1] - 100.0)
        volatility = grp["mid_price"].std()

        # Segment the day into 5 equal time blocks.
        t_min, t_max = grp["timestamp"].min(), grp["timestamp"].max()
        bins = np.linspace(t_min, t_max + 1, 6)
        grp["segment"] = pd.cut(grp["timestamp"], bins=bins, labels=False, include_lowest=True)
        seg = grp.groupby("segment")["mid_price"].agg(["first", "last"]).reset_index()
        seg["move"] = seg["last"] - seg["first"]

        rows.append(
            {
                "product": product,
                "start_price": grp["mid_price"].iloc[0],
                "end_price": grp["mid_price"].iloc[-1],
                "total_move": total_move,
                "pct_move_from_start": pct_move,
                "std": volatility,
                "segment_moves": ", ".join([f"S{int(r.segment)}:{r.move:.2f}" for r in seg.itertuples()]),
            }
        )

    return pd.DataFrame(rows)


def plot_profiles(avg_profile: pd.DataFrame, normalized_df: pd.DataFrame, output_png: Path):
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    for product, grp in avg_profile.groupby("product"):
        axes[0].plot(grp["timestamp"], grp["mid_price"], label=product, linewidth=1.8)

    axes[0].set_title("Average Mid-Price Movement by Timestamp (Across Days -1 and -2)")
    axes[0].set_ylabel("Mid Price")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    for product, grp in normalized_df.groupby("product"):
        axes[1].plot(grp["timestamp"], grp["index_100"], label=product, linewidth=1.8)

    axes[1].set_title("Normalized Price Index (Start = 100)")
    axes[1].set_xlabel("Timestamp")
    axes[1].set_ylabel("Index")
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_png, dpi=150)
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    out_dir = root / "analysis"

    df = load_prices(data_dir)
    avg_profile, normalized_df = build_profiles(df)
    trend_summary = summarize_trend(normalized_df)

    avg_profile.to_csv(out_dir / "average_price_profile.csv", index=False)
    normalized_df.to_csv(out_dir / "average_price_profile_normalized.csv", index=False)
    trend_summary.to_csv(out_dir / "average_price_trend_summary.csv", index=False)

    plot_profiles(avg_profile, normalized_df, out_dir / "average_price_movement.png")

    print("Saved:")
    print(out_dir / "average_price_movement.png")
    print(out_dir / "average_price_profile.csv")
    print(out_dir / "average_price_profile_normalized.csv")
    print(out_dir / "average_price_trend_summary.csv")
    print("\nTrend Summary:")
    print(trend_summary.to_string(index=False))


if __name__ == "__main__":
    main()
