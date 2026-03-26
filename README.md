# MTA Ridership Project

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/advanced-computing/bouncing-penguin/blob/main/mta_ridership_project.ipynb)

## Team Members

- Haixin Liu
- Hanghai Li

## Project Description

This project analyzes MTA Daily Ridership Data to examine COVID-19 recovery patterns across different transit modes in New York City. We explore how subway, bus, and commuter rail ridership has changed over time and compare the recovery rates of different transportation methods.

## Research Questions

1. How has MTA ridership recovered since COVID-19 across different transit modes?
2. Which transit modes have recovered faster - subway, bus, or commuter rail?
3. Are there seasonal patterns in the ridership recovery?

## Dataset

- **Source:** [MTA Daily Ridership Data](https://data.ny.gov/Transportation/MTA-Daily-Ridership-Data-Beginning-2020/vxuj-8kew)
- **Updated:** Daily

## Setup

### 1. Clone and install

```bash
git clone https://github.com/advanced-computing/bouncing-penguin.git
cd bouncing-penguin
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure BigQuery credentials

The app reads MTA data from BigQuery. You need a service account key to connect.

1. Get the service account key JSON for `streamlit@sipa-adv-c-bouncing-penguin.iam.gserviceaccount.com` from your team or GCP Console (IAM & Admin > Service Accounts > Keys).
2. Create the secrets file:

```bash
mkdir -p .streamlit
```

3. Create `.streamlit/secrets.toml` with the following structure, filling in values from the JSON key:

```toml
[gcp_service_account]
type = "service_account"
project_id = "sipa-adv-c-bouncing-penguin"
private_key_id = "<from JSON>"
client_email = "streamlit@sipa-adv-c-bouncing-penguin.iam.gserviceaccount.com"
client_id = "<from JSON>"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
private_key = "<from JSON>"
```

### 3. Load data into BigQuery (optional)

If the BigQuery table doesn't exist yet, run the data loading script:

```bash
python load_data_to_bq.py
```

This fetches MTA ridership data from the NYC Open Data API and uploads it to BigQuery. You will be prompted to authenticate with your Google account.

### 4. Run the app

```bash
streamlit run streamlit_app.py
```

The app will open at `http://localhost:8501`.

## Live App

[bouncing-penguin-forever.streamlit.app](https://bouncing-penguin-forever.streamlit.app)

## Usage

- **Dashboard tab**: Interactive visualizations of MTA ridership recovery trends, weekday vs weekend comparisons, holiday impacts, and year-over-year analysis.
- **Proposal tab**: Project background, research questions, methodology, and preliminary findings.
- **MTA Ridership page**: Simplified ridership charts.
- **Second Dataset page**: NYC COVID-19 case data for context.
