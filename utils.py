from contextlib import contextmanager
from datetime import date
import time
from typing import Iterable

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "sipa-adv-c-bouncing-penguin"
MTA_TABLE = "mta_data.daily_ridership"
COVID_TABLE = "mta_data.nyc_covid_cases"
MTA_MIN_DATE = date(2020, 3, 1)
COVID_MIN_DATE = date(2020, 3, 1)

MTA_COLUMNS = (
    "date",
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
)

COVID_COLUMNS = (
    "date_of_interest",
    "case_count",
)

MTA_LEGACY_COLUMN_MAP = {
    "subways_pct_of_comparable_pre_pandemic_day": "subways_of_comparable_pre_pandemic_day",
    "buses_pct_of_comparable_pre_pandemic_day": "buses_of_comparable_pre_pandemic_day",
    "lirr_pct_of_comparable_pre_pandemic_day": "lirr_of_comparable_pre_pandemic_day",
    "metro_north_pct_of_comparable_pre_pandemic_day": "metro_north_of_comparable_pre_pandemic_day",
    "bridges_and_tunnels_pct_of_comparable_pre_pandemic_day": "bridges_and_tunnels_of_comparable_pre_pandemic_day",
    "access_a_ride_pct_of_comparable_pre_pandemic_day": "access_a_ride_of_comparable_pre_pandemic_day",
    "staten_island_railway_pct_of_comparable_pre_pandemic_day": "staten_island_railway_of_comparable_pre_pandemic_day",
}


@st.cache_resource(show_spinner=False)
def get_bigquery_client() -> bigquery.Client:
    """Create and cache the BigQuery client used by the app."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        return bigquery.Client(credentials=credentials, project=PROJECT_ID)
    except Exception:
        # Fallback: use default credentials (e.g. local gcloud auth)
        return bigquery.Client(project=PROJECT_ID)


def _render_select_clause(columns: Iterable[str]) -> str:
    return ", ".join(f"`{column}`" for column in columns)


@st.cache_data(show_spinner=False, persist="disk", ttl=60 * 60 * 12)
def _get_table_columns(table_name: str) -> set[str]:
    client = get_bigquery_client()
    table = client.get_table(f"{PROJECT_ID}.{table_name}")
    return {field.name for field in table.schema}


def _resolve_mta_columns(columns: Iterable[str]) -> list[str]:
    available_columns = _get_table_columns(MTA_TABLE)
    resolved_columns = []

    for column in columns:
        if column in available_columns:
            resolved_columns.append(f"`{column}`")
            continue

        legacy_column = MTA_LEGACY_COLUMN_MAP.get(column)
        if legacy_column and legacy_column in available_columns:
            resolved_columns.append(f"`{legacy_column}` AS `{column}`")
            continue

    return resolved_columns


def _get_source_column(
    table_name: str,
    output_column: str,
    available_columns: set[str],
) -> str | None:
    if output_column in available_columns:
        return output_column

    if table_name == MTA_TABLE:
        legacy_column = MTA_LEGACY_COLUMN_MAP.get(output_column)
        if legacy_column in available_columns:
            return legacy_column

    return None


def _build_select_expressions(
    table_name: str,
    requested_columns: Iterable[str],
) -> tuple[list[str], str]:
    available_columns = _get_table_columns(table_name)
    date_column = "date" if table_name == MTA_TABLE else "date_of_interest"
    expressions = []

    for output_column in requested_columns:
        source_column = _get_source_column(table_name, output_column, available_columns)
        if not source_column:
            continue

        if output_column == date_column:
            expressions.append(
                f"SAFE_CAST(`{source_column}` AS DATE) AS `{output_column}`"
            )
        else:
            expressions.append(
                f"SAFE_CAST(`{source_column}` AS FLOAT64) AS `{output_column}`"
            )

    return expressions, date_column


def _load_table(
    table_name: str,
    columns: Iterable[str],
    order_by: str,
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int | None = None,
) -> pd.DataFrame:
    select_expressions, date_column = _build_select_expressions(table_name, columns)
    if not select_expressions:
        raise KeyError(f"No requested columns were found in BigQuery table {table_name}.")

    where_clause = ""
    order_clause = f"ORDER BY `{order_by}`"
    limit_clause = ""
    if lookback_days is not None:
        order_clause = f"ORDER BY `{date_column}` DESC"
        limit_clause = f"LIMIT {lookback_days + 1}"
    elif start_date and end_date:
        where_clause = (
            f"\n        WHERE `{date_column}` BETWEEN '{start_date}' AND '{end_date}'"
        )

    query = f"""
        WITH normalized AS (
            SELECT
                {", ".join(select_expressions)}
            FROM `{PROJECT_ID}.{table_name}`
        )
        SELECT *
        FROM normalized
        {where_clause}
        {order_clause}
        {limit_clause}
    """
    client = get_bigquery_client()
    job_config = bigquery.QueryJobConfig(use_query_cache=True)
    query_job = client.query(query, job_config=job_config)
    return query_job.to_dataframe(create_bqstorage_client=False)


@st.cache_data(show_spinner=False, persist="disk")
def load_mta_data(
    columns: tuple[str, ...] = MTA_COLUMNS,
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int | None = None,
) -> pd.DataFrame:
    """Load MTA ridership data from BigQuery."""
    df = _load_table(
        MTA_TABLE,
        columns,
        order_by="date",
        start_date=start_date,
        end_date=end_date,
        lookback_days=lookback_days,
    )
    return clean_mta_df(df)


def clean_covid_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "date_of_interest" not in out.columns:
        raise KeyError("Missing 'date_of_interest' column")

    out["date_of_interest"] = pd.to_datetime(out["date_of_interest"])
    out = out.sort_values("date_of_interest").reset_index(drop=True)

    if "case_count" in out.columns:
        out["case_count"] = pd.to_numeric(out["case_count"], errors="coerce")

    out["year"] = out["date_of_interest"].dt.year
    out["month"] = out["date_of_interest"].dt.month
    out["year_month"] = out["date_of_interest"].dt.to_period("M").astype(str)

    return out


@st.cache_data(show_spinner=False, persist="disk")
def load_covid_data(
    columns: tuple[str, ...] = COVID_COLUMNS,
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int | None = None,
) -> pd.DataFrame:
    """Load NYC COVID case data from BigQuery."""
    df = _load_table(
        COVID_TABLE,
        columns,
        order_by="date_of_interest",
        start_date=start_date,
        end_date=end_date,
        lookback_days=lookback_days,
    )
    return clean_covid_df(df)


@contextmanager
def display_load_time():
    """Display total Streamlit page load time in the footer."""
    start_time = time.perf_counter()

    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        st.caption(f"Page loaded in {elapsed:.2f} seconds")


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


def plot_ridership_recovery(df: pd.DataFrame):
    """Plot MTA ridership recovery by transit mode as % of pre-pandemic levels."""
    import matplotlib.pyplot as plt

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
