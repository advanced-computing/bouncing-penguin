import matplotlib.pyplot as plt
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "sipa-adv-c-bouncing-penguin"
DATASET_TABLE = "mta_data.daily_ridership"


def load_mta_data() -> pd.DataFrame:
    """Load MTA ridership data from BigQuery."""
    try:
        import streamlit as st

        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
    except Exception:
        # Fallback: use default credentials (e.g. local gcloud auth)
        client = bigquery.Client(project=PROJECT_ID)

    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_TABLE}`"
    df = client.query(query).to_dataframe()
    df = clean_mta_df(df)
    return df


def clean_mta_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "date" not in out.columns:
        raise KeyError("Missing 'date' column")

    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    # Normalize column names: API may return _of_ format,
    # we standardize to _pct_of_ to match our tests and code
    rename_map = {}
    for col in out.columns:
        if "_of_comparable_pre_pandemic_day" in col and "_pct_of_" not in col:
            new_col = col.replace(
                "_of_comparable_pre_pandemic_day",
                "_pct_of_comparable_pre_pandemic_day",
            )
            rename_map[col] = new_col
    if rename_map:
        out = out.rename(columns=rename_map)

    # Make sure numeric columns are actually numeric
    numeric_cols = [
        "subways_total_estimated_ridership",
        "subways_pct_of_comparable_pre_pandemic_day",
        "buses_total_estimated_ridership",
        "buses_pct_of_comparable_pre_pandemic_day",
        "lirr_total_estimated_ridership",
        "lirr_pct_of_comparable_pre_pandemic_day",
        "metro_north_total_estimated_ridership",
        "metro_north_pct_of_comparable_pre_pandemic_day",
        "bridges_and_tunnels_total_traffic",
        "bridges_and_tunnels_pct_of_comparable_pre_pandemic_day",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Add useful time columns
    out["day_of_week"] = out["date"].dt.dayofweek
    out["day_name"] = out["date"].dt.day_name()
    out["is_weekend"] = out["day_of_week"] >= 5
    out["year"] = out["date"].dt.year
    out["month"] = out["date"].dt.month
    out["year_month"] = out["date"].dt.to_period("M").astype(str)

    return out


# Mapping from friendly names to column names
TRANSIT_MODES = {
    "Subway": {
        "ridership": "subways_total_estimated_ridership",
        "recovery": "subways_pct_of_comparable_pre_pandemic_day",
    },
    "Bus": {
        "ridership": "buses_total_estimated_ridership",
        "recovery": "buses_pct_of_comparable_pre_pandemic_day",
    },
    "LIRR": {
        "ridership": "lirr_total_estimated_ridership",
        "recovery": "lirr_pct_of_comparable_pre_pandemic_day",
    },
    "Metro-North": {
        "ridership": "metro_north_total_estimated_ridership",
        "recovery": "metro_north_pct_of_comparable_pre_pandemic_day",
    },
    "Bridges & Tunnels": {
        "ridership": "bridges_and_tunnels_total_traffic",
        "recovery": "bridges_and_tunnels_pct_of_comparable_pre_pandemic_day",
    },
}


# US federal holidays and NYC-relevant events
HOLIDAYS = {
    "New Year's Day": [
        "2020-01-01",
        "2021-01-01",
        "2022-01-01",
        "2023-01-01",
        "2024-01-01",
        "2025-01-01",
        "2026-01-01",
    ],
    "Independence Day": [
        "2020-07-04",
        "2021-07-04",
        "2022-07-04",
        "2023-07-04",
        "2024-07-04",
        "2025-07-04",
    ],
    "Thanksgiving": [
        "2020-11-26",
        "2021-11-25",
        "2022-11-24",
        "2023-11-23",
        "2024-11-28",
        "2025-11-27",
    ],
    "Christmas": [
        "2020-12-25",
        "2021-12-25",
        "2022-12-25",
        "2023-12-25",
        "2024-12-25",
        "2025-12-25",
    ],
    "NYC Marathon": [
        "2021-11-07",
        "2022-11-06",
        "2023-11-05",
        "2024-11-03",
        "2025-11-02",
    ],
    "Congestion Pricing Launch": ["2025-01-05"],
}


def get_holiday_df() -> pd.DataFrame:
    """Return a dataframe of holiday dates and names."""
    rows = []
    for name, dates in HOLIDAYS.items():
        for d in dates:
            rows.append({"date": pd.to_datetime(d), "holiday": name})
    return pd.DataFrame(rows)


def get_latest_recovery(df: pd.DataFrame, days: int = 30) -> dict:
    """Get the average recovery rate for each transit mode over the last N days."""
    recent = df.sort_values("date").tail(days)
    result = {}
    for mode, cols in TRANSIT_MODES.items():
        col = cols["recovery"]
        if col in recent.columns:
            val = recent[col].mean()
            result[mode] = val
    return result


def get_weekday_weekend_comparison(df: pd.DataFrame, year: int = None) -> pd.DataFrame:
    """Compare weekday vs weekend recovery rates by transit mode."""
    data = df.copy()
    if year:
        data = data[data["year"] == year]

    rows = []
    for mode, cols in TRANSIT_MODES.items():
        col = cols["recovery"]
        if col not in data.columns:
            continue
        weekday_avg = data[~data["is_weekend"]][col].mean()
        weekend_avg = data[data["is_weekend"]][col].mean()
        rows.append(
            {
                "Transit Mode": mode,
                "Weekday Avg Recovery": weekday_avg,
                "Weekend Avg Recovery": weekend_avg,
                "Gap (Weekend - Weekday)": weekend_avg - weekday_avg,
            }
        )
    return pd.DataFrame(rows)


def plot_ridership_recovery(df: pd.DataFrame) -> plt.Figure:
    """Plot MTA ridership recovery by transit mode as % of pre-pandemic levels."""
    required_cols = [
        "date",
        "subways_pct_of_comparable_pre_pandemic_day",
        "buses_pct_of_comparable_pre_pandemic_day",
        "lirr_pct_of_comparable_pre_pandemic_day",
        "metro_north_pct_of_comparable_pre_pandemic_day",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(
        df["date"],
        df["subways_pct_of_comparable_pre_pandemic_day"],
        label="Subway",
        alpha=0.8,
        linewidth=1.2,
    )
    ax.plot(
        df["date"],
        df["buses_pct_of_comparable_pre_pandemic_day"],
        label="Bus",
        alpha=0.8,
        linewidth=1.2,
    )
    ax.plot(
        df["date"],
        df["lirr_pct_of_comparable_pre_pandemic_day"],
        label="LIRR",
        alpha=0.8,
        linewidth=1.2,
    )
    ax.plot(
        df["date"],
        df["metro_north_pct_of_comparable_pre_pandemic_day"],
        label="Metro-North",
        alpha=0.8,
        linewidth=1.2,
    )

    ax.axhline(
        y=1.0,
        color="gray",
        linestyle="--",
        linewidth=1.5,
        label="Pre-pandemic baseline (100%)",
    )

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("% of Pre-Pandemic Ridership", fontsize=12)
    ax.set_title(
        "MTA Ridership Recovery: Subway vs Bus vs Commuter Rail (2020-Present)",
        fontsize=14,
        fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.5)
    fig.tight_layout()

    return fig
