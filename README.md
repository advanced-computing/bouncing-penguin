# MTA Ridership Project

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/advanced-computing/bouncing-penguin/blob/main/mta_ridership_project.ipynb)

## Team Members

- Haixin Liu
- Hanghai Li

## Project Overview

This project analyzes MTA daily ridership trends in New York City to understand how different transit services have recovered since COVID-19. Our Streamlit dashboard compares subway, bus, LIRR, and Metro-North ridership over time and uses NYC COVID-19 case data as additional context.

## Research Questions

1. How have different MTA services recovered since COVID-19?
2. How do weekday and weekend ridership patterns differ?
3. How do changes in COVID-19 cases relate to changes in transit ridership?

## Data Sources

- **MTA Daily Ridership Data**  
  https://data.ny.gov/Transportation/MTA-Daily-Ridership-Data-Beginning-2020/vxuj-8kew

- **NYC COVID-19 Daily Cases**  
  https://data.cityofnewyork.us/Health/Coronavirus-Data/rc75-m7u3

Both datasets are loaded into BigQuery for the Streamlit app:

- `sipa-adv-c-bouncing-penguin.mta_data.daily_ridership`
- `sipa-adv-c-bouncing-penguin.mta_data.nyc_covid_cases`

## Repository Structure

- `streamlit_app.py` - homepage and project introduction
- `pages/1_MTA_Ridership.py` - main MTA ridership analysis
- `pages/2_Second_Dataset.py` - NYC COVID-19 context page
- `utils.py` - helper functions for cleaning and plotting
- `validation.py` - Pandera schema validation
- `tests/` - unit tests for utility and validation code
- `load_data_to_bq.py` - script for loading both datasets into BigQuery
- `.github/workflows/refresh-data.yml` - daily automated BigQuery refresh
- `LAB_10_WRITEUP.md` - Lab 10 notes on data loading and performance

## Setup

1. Clone this repository: `git clone https://github.com/advanced-computing/bouncing-penguin.git`
2. Create virtual environment: `python -m venv .venv`
3. Activate virtual environment:
   - Mac/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Load the BigQuery tables: `python load_data_to_bq.py --dataset all`

## Usage

Run the Streamlit app locally:

```bash
streamlit run streamlit_app.py
```

You can still open `mta_ridership_project.ipynb` in Jupyter Notebook or VS Code for notebook-based exploration.

## Automation

The BigQuery tables are refreshed daily by GitHub Actions
([`.github/workflows/refresh-data.yml`](./.github/workflows/refresh-data.yml)).
The workflow runs at 12:00 UTC every day and can also be triggered manually
from the **Actions** tab via *Run workflow*.

To enable the workflow on a fresh fork:

1. Create a Google Cloud service account with BigQuery Data Editor + BigQuery Job User on the
   `sipa-adv-c-bouncing-penguin` project, and download its JSON key.
2. In the GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Name the secret `GCP_SA_KEY` and paste the entire contents of the JSON key file as the value.
4. Trigger the workflow once via *Run workflow* to confirm it succeeds. Subsequent runs happen
   automatically every day.

The Streamlit dashboard caches BigQuery results for one hour (`ttl=3600`), so updates from
the workflow surface in the deployed app within an hour of completion. The dashboard also
shows a "Data current as of" banner at the top so you can see at a glance how fresh the data is.

## Lab 10

Lab 10 documentation lives in [LAB_10_WRITEUP.md](./LAB_10_WRITEUP.md).
