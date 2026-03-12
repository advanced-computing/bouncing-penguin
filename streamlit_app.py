import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import (
    TRANSIT_MODES,
    get_holiday_df,
    get_latest_recovery,
    get_weekday_weekend_comparison,
    load_mta_data,
)

st.set_page_config(page_title="MTA Ridership Dashboard", layout="wide")

st.title("🚇 MTA Ridership Recovery Dashboard")
st.markdown(
    "Exploring MTA ridership trends and COVID-19 recovery patterns "
    "across transit services in New York City."
)

# ---------------------------------------------------------------------------
# Tabs: Dashboard vs Proposal
# ---------------------------------------------------------------------------
tab_dashboard, tab_proposal = st.tabs(["📊 Dashboard", "📝 Proposal"])

# ===========================
#  DATA LOADING (cached)
# ===========================


@st.cache_data(ttl=3600)
def fetch_data():
    return load_mta_data()


try:
    df = fetch_data()
    data_loaded = True
except Exception as e:
    data_loaded = False
    st.error(f"Failed to load data: {e}")

# ===========================
#  DASHBOARD TAB
# ===========================
with tab_dashboard:
    if not data_loaded:
        st.warning("Could not load MTA data. Please try again later.")
        st.stop()

    # -- Sidebar filters --
    st.sidebar.header("Filters")

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
        filtered = df[mask].copy()
    else:
        filtered = df.copy()

    selected_modes = st.sidebar.multiselect(
        "Transit modes",
        options=list(TRANSIT_MODES.keys()),
        default=["Subway", "Bus", "LIRR", "Metro-North"],
    )

    rolling_window = st.sidebar.slider(
        "Rolling average (days)", min_value=1, max_value=60, value=7
    )

    # -------------------------------------------------------
    # Section 1: KPI Cards
    # -------------------------------------------------------
    st.subheader("Current Recovery Snapshot")
    st.caption("Average recovery rate over the most recent 30 days in the dataset")

    recovery = get_latest_recovery(filtered, days=30)
    kpi_cols = st.columns(len(recovery))
    for i, (mode, rate) in enumerate(recovery.items()):
        with kpi_cols[i]:
            st.metric(
                label=mode,
                value=f"{rate:.0%}",
                delta=None,
            )

    st.markdown("---")

    # -------------------------------------------------------
    # Section 2: Recovery Trend (interactive plotly)
    # -------------------------------------------------------
    st.subheader("Recovery Trend Over Time")

    fig_recovery = go.Figure()
    for mode in selected_modes:
        col = TRANSIT_MODES[mode]["recovery"]
        if col not in filtered.columns:
            continue
        series = filtered.set_index("date")[col].rolling(rolling_window).mean()
        fig_recovery.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines",
                name=mode,
            )
        )

    # Baseline
    fig_recovery.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="gray",
        annotation_text="Pre-pandemic baseline (100%)",
    )

    fig_recovery.update_layout(
        yaxis_title="% of Pre-Pandemic Ridership",
        xaxis_title="Date",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=500,
        yaxis_tickformat=".0%",
    )
    st.plotly_chart(fig_recovery, use_container_width=True)

    # -------------------------------------------------------
    # Section 3: Total Ridership Trend
    # -------------------------------------------------------
    st.subheader("Total Daily Ridership")

    fig_total = go.Figure()
    for mode in selected_modes:
        col = TRANSIT_MODES[mode]["ridership"]
        if col not in filtered.columns:
            continue
        series = filtered.set_index("date")[col].rolling(rolling_window).mean()
        fig_total.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines",
                name=mode,
            )
        )

    fig_total.update_layout(
        yaxis_title="Daily Ridership",
        xaxis_title="Date",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        height=500,
    )
    st.plotly_chart(fig_total, use_container_width=True)

    # -------------------------------------------------------
    # Section 4: Weekday vs Weekend
    # -------------------------------------------------------
    st.subheader("Weekday vs Weekend Recovery")

    available_years = sorted(filtered["year"].unique())
    selected_year = st.selectbox(
        "Select year for comparison",
        options=["All Years"] + available_years,
        index=0,
    )

    year_val = None if selected_year == "All Years" else int(selected_year)
    comparison = get_weekday_weekend_comparison(filtered, year=year_val)

    if not comparison.empty:
        # Grouped bar chart
        comp_melted = comparison.melt(
            id_vars="Transit Mode",
            value_vars=["Weekday Avg Recovery", "Weekend Avg Recovery"],
            var_name="Day Type",
            value_name="Recovery Rate",
        )
        comp_melted["Day Type"] = comp_melted["Day Type"].str.replace(
            " Avg Recovery", ""
        )

        fig_wkday = px.bar(
            comp_melted,
            x="Transit Mode",
            y="Recovery Rate",
            color="Day Type",
            barmode="group",
            color_discrete_map={"Weekday": "#636EFA", "Weekend": "#EF553B"},
        )
        fig_wkday.update_layout(
            yaxis_tickformat=".0%",
            yaxis_title="Avg Recovery Rate (% of Pre-Pandemic)",
            height=450,
        )
        st.plotly_chart(fig_wkday, use_container_width=True)

    # Weekday vs Weekend gap over time (monthly)
    st.markdown("**Monthly Weekday-Weekend Gap (Subway)**")
    subway_col = TRANSIT_MODES["Subway"]["recovery"]
    if subway_col in filtered.columns:
        monthly = (
            filtered.groupby(["year_month", "is_weekend"])[subway_col]
            .mean()
            .unstack()
            .rename(columns={False: "Weekday", True: "Weekend"})
        )
        monthly["Gap"] = monthly["Weekend"] - monthly["Weekday"]
        monthly = monthly.reset_index()

        fig_gap = px.bar(
            monthly,
            x="year_month",
            y="Gap",
            color="Gap",
            color_continuous_scale=["#EF553B", "#CCCCCC", "#636EFA"],
            color_continuous_midpoint=0,
        )
        fig_gap.update_layout(
            xaxis_title="Month",
            yaxis_title="Weekend - Weekday Recovery Gap",
            yaxis_tickformat=".0%",
            height=350,
            showlegend=False,
            xaxis=dict(tickangle=-45, dtick=3),
        )
        st.plotly_chart(fig_gap, use_container_width=True)
        st.caption(
            "Positive values mean weekend recovery is higher than weekday. "
            "This is consistent with reduced weekday commuting due to remote work."
        )

    # -------------------------------------------------------
    # Section 5: Holiday Impact
    # -------------------------------------------------------
    st.subheader("Holiday & Event Impact on Ridership")

    holidays_df = get_holiday_df()
    holiday_names = sorted(holidays_df["holiday"].unique())
    selected_holidays = st.multiselect(
        "Select holidays/events to highlight",
        options=holiday_names,
        default=["Thanksgiving", "Christmas", "Congestion Pricing Launch"],
    )

    if selected_holidays:
        fig_holiday = go.Figure()

        # Plot subway recovery as the background line
        subway_col = TRANSIT_MODES["Subway"]["recovery"]
        if subway_col in filtered.columns:
            series = filtered.set_index("date")[subway_col].rolling(7).mean()
            fig_holiday.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series.values,
                    mode="lines",
                    name="Subway (7-day avg)",
                    line=dict(color="#636EFA"),
                )
            )

        # Add vertical lines for selected holidays
        colors = px.colors.qualitative.Set2
        sel_holidays = holidays_df[holidays_df["holiday"].isin(selected_holidays)]
        for i, holiday in enumerate(selected_holidays):
            dates = sel_holidays[sel_holidays["holiday"] == holiday]["date"]
            color = colors[i % len(colors)]
            for j, d in enumerate(dates):
                if filtered["date"].min() <= d <= filtered["date"].max():
                    fig_holiday.add_vline(
                        x=d,
                        line_dash="dot",
                        line_color=color,
                        annotation_text=holiday if j == 0 else None,
                        annotation_position="top left",
                    )

        fig_holiday.update_layout(
            yaxis_title="Subway Recovery (% of Pre-Pandemic)",
            xaxis_title="Date",
            yaxis_tickformat=".0%",
            hovermode="x unified",
            height=500,
        )
        st.plotly_chart(fig_holiday, use_container_width=True)

        # Holiday impact table
        st.markdown("**Average Subway Ridership Around Holidays**")
        impact_rows = []
        for _, row in sel_holidays.iterrows():
            h_date = row["date"]
            # 3-day window around the holiday
            window = filtered[
                (filtered["date"] >= h_date - pd.Timedelta(days=1))
                & (filtered["date"] <= h_date + pd.Timedelta(days=1))
            ]
            # Surrounding week for comparison
            baseline = filtered[
                (filtered["date"] >= h_date - pd.Timedelta(days=8))
                & (filtered["date"] < h_date - pd.Timedelta(days=1))
            ]
            if not window.empty and not baseline.empty:
                h_avg = window[subway_col].mean()
                b_avg = baseline[subway_col].mean()
                impact_rows.append(
                    {
                        "Holiday": row["holiday"],
                        "Date": h_date.strftime("%Y-%m-%d"),
                        "Holiday Recovery": f"{h_avg:.0%}",
                        "Prior Week Recovery": f"{b_avg:.0%}",
                        "Change": f"{h_avg - b_avg:+.0%}",
                    }
                )
        if impact_rows:
            st.dataframe(
                pd.DataFrame(impact_rows),
                use_container_width=True,
                hide_index=True,
            )

    # -------------------------------------------------------
    # Section 6: Year-over-Year Recovery
    # -------------------------------------------------------
    st.subheader("Year-over-Year Recovery by Transit Mode")

    yearly_rows = []
    for year in sorted(filtered["year"].unique()):
        year_data = filtered[filtered["year"] == year]
        for mode, cols in TRANSIT_MODES.items():
            col = cols["recovery"]
            if col in year_data.columns:
                avg = year_data[col].mean()
                yearly_rows.append(
                    {
                        "Year": str(year),
                        "Transit Mode": mode,
                        "Avg Recovery": avg,
                    }
                )

    if yearly_rows:
        yearly_df = pd.DataFrame(yearly_rows)
        fig_yearly = px.bar(
            yearly_df,
            x="Year",
            y="Avg Recovery",
            color="Transit Mode",
            barmode="group",
        )
        fig_yearly.update_layout(
            yaxis_title="Avg Recovery Rate (% of Pre-Pandemic)",
            yaxis_tickformat=".0%",
            height=450,
        )
        st.plotly_chart(fig_yearly, use_container_width=True)

    # -------------------------------------------------------
    # Section 7: Day-of-Week Heatmap
    # -------------------------------------------------------
    st.subheader("Ridership by Day of Week")

    heatmap_mode = st.selectbox(
        "Select transit mode for heatmap",
        options=list(TRANSIT_MODES.keys()),
        index=0,
    )
    heatmap_col = TRANSIT_MODES[heatmap_mode]["recovery"]
    if heatmap_col in filtered.columns:
        pivot = filtered.groupby(["year", "day_name"])[heatmap_col].mean().reset_index()
        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        pivot["day_name"] = pd.Categorical(
            pivot["day_name"], categories=day_order, ordered=True
        )
        pivot = pivot.sort_values(["year", "day_name"])
        pivot_wide = pivot.pivot(index="day_name", columns="year", values=heatmap_col)

        fig_heat = px.imshow(
            pivot_wide,
            color_continuous_scale="RdYlGn",
            aspect="auto",
            labels=dict(x="Year", y="Day of Week", color="Recovery %"),
            zmin=0,
            zmax=1.2,
        )
        fig_heat.update_layout(height=350)
        st.plotly_chart(fig_heat, use_container_width=True)

    # -------------------------------------------------------
    # Footer
    # -------------------------------------------------------
    st.markdown("---")
    st.caption(
        "Data source: [MTA Daily Ridership Data](https://data.ny.gov/Transportation/"
        "MTA-Daily-Ridership-Data-Beginning-2020/vxuj-8kew) | "
        "Team bouncing-penguin: Haixin Liu & Hanghai Li"
    )

# ===========================
#  PROPOSAL TAB
# ===========================
with tab_proposal:
    st.header("Project Proposal")

    st.subheader("Background and Motivation")
    st.markdown("""
    The COVID-19 pandemic caused an unprecedented drop in public transit ridership across
    New York City. At its lowest point in April 2020, subway ridership fell to roughly
    10% of normal levels, and other MTA services experienced similar declines. Since then,
    ridership has been gradually recovering, but the pace and pattern of that recovery
    has varied significantly depending on the transit mode, time of week, and even
    specific events or holidays.

    As of late 2025, subway ridership has climbed back to about 85% of pre-pandemic levels,
    while the Long Island Rail Road (LIRR) has reached 92% and Metro-North sits at around 88%.
    Bridges and tunnels traffic has actually exceeded pre-pandemic levels at roughly 105%,
    suggesting a shift in how New Yorkers choose to commute. Paratransit ridership has surged
    to 161% of pre-pandemic levels, pointing to growing demand for accessible transit options.
    These differences raise interesting questions about what drives recovery in different parts
    of the transit system and whether these patterns will continue.

    Understanding these recovery dynamics matters not just for transit planning but also
    for broader urban policy. Transit ridership affects fare revenue, congestion, air quality,
    and economic activity across the region.
    """)

    st.subheader("Research Questions")
    st.markdown("""
    We started this project with three main research questions. After working through the
    data over the past few weeks, we've refined them based on what we've actually been
    able to observe:

    **1. How do weekday vs. weekend ridership patterns differ across MTA services, and
    has that gap changed over time?**

    Our original question was simply about weekday vs. weekend differences, but we've found
    that the more interesting story is how that gap has evolved. Early in the pandemic,
    weekend ridership actually recovered faster than weekday ridership for subways and
    commuter rail, likely due to remote work reducing weekday commuting. We want to explore
    whether that trend has continued or whether weekday ridership is catching up as
    return-to-office policies have become more common.

    **2. How do holidays and major events affect ridership across different transit modes?**

    We initially framed this broadly, but we're now focusing on specific events: major holidays
    (Thanksgiving, Christmas, July 4th, New Year's), large-scale events (marathon, Times Square
    NYE), and policy changes like the launch of congestion pricing in early 2025. The congestion
    pricing angle is particularly interesting because it directly connects transit policy to
    ridership behavior.

    **3. Which transit modes have recovered fastest, and what factors explain the differences?**

    This remains our core question, but we've added more nuance. Rather than just looking at
    which mode recovered fastest, we're now also examining the rate of recovery over time.
    For example, LIRR's recovery accelerated after Grand Central Madison opened, and bus
    ridership got a boost from the Queens Bus Network Redesign. We want to see whether these
    service improvements show up clearly in the data.
    """)

    st.subheader("Dataset")
    st.markdown("""
    We're using the **MTA Daily Ridership Data** from the New York State Open Data portal
    (data.ny.gov), which is updated daily and covers all major MTA services starting from
    March 2020.

    The dataset includes daily total ridership estimates and the percentage of comparable
    pre-pandemic day ridership for each transit mode: Subways, Buses, LIRR, Metro-North,
    Access-A-Ride, and Bridges & Tunnels. This gives us both absolute numbers and a built-in
    recovery metric (the pre-pandemic percentage), which makes cross-mode comparison
    straightforward.

    One limitation we've noticed is that the "comparable pre-pandemic day" metric can be noisy
    around holidays, since the comparison day may not perfectly match the current day's
    conditions. We handle this by using rolling averages for trend analysis instead of relying
    on individual daily values.

    We pull the data directly from the NYC Open Data API so the dashboard always reflects
    the most recent available data without needing manual updates.
    """)

    st.subheader("Methodology")
    st.markdown("""
    Our analysis approach includes the following:

    - **Recovery trend analysis:** We track the pre-pandemic percentage for each transit mode
      over time, using 7-day and 30-day rolling averages to smooth out daily fluctuations.
      This helps us identify the overall trajectory and any inflection points.

    - **Weekday vs. weekend comparison:** We categorize each day as weekday or weekend,
      then compare average ridership and recovery rates for each transit mode across these
      two groups. We also look at how this gap has changed year over year.

    - **Holiday and event impact:** We flag known holidays and major events in the data
      and examine ridership patterns in the days surrounding them. We compare holiday
      ridership to the surrounding week's average to quantify the impact.

    - **Cross-mode comparison:** We rank transit modes by their recovery rate and visualize
      them side by side. We also look at whether modes that serve different geographic areas
      or rider demographics have recovered differently.

    All visualizations use Plotly for interactivity, allowing users to zoom in on specific
    time periods, toggle transit modes on and off, and hover over data points for details.
    """)

    st.subheader("Preliminary Findings")
    st.markdown("""
    Based on our analysis so far, here are the key patterns we've identified:

    - **Commuter rail is recovering faster than subway and bus.** LIRR leads at 92% recovery,
      followed by Metro-North at 88%, while subway sits at 85%. This may reflect the
      return-to-office trend among suburban commuters and service improvements like Grand
      Central Madison.

    - **Bridges and tunnels traffic has fully recovered and then some**, currently at 105% of
      pre-pandemic levels. This suggests some riders may have permanently shifted from transit
      to driving, or that overall regional travel volume has increased.

    - **Weekend ridership recovery has been proportionally stronger than weekday ridership**
      for subway and bus, consistent with the shift toward remote and hybrid work reducing
      traditional weekday commuting.

    - **Paratransit demand has surged well beyond pre-pandemic levels** (161%), indicating
      growing need for accessible transit services that goes beyond simple pandemic recovery.

    - **Recovery is not linear.** There are clear seasonal dips (winter holidays, summer),
      and specific events like congestion pricing launch appear to have boosted transit
      ridership in early 2025.

    These findings are preliminary and will be refined as we build out the full dashboard
    with interactive visualizations.
    """)

    st.markdown("---")
    st.markdown("**Team bouncing-penguin:** Haixin Liu & Hanghai Li")
