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

## Repository Structure

- `streamlit_app.py` - homepage and project introduction
- `pages/1_MTA_Ridership.py` - main MTA ridership analysis
- `pages/2_Second_Dataset.py` - NYC COVID-19 context page
- `utils.py` - helper functions for cleaning and plotting
- `validation.py` - Pandera schema validation
- `tests/` - unit tests for utility and validation code
- `load_data_to_bq.py` - script for loading data into BigQuery

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/advanced-computing/bouncing-penguin.git
cd bouncing-penguin
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

Mac/Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the Streamlit App

From the project directory, run:

```bash
python -m streamlit run streamlit_app.py
```

Streamlit should print a local URL in the terminal, usually:

```text
http://localhost:8501
```

Open that URL in your browser.

## Run Tests

To run the unit tests:

```bash
python -m pytest -p no:cacheprovider
```

## App Pages

### Home Page

The homepage introduces the project, the team, and the main research questions.

### MTA Ridership Page

This page shows:

- daily ridership over time for selected transit services
- recovery rates compared with pre-pandemic levels
- average weekday versus weekend subway ridership

### Second Dataset Page

This page shows NYC COVID-19 daily case counts and helps provide context for major ridership drops and recovery periods.

## Optional: Load Data to BigQuery

The repository also includes a script for loading the MTA ridership dataset into BigQuery:

```bash
python load_data_to_bq.py
```

This script:

- authenticates with your Google account
- downloads MTA ridership data from the NYC Open Data API
- uploads the data to the BigQuery table
- runs a verification query after upload

Before using it, make sure your environment includes the required Google and BigQuery dependencies from `requirements.txt`, and be prepared to complete the browser-based Google login flow.

## Notes

- The app pulls live data from public APIs, so internet access is required.
- If a dependency is missing, rerun:

```bash
python -m pip install -r requirements.txt
```

- If your environment is broken, recreate it:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

- Streamlit secrets are ignored through `.streamlit/secrets.toml`, so local credentials should not be committed.

## Project Goal

Our goal is to make it easier to explore how public transit usage in New York changed after COVID-19 and how recovery differs across transit modes. We want users to compare trends visually and better understand how public health conditions affected ridership behavior.
