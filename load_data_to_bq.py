"""Load project datasets from NYC Open Data into BigQuery."""

import argparse
from dataclasses import dataclass
import sys

import pandas as pd
import pandas_gbq
import pydata_google_auth
import requests
from google.cloud import bigquery

PROJECT_ID = "sipa-adv-c-bouncing-penguin"
DATASET_ID = "mta_data"

SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
]


@dataclass(frozen=True)
class DataSource:
    name: str
    api_url: str
    destination_table: str
    order_column: str
    date_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]


DATA_SOURCES = {
    "mta": DataSource(
        name="MTA ridership",
        api_url="https://data.ny.gov/resource/vxuj-8kew.json",
        destination_table=f"{DATASET_ID}.daily_ridership",
        order_column="date",
        date_columns=("date",),
        numeric_columns=(
            "subways_total_estimated_ridership",
            "subways_pct_of_comparable_pre_pandemic_day",
            "buses_total_estimated_ridership",
            "buses_pct_of_comparable_pre_pandemic_day",
            "lirr_total_estimated_ridership",
            "lirr_pct_of_comparable_pre_pandemic_day",
            "metro_north_total_estimated_ridership",
            "metro_north_pct_of_comparable_pre_pandemic_day",
            "access_a_ride_total_scheduled_trips",
            "access_a_ride_pct_of_comparable_pre_pandemic_day",
            "bridges_and_tunnels_total_traffic",
            "bridges_and_tunnels_pct_of_comparable_pre_pandemic_day",
            "staten_island_railway_total_estimated_ridership",
            "staten_island_railway_pct_of_comparable_pre_pandemic_day",
        ),
    ),
    "covid": DataSource(
        name="NYC COVID cases",
        api_url="https://data.cityofnewyork.us/resource/rc75-m7u3.json",
        destination_table=f"{DATASET_ID}.nyc_covid_cases",
        order_column="date_of_interest",
        date_columns=("date_of_interest",),
        numeric_columns=(
            "case_count",
            "probable_case_count",
            "hospitalized_count",
            "death_count",
            "probable_death_count",
            "bx_case_count",
            "bk_case_count",
            "mn_case_count",
            "qn_case_count",
            "si_case_count",
        ),
    ),
}

MTA_RENAME_MAP = {
    "subways_of_comparable_pre_pandemic_day": "subways_pct_of_comparable_pre_pandemic_day",
    "buses_of_comparable_pre_pandemic_day": "buses_pct_of_comparable_pre_pandemic_day",
    "lirr_of_comparable_pre_pandemic_day": "lirr_pct_of_comparable_pre_pandemic_day",
    "metro_north_of_comparable_pre_pandemic_day": "metro_north_pct_of_comparable_pre_pandemic_day",
    "bridges_and_tunnels_of_comparable_pre_pandemic_day": "bridges_and_tunnels_pct_of_comparable_pre_pandemic_day",
    "access_a_ride_of_comparable_pre_pandemic_day": "access_a_ride_pct_of_comparable_pre_pandemic_day",
    "staten_island_railway_of_comparable_pre_pandemic_day": "staten_island_railway_pct_of_comparable_pre_pandemic_day",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load project datasets from NYC Open Data into BigQuery."
    )
    parser.add_argument(
        "--dataset",
        choices=("all", "mta", "covid"),
        default="all",
        help="Which dataset to load. Defaults to all.",
    )
    return parser.parse_args()


def get_credentials():
    """Get Google credentials with browser-based auth flow."""
    print("Authenticating with Google... A browser window should open.")
    print("If it doesn't, copy the URL shown below and open it manually.")
    credentials = pydata_google_auth.get_user_credentials(
        SCOPES,
        auth_local_webserver=False,
    )
    print("Authentication successful!")
    return credentials


def ensure_dataset_exists(credentials) -> None:
    """Create the BigQuery dataset if it does not already exist."""
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
    dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)


def fetch_source(source: DataSource) -> pd.DataFrame:
    """Pull a dataset from an NYC Open Data endpoint."""
    print(f"Fetching {source.name} from {source.api_url} ...")
    sys.stdout.flush()
    response = requests.get(
        source.api_url,
        params={"$limit": 50000, "$order": source.order_column},
        timeout=60,
    )
    response.raise_for_status()

    df = pd.DataFrame(response.json())
    if df.empty:
        raise RuntimeError(f"{source.name} returned no rows.")

    if source.destination_table.endswith("daily_ridership"):
        df = df.rename(columns=MTA_RENAME_MAP)

    for column in source.date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column])

    for column in source.numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    date_column = source.date_columns[0]
    print(
        "Fetched "
        f"{len(df)} rows "
        f"({df[date_column].min().date()} to {df[date_column].max().date()})"
    )
    return df


def upload_source(df: pd.DataFrame, source: DataSource, credentials) -> None:
    """Upload a dataframe into its destination BigQuery table."""
    print(f"Uploading to BigQuery: {PROJECT_ID}.{source.destination_table} ...")
    sys.stdout.flush()
    pandas_gbq.to_gbq(
        df,
        destination_table=source.destination_table,
        project_id=PROJECT_ID,
        if_exists="replace",
        credentials=credentials,
    )
    print("Upload complete.")


def verify_source(source: DataSource, credentials) -> None:
    """Print a quick verification summary for the target table."""
    date_column = source.date_columns[0]
    query = f"""
        SELECT
            COUNT(*) AS row_count,
            MIN(`{date_column}`) AS min_date,
            MAX(`{date_column}`) AS max_date
        FROM `{PROJECT_ID}.{source.destination_table}`
    """
    result = pandas_gbq.read_gbq(
        query,
        project_id=PROJECT_ID,
        credentials=credentials,
    )
    row = result.iloc[0]
    print(
        "Verification: "
        f"{row['row_count']} rows "
        f"({pd.Timestamp(row['min_date']).date()} to {pd.Timestamp(row['max_date']).date()})"
    )


def main() -> None:
    args = parse_args()
    selected_keys = list(DATA_SOURCES) if args.dataset == "all" else [args.dataset]

    credentials = get_credentials()
    ensure_dataset_exists(credentials)

    for key in selected_keys:
        source = DATA_SOURCES[key]
        df = fetch_source(source)
        upload_source(df, source, credentials)
        verify_source(source, credentials)
        print("")

    print("Done! BigQuery tables are ready for the Streamlit app.")


if __name__ == "__main__":
    main()
