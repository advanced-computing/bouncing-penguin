from datetime import date, timedelta

import streamlit as st

from utils import COVID_MIN_DATE, display_load_time, load_covid_data

st.set_page_config(page_title="NYC COVID Data", layout="wide")


def main() -> None:
    st.title("NYC COVID-19 Cases")
    st.markdown(
        "This page uses BigQuery-hosted COVID case data to contextualize changes in MTA ridership."
    )

    time_window = st.radio(
        "Time window",
        options=["Recent 180 days", "Recent 365 days", "Full history", "Custom range"],
        index=0,
        key="covid_page_time_window_v1",
    )

    try:
        if time_window == "Recent 180 days":
            df = load_covid_data(lookback_days=180)
        elif time_window == "Recent 365 days":
            df = load_covid_data(lookback_days=365)
        elif time_window == "Full history":
            df = load_covid_data()
        else:
            today = date.today()
            default_start = today - timedelta(days=180)
            selected_dates = st.date_input(
                "Date range",
                value=(default_start, today),
                min_value=COVID_MIN_DATE,
                max_value=today,
                key="covid_page_date_range_v3",
            )
            start_date = default_start
            end_date = today
            if len(selected_dates) == 2:
                start_date, end_date = selected_dates
            df = load_covid_data(start_date=str(start_date), end_date=str(end_date))
    except Exception as exc:
        st.error(f"Failed to load COVID data from BigQuery: {exc}")
        return

    st.caption("Source: BigQuery table `mta_data.nyc_covid_cases`.")
    st.write(
        "Loaded "
        f"{len(df)} rows from {df['date_of_interest'].min().date()} "
        f"to {df['date_of_interest'].max().date()}."
    )

    st.caption("Fast default: recent 180 days. Expand only when you need the full history.")
    rolling_window = st.slider(
        "Rolling average (days)",
        min_value=1,
        max_value=30,
        value=7,
        key="covid_page_rolling_v2",
    )

    plot_df = df[["date_of_interest", "case_count"]].copy()
    plot_df["7-day avg"] = plot_df["case_count"].rolling(rolling_window).mean()

    st.line_chart(plot_df.set_index("date_of_interest"), height=320)

    monthly = (
        df.groupby("year_month", as_index=False)["case_count"]
        .mean()
        .rename(columns={"case_count": "avg_case_count"})
    )
    st.bar_chart(monthly.set_index("year_month"), height=280)

    st.markdown(
        """
        **Connection to MTA Ridership:** comparing COVID case surges with ridership dips helps
        explain why commuter rail and subway recovery lagged during major waves.
        """
    )


with display_load_time():
    main()
