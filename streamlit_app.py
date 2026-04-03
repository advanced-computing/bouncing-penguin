from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import (
    MTA_MIN_DATE,
    TRANSIT_MODES,
    display_load_time,
    get_holiday_df,
    get_latest_recovery,
    get_weekday_weekend_comparison,
    load_mta_data,
)

st.set_page_config(page_title="MTA Ridership Dashboard", layout="wide")


def get_dashboard_columns(view: str, selected_modes: list[str]) -> tuple[str, ...]:
    columns = {"date"}

    if view == "Overview":
        columns.add(TRANSIT_MODES["Subway"]["ridership"])
        for mode in selected_modes:
            mode_columns = TRANSIT_MODES.get(mode, {})
            columns.update(mode_columns.values())
        for mode_columns in TRANSIT_MODES.values():
            columns.add(mode_columns["recovery"])
    elif view == "Comparison":
        for mode_columns in TRANSIT_MODES.values():
            columns.add(mode_columns["recovery"])
    elif view == "Calendar":
        for mode_columns in TRANSIT_MODES.values():
            columns.add(mode_columns["recovery"])
    else:
        columns.add(TRANSIT_MODES["Subway"]["recovery"])

    return tuple(columns)


def render_kpis(filtered: pd.DataFrame) -> None:
    st.subheader("Current Recovery Snapshot")
    st.caption("Average recovery rate over the most recent 30 days in the filtered view")

    recovery = get_latest_recovery(filtered, days=30)
    if not recovery:
        st.info("No recovery metrics are available for the current filter selection.")
        return

    kpi_columns = st.columns(len(recovery))
    for index, (mode, rate) in enumerate(recovery.items()):
        with kpi_columns[index]:
            st.metric(mode, f"{rate:.0%}")


def render_recovery_chart(
    filtered: pd.DataFrame,
    selected_modes: list[str],
    rolling_window: int,
) -> None:
    st.subheader("Recovery Trend Over Time")

    chart_df = filtered[["date"]].copy()
    for mode in selected_modes:
        column = TRANSIT_MODES[mode]["recovery"]
        if column not in filtered.columns:
            continue
        chart_df[mode] = filtered[column].rolling(rolling_window).mean()

    chart_df = chart_df.set_index("date").dropna(how="all")
    if chart_df.empty:
        st.info("No recovery series are available for the selected transit modes.")
        return

    st.line_chart(chart_df, height=320)
    st.caption("The pre-pandemic baseline is 100% recovery.")


def render_total_chart(
    filtered: pd.DataFrame,
    selected_modes: list[str],
    rolling_window: int,
) -> None:
    st.subheader("Total Daily Ridership")

    chart_df = filtered[["date"]].copy()
    for mode in selected_modes:
        column = TRANSIT_MODES[mode]["ridership"]
        if column not in filtered.columns:
            continue
        chart_df[mode] = filtered[column].rolling(rolling_window).mean()

    chart_df = chart_df.set_index("date").dropna(how="all")
    if chart_df.empty:
        st.info("No ridership series are available for the selected transit modes.")
        return

    st.line_chart(chart_df, height=320)


def render_subway_day_type_summary(filtered: pd.DataFrame) -> None:
    st.subheader("Weekday vs Weekend Subway Ridership")

    subway_column = TRANSIT_MODES["Subway"]["ridership"]
    if subway_column not in filtered.columns:
        st.info("Subway ridership data is not available in the current dataset.")
        return

    summary = filtered.copy()
    summary["Day Type"] = summary["is_weekend"].map({True: "Weekend", False: "Weekday"})
    averages = (
        summary.groupby("Day Type")[subway_column]
        .mean()
        .reset_index()
        .set_index("Day Type")
    )
    st.bar_chart(averages, height=240)


def render_mode_recovery_summary(filtered: pd.DataFrame) -> None:
    st.subheader("Average Recovery by Mode")

    rows = []
    for mode, columns in TRANSIT_MODES.items():
        recovery_column = columns["recovery"]
        if recovery_column not in filtered.columns:
            continue
        rows.append({"Mode": mode, "Recovery": filtered[recovery_column].mean()})

    if not rows:
        st.info("No recovery summary is available for the current dataset.")
        return

    summary_df = pd.DataFrame(rows).set_index("Mode")
    st.bar_chart(summary_df, height=240)


def render_weekday_weekend(filtered: pd.DataFrame) -> None:
    st.subheader("Weekday vs Weekend Recovery")

    available_years = [str(year) for year in sorted(filtered["year"].unique())]
    selected_year = st.selectbox(
        "Select year for comparison",
        options=["All Years", *available_years],
        index=0,
    )

    year_value = None if selected_year == "All Years" else int(selected_year)
    comparison = get_weekday_weekend_comparison(filtered, year=year_value)
    if comparison.empty:
        st.info("No weekday/weekend comparison is available for the current filter.")
        return

    comparison_long = comparison.melt(
        id_vars="Transit Mode",
        value_vars=["Weekday Avg Recovery", "Weekend Avg Recovery"],
        var_name="Day Type",
        value_name="Recovery Rate",
    )
    comparison_long["Day Type"] = comparison_long["Day Type"].str.replace(
        " Avg Recovery",
        "",
    )
    comparison_long["Recovery Percent"] = comparison_long["Recovery Rate"] * 100
    comparison_fig = px.bar(
        comparison_long,
        x="Transit Mode",
        y="Recovery Percent",
        color="Day Type",
        barmode="group",
        category_orders={"Day Type": ["Weekday", "Weekend"]},
        color_discrete_sequence=["#7dd3fc", "#2563eb"],
    )
    comparison_fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Recovery Rate",
        legend_title_text="",
    )
    comparison_fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(comparison_fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("**Monthly Weekend Minus Weekday Gap (Subway)**")
    subway_column = TRANSIT_MODES["Subway"]["recovery"]
    monthly = (
        filtered.groupby(["year_month", "is_weekend"])[subway_column]
        .mean()
        .unstack()
        .rename(columns={False: "Weekday", True: "Weekend"})
    )
    if monthly.empty:
        st.info("Not enough data to compute the monthly weekday/weekend gap.")
        return

    monthly["Gap"] = monthly["Weekend"] - monthly["Weekday"]
    monthly = monthly.reset_index()
    monthly["Gap Percent"] = monthly["Gap"] * 100
    gap_fig = px.bar(
        monthly,
        x="year_month",
        y="Gap Percent",
        color="Gap Percent",
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
    )
    gap_fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Month",
        yaxis_title="Weekend - Weekday",
        coloraxis_showscale=False,
    )
    gap_fig.update_yaxes(ticksuffix="%", zeroline=True, zerolinewidth=1)
    st.plotly_chart(gap_fig, use_container_width=True, config={"displayModeBar": False})


def render_holiday_impact(filtered: pd.DataFrame) -> None:
    st.subheader("Holiday & Event Impact on Subway Recovery")

    holidays_df = get_holiday_df()
    holiday_names = sorted(holidays_df["holiday"].unique())
    selected_holidays = st.multiselect(
        "Select holidays or events to highlight",
        options=holiday_names,
        default=["Thanksgiving", "Christmas", "Congestion Pricing Launch"],
    )
    if not selected_holidays:
        st.info("Choose at least one holiday or event to draw comparison lines.")
        return

    subway_column = TRANSIT_MODES["Subway"]["recovery"]
    if subway_column not in filtered.columns:
        st.info("Subway recovery data is not available in the current dataset.")
        return

    series = filtered.set_index("date")[subway_column].rolling(7).mean().rename("Subway")
    st.line_chart(series, height=320)

    selected_rows = holidays_df[holidays_df["holiday"].isin(selected_holidays)]
    visible_events = selected_rows[
        (selected_rows["date"] >= filtered["date"].min())
        & (selected_rows["date"] <= filtered["date"].max())
    ][["holiday", "date"]].copy()
    if not visible_events.empty:
        visible_events["date"] = visible_events["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(visible_events, use_container_width=True, hide_index=True)

    impact_rows = []
    for _, row in selected_rows.iterrows():
        holiday_date = pd.Timestamp(row["date"])
        holiday_window = filtered[
            (filtered["date"] >= holiday_date - pd.Timedelta(days=1))
            & (filtered["date"] <= holiday_date + pd.Timedelta(days=1))
        ]
        baseline_window = filtered[
            (filtered["date"] >= holiday_date - pd.Timedelta(days=8))
            & (filtered["date"] < holiday_date - pd.Timedelta(days=1))
        ]
        if holiday_window.empty or baseline_window.empty:
            continue
        holiday_average = holiday_window[subway_column].mean()
        baseline_average = baseline_window[subway_column].mean()
        impact_rows.append(
            {
                "Holiday": row["holiday"],
                "Date": holiday_date.strftime("%Y-%m-%d"),
                "Holiday Recovery": f"{holiday_average:.0%}",
                "Prior Week Recovery": f"{baseline_average:.0%}",
                "Change": f"{holiday_average - baseline_average:+.0%}",
            }
        )

    if impact_rows:
        st.dataframe(pd.DataFrame(impact_rows), use_container_width=True, hide_index=True)


def render_yearly_recovery(filtered: pd.DataFrame) -> None:
    st.subheader("Year-over-Year Recovery by Transit Mode")

    rows = []
    for year in sorted(filtered["year"].unique()):
        year_data = filtered[filtered["year"] == year]
        for mode, columns in TRANSIT_MODES.items():
            recovery_column = columns["recovery"]
            if recovery_column not in year_data.columns:
                continue
            rows.append(
                {
                    "Year": str(year),
                    "Transit Mode": mode,
                    "Avg Recovery": year_data[recovery_column].mean(),
                }
            )

    if not rows:
        st.info("No yearly recovery view is available for the current filter.")
        return

    yearly_df = pd.DataFrame(rows)
    yearly_df["Avg Recovery Percent"] = yearly_df["Avg Recovery"] * 100
    yearly_fig = px.bar(
        yearly_df,
        x="Year",
        y="Avg Recovery Percent",
        color="Transit Mode",
        barmode="group",
        color_discrete_sequence=["#60a5fa", "#f97316", "#ef4444", "#34d399", "#a78bfa"],
    )
    yearly_fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Average Recovery",
        legend_title_text="",
    )
    yearly_fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(yearly_fig, use_container_width=True, config={"displayModeBar": False})


def render_heatmap(filtered: pd.DataFrame) -> None:
    st.subheader("Ridership by Day of Week")

    selected_mode = st.selectbox(
        "Select transit mode for heatmap",
        options=list(TRANSIT_MODES.keys()),
        index=0,
    )
    recovery_column = TRANSIT_MODES[selected_mode]["recovery"]
    if recovery_column not in filtered.columns:
        st.info("The selected transit mode is unavailable in the current dataset.")
        return

    pivot = filtered.groupby(["year", "day_name"])[recovery_column].mean().reset_index()
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    pivot["day_name"] = pd.Categorical(pivot["day_name"], categories=day_order, ordered=True)
    pivot = pivot.sort_values(["year", "day_name"])
    pivot_wide = pivot.pivot(index="day_name", columns="year", values=recovery_column)

    st.dataframe(
        pivot_wide.style.format("{:.0%}").background_gradient(cmap="RdYlGn"),
        use_container_width=True,
    )


def render_dashboard(
    df: pd.DataFrame,
    view: str,
    selected_modes: list[str],
    rolling_window: int,
) -> None:
    st.sidebar.header("Filters")
    st.sidebar.caption("Fast default: recent 180 days. Expand the range only when needed.")

    if df.empty:
        st.warning("No data is available for the current filters.")
        return

    st.caption("Sections are split to keep each page load fast while preserving the full analysis.")

    if view == "Overview":
        render_kpis(df)
        st.markdown("---")
        render_recovery_chart(df, selected_modes, rolling_window)
        render_total_chart(df, selected_modes, rolling_window)
        render_subway_day_type_summary(df)
        render_mode_recovery_summary(df)
    elif view == "Comparison":
        render_weekday_weekend(df)
        render_yearly_recovery(df)
    elif view == "Calendar":
        render_heatmap(df)
    else:
        render_holiday_impact(df)

    st.markdown("---")
    st.caption(
        "Data source: BigQuery tables "
        "`mta_data.daily_ridership` and supporting holiday metadata in the app."
    )


def render_proposal() -> None:
    st.header("Project Proposal")

    st.subheader("Research Questions")
    st.markdown(
        """
        1. How have subway, bus, LIRR, and Metro-North recovered relative to comparable pre-pandemic days?
        2. How different are weekday and weekend recovery patterns, and how has that gap changed over time?
        3. Do holidays, major events, and policy changes line up with visible ridership shifts?
        """
    )

    st.subheader("Datasets")
    st.markdown(
        """
        The app uses two BigQuery-backed datasets:

        - `mta_data.daily_ridership`: the statewide MTA daily ridership dataset from `data.ny.gov`
        - `mta_data.nyc_covid_cases`: NYC daily COVID case counts from `data.cityofnewyork.us`

        We use batch loading for both sources because the tables are relatively small, update on a daily cadence,
        and are easier to keep consistent with a full refresh than with event-by-event ingestion.
        """
    )

    st.subheader("Methodology")
    st.markdown(
        """
        The dashboard focuses on rolling averages, weekday-versus-weekend comparisons, and event windows around
        holidays. Those views let us compare absolute ridership and recovery percentages without moving large
        raw files into Streamlit on every rerun.
        """
    )

    st.subheader("Performance Notes")
    st.markdown(
        """
        For Lab 10, the app now reads both datasets from BigQuery, caches query results in Streamlit,
        selects only the columns each page actually needs, and shows total page load time with a custom
        context manager.
        """
    )


def main() -> None:
    st.title("MTA Ridership Recovery Dashboard")
    st.markdown(
        "Explore how New York City's transit system has recovered since 2020 using BigQuery-backed data."
    )

    page = st.radio("View", ["Dashboard", "Proposal"], horizontal=True)
    if page == "Dashboard":
        view = st.radio(
            "Dashboard section",
            options=["Overview", "Comparison", "Calendar", "Events"],
            horizontal=True,
            key="dashboard_section_v2",
        )
        selected_modes = st.sidebar.multiselect(
            "Transit modes",
            options=list(TRANSIT_MODES.keys()),
            default=["Subway"],
            key="dashboard_modes_v2",
        )
        rolling_window = st.sidebar.slider(
            "Rolling average (days)",
            1,
            60,
            7,
            key="dashboard_rolling_v2",
        )
        time_window = st.sidebar.radio(
            "Time window",
            options=["Recent 180 days", "Recent 365 days", "Full history", "Custom range"],
            index=0,
            key="dashboard_time_window_v1",
        )

        requested_columns = get_dashboard_columns(view, selected_modes)
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
                selected_dates = st.sidebar.date_input(
                    "Date range",
                    value=(default_start, today),
                    min_value=MTA_MIN_DATE,
                    max_value=today,
                    key="dashboard_date_range_v3",
                )
                start_date = default_start
                end_date = today
                if len(selected_dates) == 2:
                    start_date, end_date = selected_dates
                df = load_mta_data(
                    columns=requested_columns,
                    start_date=str(start_date),
                    end_date=str(end_date),
                )
        except Exception as exc:
            st.error(f"Failed to load data from BigQuery: {exc}")
            return

        render_dashboard(df, view, selected_modes, rolling_window)
    else:
        render_proposal()


with display_load_time():
    main()
