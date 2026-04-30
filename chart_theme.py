"""Unified Plotly theme for Bouncing Penguin dashboard."""

PENGUIN_PALETTE = [
    "#1E5BA8",
    "#F39C5C",
    "#5BA9DD",
    "#1F3464",
    "#B9D9EB",
    "#0F8B8D",
    "#9B6B9E",
]

PENGUIN_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#0F1419", size=13),
    colorway=PENGUIN_PALETTE,
    xaxis=dict(gridcolor="#E8EDF3", zerolinecolor="#E8EDF3"),
    yaxis=dict(gridcolor="#E8EDF3", zerolinecolor="#E8EDF3"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    hoverlabel=dict(bgcolor="#1F3464", font=dict(color="#FFFFFF", family="Inter")),
)


def apply_penguin_theme(fig):
    """Apply Bouncing Penguin theme to a Plotly figure (in-place)."""
    fig.update_layout(**PENGUIN_LAYOUT)
    return fig
