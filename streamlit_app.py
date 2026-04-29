from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from utils import (
    MODE_COLORS,
    MTA_MIN_DATE,
    TRANSIT_MODES,
    display_load_time,
    get_holiday_df,
    get_latest_recovery,
    get_recovery_with_delta,
    get_weekday_weekend_comparison,
    load_covid_data,
    load_mta_data,
)

st.set_page_config(page_title="MTA Ridership Dashboard", layout="wide")


def get_dashboard_columns(selected_modes: list[str]) -> tuple[str, ...]:
    columns = {"date", TRANSIT_MODES["Subway"]["ridership"]}

    for mode_columns in TRANSIT_MODES.values():
        columns.add(mode_columns["recovery"])

    for mode in selected_modes:
        mode_columns = TRANSIT_MODES.get(mode, {})
        columns.update(mode_columns.values())

    return tuple(columns)


def get_date_bounds(time_window: str) -> tuple[str | None, str | None, int | None]:
    if time_window == "Recent 180 days":
        return None, None, 180
    if time_window == "Recent 365 days":
        return None, None, 365
    if time_window == "Full history":
        return None, None, None

    today = date.today()
    default_start = today - timedelta(days=180)
    selected_dates = st.sidebar.date_input(
        "Date range",
        value=(default_start, today),
        min_value=MTA_MIN_DATE,
        max_value=today,
        key="dashboard_date_range_v4",
    )
    start_date = default_start
    end_date = today
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    return str(start_date), str(end_date), None


def render_data_status(mta_df: pd.DataFrame, covid_df: pd.DataFrame) -> None:
    if mta_df.empty:
        return

    latest_mta = mta_df["date"].max().date()
    mta_range = f"{mta_df['date'].min().date()} to {latest_mta}"
    status_columns = st.columns(4)
    status_columns[0].metric("Latest MTA Date", str(latest_mta))
    status_columns[1].metric("MTA Rows Loaded", f"{len(mta_df):,}")
    status_columns[2].metric("Selected Range", mta_range)

    if covid_df.empty:
        status_columns[3].metric("Latest COVID Date", "Unavailable")
    else:
        latest_covid = covid_df["date_of_interest"].max().date()
        status_columns[3].metric("Latest COVID Date", str(latest_covid))


def render_about_data() -> None:
    with st.expander("About the data", expanded=False):
        st.markdown(
            """
            **Data sources**
            - MTA Daily Ridership — NY Open Data dataset `vxuj-8kew`
            - NYC COVID-19 Cases — NY Open Data dataset `rc75-m7u3`

            **Refresh cadence**
            - GitHub Actions runs the ETL daily at 12:00 UTC
            - Manual `workflow_dispatch` trigger available for ad-hoc refreshes

            **Validation**
            - pandera schema validation on ingest; missing optional numeric
              columns produce warnings rather than failures so the pipeline
              degrades gracefully

            **Upstream status**
            - As of the most recent successful run, the upstream MTA Daily
              Ridership feed has not published rows beyond 2025-01-09.
              The pipeline continues to execute cleanly each day; the latest
              BigQuery date reflects the upstream publisher's cadence,
              not a pipeline failure.
            """
        )


def tidy_time_series(
    df: pd.DataFrame,
    selected_modes: list[str],
    value_type: str,
    rolling_window: int,
) -> pd.DataFrame:
    rows = []
    for mode in selected_modes:
        column = TRANSIT_MODES[mode][value_type]
        if column not in df.columns:
            continue

        series = df[["date", column]].copy()
        series["Transit Mode"] = mode
        series["Value"] = series[column].rolling(rolling_window).mean()
        rows.append(series[["date", "Transit Mode", "Value"]])

    if not rows:
        return pd.DataFrame(columns=["date", "Transit Mode", "Value"])

    return pd.concat(rows, ignore_index=True).dropna(subset=["Value"])


def render_kpis(filtered: pd.DataFrame) -> None:
    st.subheader("Current Recovery Snapshot")
    st.caption("Average recovery rate over the most recent 30 days vs the prior 30 days")

    recovery = get_recovery_with_delta(filtered, days=30)
    if not recovery:
        st.info("No recovery metrics are available for the current filter selection.")
        return

    kpi_columns = st.columns(len(recovery))
    for index, (mode, info) in enumerate(recovery.items()):
        with kpi_columns[index]:
            delta_text = (
                f"{info['delta'] * 100:+.1f} pts vs prior 30 days"
                if info["delta"] is not None
                else None
            )
            st.metric(mode, f"{info['recovery']:.0%}", delta=delta_text)


def render_key_takeaways(filtered: pd.DataFrame) -> None:
    """Three dynamic insights at the top of the Overview tab."""
    if filtered.empty:
        return

    bullets = []

    subway_rec_col = TRANSIT_MODES["Subway"]["recovery"]
    if subway_rec_col in filtered.columns:
        recent = filtered.sort_values("date").tail(30)
        weekday_avg = recent.loc[~recent["is_weekend"], subway_rec_col].mean()
        weekend_avg = recent.loc[recent["is_weekend"], subway_rec_col].mean()
        if pd.notna(weekday_avg):
            bullets.append(
                f"**Subway weekdays** are running at **{weekday_avg:.0%}** of the "
                "comparable pre-pandemic day over the last 30 days."
            )
        if pd.notna(weekday_avg) and pd.notna(weekend_avg):
            gap = weekend_avg - weekday_avg
            direction = "above" if gap >= 0 else "below"
            bullets.append(
                f"**Weekend vs weekday gap:** subway weekends are "
                f"**{abs(gap) * 100:.1f} pts {direction}** weekdays — "
                "remote work is still reshaping the commute."
            )

    recovery_30 = get_latest_recovery(filtered, days=30)
    if "Subway" in recovery_30 and "Bridges & Tunnels" in recovery_30:
        bt_gap = recovery_30["Bridges & Tunnels"] - recovery_30["Subway"]
        bullets.append(
            f"**Bridges & Tunnels lead Subway by {bt_gap * 100:+.1f} pts** in the "
            "latest 30 days — driving recovered faster than transit."
        )

    if not bullets:
        return

    st.info("**Key Takeaways**\n\n" + "\n\n".join(f"- {b}" for b in bullets[:3]))


def render_recovery_chart(
    filtered: pd.DataFrame,
    selected_modes: list[str],
    rolling_window: int,
) -> None:
    st.subheader("How has each MTA service recovered since 2020?")

    chart_df = tidy_time_series(filtered, selected_modes, "recovery", rolling_window)
    if chart_df.empty:
        st.info("No recovery series are available for the selected transit modes.")
        return

    chart_df["Recovery Percent"] = chart_df["Value"] * 100
    fig = px.line(
        chart_df,
        x="date",
        y="Recovery Percent",
        color="Transit Mode",
        color_discrete_map=MODE_COLORS,
        markers=False,
    )
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="#64748b",
        annotation_text="Pre-pandemic baseline",
    )
    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Date",
        yaxis_title="Recovery Rate",
        legend_title_text="",
    )
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    insight_lines = []
    for mode in selected_modes:
        recovery_col = TRANSIT_MODES[mode]["recovery"]
        if recovery_col in filtered.columns:
            latest = filtered.sort_values("date").tail(30)[recovery_col].mean()
            if pd.notna(latest):
                insight_lines.append(f"{mode} {latest:.0%}")
    if insight_lines:
        st.caption(
            "Latest 30-day average: "
            + ", ".join(insight_lines)
            + ". Bridges & Tunnels typically lead transit modes — driving recovered first."
        )


def render_total_chart(
    filtered: pd.DataFrame,
    selected_modes: list[str],
    rolling_window: int,
) -> None:
    st.subheader("Are riders coming back in absolute numbers?")

    chart_df = tidy_time_series(filtered, selected_modes, "ridership", rolling_window)
    if chart_df.empty:
        st.info("No ridership series are available for the selected transit modes.")
        return

    fig = px.line(
        chart_df,
        x="date",
        y="Value",
        color="Transit Mode",
        color_discrete_map=MODE_COLORS,
        markers=False,
    )
    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Date",
        yaxis_title="Daily Ridership / Traffic",
        legend_title_text="",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(
        "Even where recovery percentages plateau, raw ridership still trends up — "
        "the city is bigger and busier than 2020."
    )


def render_subway_day_type_summary(filtered: pd.DataFrame) -> None:
    st.subheader("Has commuting changed permanently?")

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
    )
    fig = px.bar(
        averages,
        x="Day Type",
        y=subway_column,
        color="Day Type",
        color_discrete_map={"Weekday": "#2563eb", "Weekend": "#f97316"},
    )
    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="",
        yaxis_title="Average Subway Ridership",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    if not averages.empty and len(averages) == 2:
        weekday_val = averages.loc[averages["Day Type"] == "Weekday", subway_column].mean()
        weekend_val = averages.loc[averages["Day Type"] == "Weekend", subway_column].mean()
        if pd.notna(weekday_val) and pd.notna(weekend_val) and weekday_val > 0:
            ratio = weekend_val / weekday_val
            st.caption(
                f"Weekends average **{ratio:.0%}** of weekday subway ridership in this window — "
                "weekday commuting still dominates the system."
            )


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

    summary_df = pd.DataFrame(rows)
    summary_df["Recovery Percent"] = summary_df["Recovery"] * 100
    fig = px.bar(
        summary_df,
        x="Mode",
        y="Recovery Percent",
        color="Mode",
        color_discrete_map=MODE_COLORS,
    )
    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="",
        yaxis_title="Average Recovery",
        showlegend=False,
    )
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_weekday_weekend(filtered: pd.DataFrame) -> None:
    st.subheader("Weekday vs Weekend Recovery")

    available_years = [str(year) for year in sorted(filtered["year"].unique())]
    selected_year = st.selectbox(
        "Select year for comparison",
        options=["All Years", *available_years],
        index=0,
        key="weekday_weekend_year_v2",
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
    st.plotly_chart(comparison_fig, width="stretch", config={"displayModeBar": False})

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
    st.plotly_chart(gap_fig, width="stretch", config={"displayModeBar": False})


def render_holiday_impact(filtered: pd.DataFrame) -> None:
    st.subheader("Holiday & Event Impact on Subway Recovery")

    holidays_df = get_holiday_df()
    holiday_names = sorted(holidays_df["holiday"].unique())
    selected_holidays = st.multiselect(
        "Select holidays or events to highlight",
        options=holiday_names,
        default=["Thanksgiving", "Christmas", "Congestion Pricing Launch"],
        key="event_holidays_v2",
    )
    if not selected_holidays:
        st.info("Choose at least one holiday or event to draw comparison lines.")
        return

    subway_column = TRANSIT_MODES["Subway"]["recovery"]
    if subway_column not in filtered.columns:
        st.info("Subway recovery data is not available in the current dataset.")
        return

    selected_rows = holidays_df[holidays_df["holiday"].isin(selected_holidays)]
    visible_events = selected_rows[
        (selected_rows["date"] >= filtered["date"].min())
        & (selected_rows["date"] <= filtered["date"].max())
    ][["holiday", "date"]].copy()

    series = filtered[["date", subway_column]].copy()
    series["Subway Recovery Percent"] = series[subway_column].rolling(7).mean() * 100
    fig = px.line(
        series.dropna(subset=["Subway Recovery Percent"]),
        x="date",
        y="Subway Recovery Percent",
        color_discrete_sequence=[MODE_COLORS["Subway"]],
    )
    for _, event in visible_events.iterrows():
        event_date = pd.Timestamp(event["date"]).strftime("%Y-%m-%d")
        fig.add_vline(
            x=event_date,
            line_width=1,
            line_dash="dot",
            line_color="#475569",
        )
        fig.add_annotation(
            x=event_date,
            y=1.02,
            yref="paper",
            text=event["holiday"],
            showarrow=False,
            textangle=-90,
            font=dict(size=10),
        )
    fig.update_layout(
        height=360,
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis_title="Date",
        yaxis_title="Subway Recovery",
        showlegend=False,
    )
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

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
        st.dataframe(pd.DataFrame(impact_rows), width="stretch", hide_index=True)


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
    st.plotly_chart(yearly_fig, width="stretch", config={"displayModeBar": False})


def render_heatmap(filtered: pd.DataFrame) -> None:
    st.subheader("Ridership by Day of Week")

    selected_mode = st.selectbox(
        "Select transit mode for heatmap",
        options=list(TRANSIT_MODES.keys()),
        index=0,
        key="calendar_mode_v2",
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
        width="stretch",
    )


def build_covid_context_frame(
    mta_df: pd.DataFrame,
    covid_df: pd.DataFrame,
    rolling_window: int,
) -> pd.DataFrame:
    subway_column = TRANSIT_MODES["Subway"]["recovery"]
    mta_daily = mta_df[["date", subway_column]].copy()
    mta_daily["Subway Recovery Percent"] = (
        mta_daily[subway_column].rolling(rolling_window).mean() * 100
    )
    covid_daily = covid_df[["date_of_interest", "case_count"]].copy().rename(
        columns={"date_of_interest": "date"}
    )
    covid_daily["COVID Cases"] = covid_daily["case_count"].rolling(rolling_window).mean()

    return pd.merge(
        mta_daily[["date", "Subway Recovery Percent"]],
        covid_daily[["date", "COVID Cases"]],
        on="date",
        how="inner",
    ).dropna()


def render_covid_context(
    mta_df: pd.DataFrame,
    covid_df: pd.DataFrame,
    rolling_window: int,
) -> None:
    st.subheader("COVID Cases and Subway Recovery")

    subway_column = TRANSIT_MODES["Subway"]["recovery"]
    if subway_column not in mta_df.columns:
        st.info("Subway recovery data is not available for the current filter.")
        return
    if covid_df.empty or "case_count" not in covid_df.columns:
        st.info("COVID case data is not available for the current filter.")
        return

    combined = build_covid_context_frame(mta_df, covid_df, rolling_window)
    using_full_overlap = False
    if combined.empty:
        full_mta = load_mta_data(columns=("date", subway_column))
        full_covid = load_covid_data()
        combined = build_covid_context_frame(full_mta, full_covid, rolling_window)
        using_full_overlap = True
        if combined.empty:
            st.info("No overlapping MTA and COVID dates are available.")
            return

    if using_full_overlap:
        st.info(
            "The selected range has no overlapping MTA and COVID dates, "
            "so this tab shows the full historical overlap instead."
        )

    metric_cols = st.columns(3)
    recent = combined.tail(30)
    metric_cols[0].metric(
        "Recent Subway Recovery",
        f"{recent['Subway Recovery Percent'].mean():.0f}%",
    )
    metric_cols[1].metric(
        "Recent COVID Cases",
        f"{recent['COVID Cases'].mean():,.0f}",
    )
    correlation = combined["Subway Recovery Percent"].corr(combined["COVID Cases"])
    metric_cols[2].metric("Series Correlation", f"{correlation:.2f}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=combined["date"],
            y=combined["Subway Recovery Percent"],
            name="Subway recovery",
            mode="lines",
            line=dict(color=MODE_COLORS["Subway"], width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=combined["date"],
            y=combined["COVID Cases"],
            name="COVID cases",
            mode="lines",
            line=dict(color="#dc2626", width=2),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Subway Recovery", ticksuffix="%", secondary_y=False)
    fig.update_yaxes(title_text="COVID Cases", secondary_y=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.caption(
        "This view directly connects the second dataset to the main research question "
        "by putting COVID case trends and subway recovery on the same timeline."
    )


def render_dashboard(
    mta_df: pd.DataFrame,
    covid_df: pd.DataFrame,
    selected_modes: list[str],
    rolling_window: int,
) -> None:
    if mta_df.empty:
        st.warning("No data is available for the current filters.")
        return

    overview_tab, comparison_tab, calendar_tab, events_tab, covid_tab = st.tabs(
        ["Overview", "Comparison", "Calendar", "Events", "COVID Context"]
    )

    with overview_tab:
        render_key_takeaways(mta_df)
        render_kpis(mta_df)
        st.markdown("---")
        chart_left, chart_right = st.columns(2)
        with chart_left:
            render_recovery_chart(mta_df, selected_modes, rolling_window)
        with chart_right:
            render_total_chart(mta_df, selected_modes, rolling_window)
        summary_left, summary_right = st.columns(2)
        with summary_left:
            render_subway_day_type_summary(mta_df)
        with summary_right:
            render_mode_recovery_summary(mta_df)

    with comparison_tab:
        render_weekday_weekend(mta_df)
        render_yearly_recovery(mta_df)

    with calendar_tab:
        render_heatmap(mta_df)

    with events_tab:
        render_holiday_impact(mta_df)

    with covid_tab:
        render_covid_context(mta_df, covid_df, rolling_window)

    st.markdown("---")
    st.caption(
        "Data source: BigQuery tables "
        "`mta_data.daily_ridership`, `mta_data.nyc_covid_cases`, "
        "and supporting holiday metadata in the app."
    )

    render_about_data()


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
        st.sidebar.header("Filters")
        time_window = st.sidebar.radio(
            "Time window",
            options=["Recent 180 days", "Recent 365 days", "Full history", "Custom range"],
            index=0,
            key="dashboard_time_window_v1",
        )

        with st.sidebar.expander("Customize view", expanded=False):
            selected_modes = st.multiselect(
                "Transit modes",
                options=list(TRANSIT_MODES.keys()),
                default=["Subway"],
                key="dashboard_modes_v2",
            )
            rolling_window = st.slider(
                "Rolling average (days)",
                1,
                60,
                7,
                key="dashboard_rolling_v2",
            )

        requested_columns = get_dashboard_columns(selected_modes)
        try:
            start_date, end_date, lookback_days = get_date_bounds(time_window)
            if lookback_days is not None:
                mta_df = load_mta_data(
                    columns=requested_columns,
                    lookback_days=lookback_days,
                )
                covid_df = load_covid_data(lookback_days=lookback_days)
            elif start_date and end_date:
                mta_df = load_mta_data(
                    columns=requested_columns,
                    start_date=start_date,
                    end_date=end_date,
                )
                covid_df = load_covid_data(start_date=start_date, end_date=end_date)
            else:
                mta_df = load_mta_data(columns=requested_columns)
                covid_df = load_covid_data()
        except Exception as exc:
            st.error(f"Failed to load data from BigQuery: {exc}")
            return

        render_data_status(mta_df, covid_df)
        render_dashboard(mta_df, covid_df, selected_modes, rolling_window)
    else:
        render_proposal()


with display_load_time():
    main()
