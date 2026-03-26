"""Load MTA ridership data from NYC Open Data API into BigQuery."""

import sys

import pandas as pd
import pydata_google_auth

import pandas_gbq

PROJECT_ID = "sipa-adv-c-bouncing-penguin"
DATASET_TABLE = "mta_data.daily_ridership"

SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
]


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


def fetch_mta_data() -> pd.DataFrame:
    """Pull MTA ridership data from NYC Open Data API."""
    print("Fetching MTA data from NYC Open Data API...")
    sys.stdout.flush()
    url = "https://data.ny.gov/resource/vxuj-8kew.csv?$limit=50000"
    df = pd.read_csv(url)
    df["date"] = pd.to_datetime(df["date"])
    print(f"Fetched {len(df)} rows (from {df['date'].min().date()} to {df['date'].max().date()})")
    return df


def main():
    # Step 1: Authenticate
    credentials = get_credentials()

    # Step 2: Fetch data
    df = fetch_mta_data()

    # Step 3: Upload to BigQuery
    print(f"Uploading to BigQuery: {PROJECT_ID}.{DATASET_TABLE} ...")
    sys.stdout.flush()
    pandas_gbq.to_gbq(
        df,
        destination_table=DATASET_TABLE,
        project_id=PROJECT_ID,
        if_exists="replace",
        credentials=credentials,
    )
    print("Done! Data loaded to BigQuery successfully.")

    # Step 4: Verify
    query = f"SELECT COUNT(*) as row_count FROM `{PROJECT_ID}.{DATASET_TABLE}`"
    result = pandas_gbq.read_gbq(query, project_id=PROJECT_ID, credentials=credentials)
    print(f"Verification: {result['row_count'].iloc[0]} rows in BigQuery table.")


if __name__ == "__main__":
    main()
