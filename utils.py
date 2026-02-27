import pandas as pd
import matplotlib.pyplot as plt

def clean_mta_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "date" not in out.columns:
        raise KeyError("Missing 'date' column")

    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    return out

def plot_ridership_recovery(df: pd.DataFrame) -> plt.Figure:
    """Plot MTA ridership recovery by transit mode as % of pre-pandemic levels."""
    required_cols = [
        "date",
        "subways_of_comparable_pre_pandemic_day",
        "buses_of_comparable_pre_pandemic_day",
        "lirr_of_comparable_pre_pandemic_day",
        "metro_north_of_comparable_pre_pandemic_day",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(df["date"], df["subways_of_comparable_pre_pandemic_day"],
            label="Subway", alpha=0.8, linewidth=1.2)
    ax.plot(df["date"], df["buses_of_comparable_pre_pandemic_day"],
            label="Bus", alpha=0.8, linewidth=1.2)
    ax.plot(df["date"], df["lirr_of_comparable_pre_pandemic_day"],
            label="LIRR", alpha=0.8, linewidth=1.2)
    ax.plot(df["date"], df["metro_north_of_comparable_pre_pandemic_day"],
            label="Metro-North", alpha=0.8, linewidth=1.2)

    ax.axhline(y=1.0, color="gray", linestyle="--", linewidth=1.5,
               label="Pre-pandemic baseline (100%)")

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("% of Pre-Pandemic Ridership", fontsize=12)
    ax.set_title(
        "MTA Ridership Recovery: Subway vs Bus vs Commuter Rail (2020-Present)",
        fontsize=14, fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.5)
    fig.tight_layout()

    return fig
