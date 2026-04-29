from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import (
    MODE_COLORS,
    MTA_MIN_DATE,
    TRANSIT_MODES,
    display_load_time,
    load_mta_data,
)

st.set_page_config(page_title="MTA Ridership", layout="wide")


def get_mta_page_columns(selected_services: list[str]) -> tuple[str, ...]:
    columns = {"date", TRANSIT_MODES["Subway"]["ridership"], TRANSIT_MODES["Subway"]["recovery"]}
    for service in selected_services:
        mode_columns = TRANSIT_MODES.get(service, {})
        columns.update(mode_columns.values())
    return tuple(columns)


def _tidy_series(
    df: pd.DataFrame,
    services: list[str],
    column_lookup: dict[str, str],
    rolling_window: int,
) -> pd.DataFrame:
    rows = []
    for service in services:
        column = column_lookup.get(service)
        if not column or column not in df.columns:
            continue
        chunk = df[["date", column]].copy()
        chunk["Service"] = service
        chunk["Value"] = chunk[column].rolling(rolling_window).mean()
        rows.append(chunk[["date", "Service", "Value"]])

    if not rows:
        return pd.DataFrame(columns=["date", "Service", "Value"])
    return pd.concat(rows, ignore_index=True).dropna(subset=["Value"])


def main() -> None:
    st.title("MTA Daily Ridership Analysis")
    st.caption("Default view loads only the latest 180 days for a faster deployed app.")

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

    requested_columns = get_mta_page_columns(selected_services)
    with st.spinner("Loading MTA data from BigQuery..."):
        try:
            if time_window == "Recent 180 days":
                df = load_mta_data(columns=requested_columns, lookback_days=180)
            elif time_window == "Recent 365 days":
                df = load_mta_data(columns=requested_columns, lookback_days=365)
            elif time_window == "Full history":
                df = load_mta_data(columns=requested_columns)
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
                if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                    start_date, end_date = selected_dates
                df = load_mta_data(
                    columns=requested_columns,
                    start_date=str(start_date),
                    end_date=str(end_date),
                )
        except Exception as exc:
            st.error(f"Failed to load MTA data from BigQuery: {exc}")
            return

    st.caption(
        "Source: BigQuery table `mta_data.daily_ridership` refreshed daily by GitHub Actions."
    )
    st.write(
        f"Loaded {len(df)} rows from {df['date'].min().date()} to {df['date'].max().date()}."
    )

    rolling_window = st.slider(
        "Rolling average (days)",
        min_value=1,
        max_value=60,
        value=7,
        key="mta_page_rolling_v2",
    )

    ridership_lookup = {service: TRANSIT_MODES[service]["ridership"] for service in selected_services}
    available_services = [s for s in selected_services if ridership_lookup[s] in df.columns]
    if not available_services:
        st.error("The selected ridership columns are not available in the current BigQuery table.")
        return

    st.subheader("Are riders coming back in absolute numbers?")
    ridership_df = _tidy_series(df, available_services, ridership_lookup, rolling_window)
    fig = px.line(
        ridership_df,
        x="date",
        y="Value",
        color="Service",
        color_discrete_map=MODE_COLORS,
    )
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Date",
        yaxis_title="Daily Ridership",
        legend_title_text="",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(
        "Absolute ridership has trended up across services even when recovery percentages plateau."
    )

    st.subheader("How has each MTA service recovered since 2020?")
    recovery_lookup = {service: TRANSIT_MODES[service]["recovery"] for service in selected_services}
    recovery_df = _tidy_series(df, available_services, recovery_lookup, rolling_window)
    recovery_df["Recovery Percent"] = recovery_df["Value"] * 100
    recovery_fig = px.line(
        recovery_df,
        x="date",
        y="Recovery Percent",
        color="Service",
        color_discrete_map=MODE_COLORS,
    )
    recovery_fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="#64748b",
        annotation_text="Pre-pandemic baseline",
    )
    recovery_fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Date",
        yaxis_title="Recovery Rate",
        legend_title_text="",
    )
    recovery_fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(recovery_fig, width="stretch", config={"displayModeBar": False})
    st.caption("The pre-pandemic baseline is 100% recovery.")

    st.subheader("Has commuting changed permanently?")
    subway_column = TRANSIT_MODES["Subway"]["ridership"]
    if subway_column in df.columns:
        day_type_frame = df.copy()
        day_type_frame["Day Type"] = day_type_frame["is_weekend"].map(
            {True: "Weekend", False: "Weekday"}
        )
        weekend_average = (
            day_type_frame.groupby("Day Type", as_index=False)[subway_column]
            .mean()
            .rename(columns={subway_column: "Average Subway Ridership"})
        )
        bar_fig = px.bar(
            weekend_average,
            x="Day Type",
            y="Average Subway Ridership",
            color="Day Type",
            color_discrete_map={"Weekday": MODE_COLORS["Subway"], "Weekend": MODE_COLORS["Bus"]},
        )
        bar_fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="",
            showlegend=False,
        )
        st.plotly_chart(bar_fig, width="stretch", config={"displayModeBar": False})
        if len(weekend_average) == 2:
            weekday_val = weekend_average.loc[
                weekend_average["Day Type"] == "Weekday", "Average Subway Ridership"
            ].iloc[0]
            weekend_val = weekend_average.loc[
                weekend_average["Day Type"] == "Weekend", "Average Subway Ridership"
            ].iloc[0]
            if weekday_val > 0:
                st.caption(
                    f"Weekends average **{weekend_val / weekday_val:.0%}** of weekday subway "
                    "ridership — weekday commuting still drives system load."
                )


with display_load_time():
    main()
