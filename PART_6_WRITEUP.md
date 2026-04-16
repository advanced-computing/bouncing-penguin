# Part 6: Scheduled ETL Workflow

## Overview

We created a GitHub Actions workflow that automatically runs our ETL pipeline on a daily schedule. This ensures our BigQuery tables always contain fresh data from the MTA ridership and NYC COVID case APIs without manual intervention.

## How It Works — Step by Step

1. **Trigger**: GitHub Actions fires the `etl.yml` workflow every day at 06:00 UTC via a cron schedule. It can also be triggered manually through the GitHub UI (`workflow_dispatch`).

2. **Environment setup**: The workflow checks out the repo, sets up Python 3.11, and installs all dependencies from `requirements.txt`.

3. **Authentication**: The script reads a GCP service account key from the `GCP_SA_KEY` GitHub Secret. This replaces the browser-based OAuth flow used in local development, allowing the pipeline to run unattended.

4. **Data fetch**: `load_data_to_bq.py` sends HTTP requests to two public APIs:
   - MTA ridership data from `data.ny.gov` (dataset `vxuj-8kew`)
   - NYC COVID case data from `data.cityofnewyork.us` (dataset `rc75-m7u3`)
   Each request pulls up to 50,000 rows sorted by date.

5. **Data cleaning**: The script renames inconsistent column names (e.g., missing `pct_` prefix in MTA data), parses date columns with `pd.to_datetime`, and coerces numeric columns with `pd.to_numeric`.

6. **Upload to BigQuery**: Cleaned DataFrames are uploaded to `mta_data.daily_ridership` and `mta_data.nyc_covid_cases` using `pandas_gbq.to_gbq` with `if_exists="replace"` (full refresh).

7. **Verification**: After each upload, the script queries BigQuery to confirm the row count and date range, printing a summary to the workflow log.

## How Will We Know If It Worked?

- **GitHub Actions tab**: Each workflow run shows a green check (success) or red X (failure). Logs contain row counts and date ranges for each table.
- **BigQuery console**: We can query the tables directly to confirm fresh data exists and the latest date matches yesterday.
- **Streamlit dashboard**: If the charts show up-to-date data, the pipeline is working.
- **Email notifications**: GitHub sends email alerts when a workflow run fails.

## Where to Look If Something Goes Wrong

| Symptom | Where to look |
|---------|--------------|
| Workflow never runs | GitHub Actions tab — check if the schedule is disabled (auto-disabled after 60 days of inactivity) |
| Authentication error | GitHub Settings > Secrets — verify `GCP_SA_KEY` is set and the service account has BigQuery permissions |
| API fetch fails | Workflow logs — look for HTTP errors; check if the API endpoint or schema changed |
| Data looks stale | BigQuery console — query `MAX(date)` to see the latest loaded date |
| Tables are empty | Workflow logs — check for upstream API returning 0 rows or a schema mismatch |

## How Is Data Collected?

Data is collected via HTTP GET requests to two NYC Open Data Socrata API endpoints. The requests include `$limit=50000` and `$order=<date_column>` parameters. The APIs return JSON arrays that are converted to pandas DataFrames. No API key is required for these public endpoints. The collection runs automatically every 24 hours via GitHub Actions.

## Potential Issues

1. **Full refresh risk**: We use `if_exists="replace"`, which means a failed fetch followed by an upload of partial data could overwrite a previously complete table. A safer approach would be to validate row counts before replacing.

2. **API rate limits / outages**: The NYC Open Data APIs are public and could rate-limit or go offline. The workflow has no retry logic — it will simply fail and alert us.

3. **Secret expiration**: GCP service account keys can expire or be rotated. If the `GCP_SA_KEY` secret becomes invalid, every run will fail until it is updated.

4. **GitHub disables inactive schedules**: If no commits are pushed for 60 days, GitHub automatically disables cron workflows. A repo maintainer must manually re-enable it.

5. **Schema drift**: If MTA or NYC Open Data changes column names or data types, the cleaning step may silently drop data or fail outright.

6. **50,000-row limit**: The `$limit=50000` parameter may become insufficient as the datasets grow, resulting in truncated data.
