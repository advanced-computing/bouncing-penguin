import streamlit as st

st.set_page_config(page_title="MTA Ridership Dashboard", layout="wide")

st.title("🚇 MTA Ridership Recovery Dashboard")
st.markdown("""
This dashboard explores MTA ridership trends and COVID-19 recovery patterns 
across different transit services in New York City.
""")

st.subheader("Research Questions")
st.markdown("""
1. How do weekday vs. weekend travel patterns differ across MTA services?
2. How have holidays impacted ridership?
3. What are the recovery rates across different MTA services since COVID-19?
""")

st.markdown("---")
st.markdown("**Team bouncing-penguin:** Haixin & Hanghai Li")
