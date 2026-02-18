import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="NYC COVID Data", layout="wide")
st.title("🦠 NYC COVID-19 Cases (Second Dataset)")

st.markdown(
    """
This page brings in NYC COVID-19 case data to contextualize MTA ridership
recovery patterns.
"""
)


@st.cache_data(ttl=3600)
def load_covid_data():
    url = "https://data.cityofnewyork.us/resource/rc75-m7u3.json"
    params = {"$limit": 50000, "$order": "date_of_interest"}
    response = requests.get(url, params=params)
    df = pd.DataFrame(response.json())
    df["date_of_interest"] = pd.to_datetime(df["date_of_interest"])
    df["case_count"] = pd.to_numeric(df["case_count"], errors="coerce")
    return df


df_covid = load_covid_data()

st.write(f"Data: {len(df_covid)} rows")

fig = px.line(
    df_covid,
    x="date_of_interest",
    y="case_count",
    title="NYC Daily COVID-19 Cases",
)
fig.update_layout(xaxis_title="Date", yaxis_title="Case Count")
st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
**Connection to MTA Ridership:** Comparing COVID case surges with ridership
dips helps us understand how public health events drive transit behavior.
"""
)
