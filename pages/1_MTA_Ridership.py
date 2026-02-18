import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="MTA Ridership", layout="wide")
st.title("📊 MTA Daily Ridership Analysis")


@st.cache_data(ttl=3600)
def load_mta_data():
    """Load MTA Daily Ridership data from NYC Open Data API."""
    url = "https://data.ny.gov/resource/vxuj-8kew.json"
    all_data = []
    offset = 0
    limit = 50000
    while True:
        params = {"$limit": limit, "$offset": offset, "$order": "date"}
        response = requests.get(url, params=params)
        data = response.json()
        if not data:
            break
        all_data.extend(data)
        offset += limit
    df = pd.DataFrame(all_data)
    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = [
        "subways_total_estimated_ridership",
        "subways_pct_of_comparable_pre_pandemic_day",
        "buses_total_estimated_ridership",
        "buses_pct_of_comparable_pre_pandemic_day",
        "lirr_total_estimated_ridership",
        "lirr_pct_of_comparable_pre_pandemic_day",
        "metro_north_total_estimated_ridership",
        "metro_north_pct_of_comparable_pre_pandemic_day",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


df = load_mta_data()

st.write(
    f"Data loaded: {len(df)} rows, from {df['date'].min().date()} to {df['date'].max().date()}"
)

# --- Visualization 1: Ridership over time ---
st.subheader("Daily Ridership Over Time")

services = {
    "Subways": "subways_total_estimated_ridership",
    "Buses": "buses_total_estimated_ridership",
    "LIRR": "lirr_total_estimated_ridership",
    "Metro-North": "metro_north_total_estimated_ridership",
}

selected = st.multiselect(
    "Select services:", list(services.keys()), default=["Subways"]
)

if selected:
    fig_data = df[["date"]].copy()
    for s in selected:
        fig_data[s] = df[services[s]]

    melted = fig_data.melt(id_vars="date", var_name="Service", value_name="Ridership")
    fig = px.line(
        melted,
        x="date",
        y="Ridership",
        color="Service",
        title="MTA Daily Ridership by Service",
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Estimated Ridership")
    st.plotly_chart(fig, use_container_width=True)

# --- Visualization 2: Recovery percentage ---
st.subheader("Recovery Rate (% of Pre-Pandemic Levels)")

recovery_cols = {
    "Subways": "subways_pct_of_comparable_pre_pandemic_day",
    "Buses": "buses_pct_of_comparable_pre_pandemic_day",
    "LIRR": "lirr_pct_of_comparable_pre_pandemic_day",
    "Metro-North": "metro_north_pct_of_comparable_pre_pandemic_day",
}

recovery_data = df[["date"]].copy()
for name, col in recovery_cols.items():
    if col in df.columns:
        recovery_data[name] = df[col] * 100

melted_recovery = recovery_data.melt(
    id_vars="date", var_name="Service", value_name="% of Pre-Pandemic"
)
fig2 = px.line(
    melted_recovery,
    x="date",
    y="% of Pre-Pandemic",
    color="Service",
    title="Ridership Recovery: % of Comparable Pre-Pandemic Day",
)
fig2.add_hline(
    y=100,
    line_dash="dash",
    line_color="gray",
    annotation_text="Pre-Pandemic Level",
)
fig2.update_layout(xaxis_title="Date", yaxis_title="% of Pre-Pandemic")
st.plotly_chart(fig2, use_container_width=True)

# --- Weekday vs Weekend ---
st.subheader("Weekday vs. Weekend Ridership")
df["day_of_week"] = df["date"].dt.day_name()
df["is_weekend"] = df["date"].dt.dayofweek >= 5

weekend_avg = (
    df.groupby("is_weekend")["subways_total_estimated_ridership"].mean().reset_index()
)
weekend_avg["Type"] = weekend_avg["is_weekend"].map({True: "Weekend", False: "Weekday"})
fig3 = px.bar(
    weekend_avg,
    x="Type",
    y="subways_total_estimated_ridership",
    title="Average Subway Ridership: Weekday vs Weekend",
)
fig3.update_layout(yaxis_title="Average Estimated Ridership")
st.plotly_chart(fig3, use_container_width=True)
