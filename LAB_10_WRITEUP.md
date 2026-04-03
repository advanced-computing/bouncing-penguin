# Lab 10 Writeup

## BigQuery Data Loading

This project now uses BigQuery for every dataset shown in the Streamlit app.

### Dataset 1: MTA Daily Ridership

- Source: `https://data.ny.gov/resource/vxuj-8kew`
- BigQuery table: `sipa-adv-c-bouncing-penguin.mta_data.daily_ridership`
- Loading type: batch full refresh
- Why: the dataset is small, updated on a daily cadence, and easy to keep consistent by reloading the full table instead of managing row-by-row updates.

### Dataset 2: NYC COVID-19 Daily Cases

- Source: `https://data.cityofnewyork.us/resource/rc75-m7u3`
- BigQuery table: `sipa-adv-c-bouncing-penguin.mta_data.nyc_covid_cases`
- Loading type: batch full refresh
- Why: this table is also small enough for a daily refresh, and full replacement keeps the historical series in sync without extra incremental-loading logic.

### Loader Script

The repository includes `load_data_to_bq.py`, which:

1. Authenticates with Google BigQuery
2. Creates the `mta_data` dataset if it does not already exist
3. Pulls source data from both Open Data APIs
4. Cleans date and numeric fields before upload
5. Replaces the target BigQuery tables
6. Verifies each upload with row counts and date ranges

Run it with:

```bash
python load_data_to_bq.py --dataset all
```

You can also load a single table:

```bash
python load_data_to_bq.py --dataset mta
python load_data_to_bq.py --dataset covid
```

## App Changes for BigQuery

The Streamlit app no longer reads API responses directly inside page files.

- `utils.py` now provides shared BigQuery helpers for both datasets
- `streamlit_app.py` reads MTA data from BigQuery
- `pages/1_MTA_Ridership.py` reads MTA data from BigQuery
- `pages/2_Second_Dataset.py` reads COVID data from BigQuery

This keeps all pages aligned with the lab requirement that every dataset come from BigQuery.

## Performance Work

To improve load time and make performance visible:

- Each page uses a custom `display_load_time()` context manager and shows total load time in the UI
- BigQuery results are cached with Streamlit caching
- Queries select only the columns used by the app instead of `SELECT *`
- Repeated client setup is cached with a shared BigQuery client helper
- Basic data cleaning is centralized in `utils.py` so pages do less work on every rerun
- The homepage dashboard is split into lighter sections so each view renders only the charts needed for that section
- Default chart selections were reduced to fewer transit modes so the initial render sends fewer Plotly traces

These changes improve both initial and subsequent page loads, while keeping the code easier to maintain.

## Local Verification Steps

1. Run `python load_data_to_bq.py --dataset all`
2. Run `streamlit run streamlit_app.py`
3. Open each page and confirm the caption shows the page load time
4. Record the screen while loading the main page and both sub-pages

## Assumption

I interpreted "repeat the middle steps from Part 5" as: load the datasets into BigQuery, point the app at BigQuery tables, and document the table-level setup in the repository.
