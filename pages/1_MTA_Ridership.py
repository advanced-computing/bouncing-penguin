from datetime import date, timedelta

import streamlit as st

from utils import MTA_MIN_DATE, TRANSIT_MODES, display_load_time, load_mta_data

st.set_page_config(page_title="MTA Ridership", layout="wide")


def get_mta_page_columns(selected_services: list[str]) -> tuple[str, ...]:
    columns = {"date", TRANSIT_MODES["Subway"]["ridership"], TRANSIT_MODES["Subway"]["recovery"]}
    for service in selected_services:
        mode_columns = TRANSIT_MODES.get(service, {})
        columns.update(mode_columns.values())
    return tuple(columns)


def main() -> None:
    st.title("MTA Daily Ridership Analysis")

    selected_services = st.multiselect(
        "Select services",
        ["Subway", "Bus", "LIRR", "Metro-North"],
        default=["Subway"],
        key="mta_page_services_v3",
    )
    if not selected_services:
        st.info("Choose at least one service to display the ridership charts.")
        return

    time_window = st.radio(
        "Time window",
        options=["Recent 180 days", "Recent 365 days", "Full history", "Custom range"],
        index=0,
        key="mta_page_time_window_v1",
    )

    try:
        if time_window == "Recent 180 days":
            df = load_mta_data(columns=get_mta_page_columns(selected_services), lookback_days=180)
        elif time_window == "Recent 365 days":
            df = load_mta_data(columns=get_mta_page_columns(selected_services), lookback_days=365)
        elif time_window == "Full history":
            df = load_mta_data(columns=get_mta_page_columns(selected_services))
        else:
            today = date.today()
            default_start = today - timedelta(days=180)
            selected_dates = st.date_input(
                "Date range",
                value=(default_start, today),
                min_value=MTA_MIN_DATE,
                max_value=today,
                key="mta_page_date_range_v3",
            )
            start_date = default_start
            end_date = today
            if len(selected_dates) == 2:
                start_date, end_date = selected_dates
            df = load_mta_data(
                columns=get_mta_page_columns(selected_services),
                start_date=str(start_date),
                end_date=str(end_date),
            )
    except Exception as exc:
        st.error(f"Failed to load MTA data from BigQuery: {exc}")
        return

    st.caption(
        "Source: BigQuery table `mta_data.daily_ridership` refreshed with `load_data_to_bq.py`."
    )
    st.write(
        f"Loaded {len(df)} rows from {df['date'].min().date()} to {df['date'].max().date()}."
    )

    st.caption("Fast default: recent 180 days. Expand only when you need the full history.")
    rolling_window = st.slider(
        "Rolling average (days)",
        min_value=1,
        max_value=60,
        value=7,
        key="mta_page_rolling_v2",
    )

    services = {
        "Subway": TRANSIT_MODES["Subway"]["ridership"],
        "Bus": TRANSIT_MODES["Bus"]["ridership"],
        "LIRR": TRANSIT_MODES["LIRR"]["ridership"],
        "Metro-North": TRANSIT_MODES["Metro-North"]["ridership"],
    }
    selected_services = [
        service for service in selected_services if services[service] in df.columns
    ]
    if not selected_services:
        st.error("The selected ridership columns are not available in the current BigQuery table.")
        return

    st.subheader("Daily Ridership Over Time")
    ridership_frame = df[["date"]].copy()
    for service in selected_services:
        ridership_frame[service] = df[services[service]].rolling(rolling_window).mean()
    st.line_chart(ridership_frame.set_index("date"), height=320)

    st.subheader("Recovery Rate (% of Pre-Pandemic Levels)")
    recovery_frame = df[["date"]].copy()
    recovery_lookup = {
        "Subway": TRANSIT_MODES["Subway"]["recovery"],
        "Bus": TRANSIT_MODES["Bus"]["recovery"],
        "LIRR": TRANSIT_MODES["LIRR"]["recovery"],
        "Metro-North": TRANSIT_MODES["Metro-North"]["recovery"],
    }
    for service, column in recovery_lookup.items():
        if column not in df.columns:
            continue
        recovery_frame[service] = df[column].rolling(rolling_window).mean()
    st.line_chart(recovery_frame.set_index("date"), height=320)
    st.caption("The pre-pandemic baseline is 100% recovery.")

    st.subheader("Weekday vs Weekend Subway Ridership")
    day_type_frame = df.copy()
    day_type_frame["Day Type"] = day_type_frame["is_weekend"].map(
        {True: "Weekend", False: "Weekday"}
    )
    weekend_average = (
        day_type_frame.groupby("Day Type")[TRANSIT_MODES["Subway"]["ridership"]]
        .mean()
        .reset_index()
    )
    st.bar_chart(weekend_average.set_index("Day Type"))


with display_load_time():
    main()
