import pandas as pd
import pytest
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for testing
from utils import clean_mta_df, plot_ridership_recovery

def test_clean_mta_df_converts_date_and_sorts():
    df = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-01"],
        "x": [2, 1],
    })

    out = clean_mta_df(df)

    assert str(out["date"].dtype).startswith("datetime64")

    assert out["date"].is_monotonic_increasing

    assert list(out["x"]) == [1, 2]

def test_clean_mta_df_missing_date_raises():
    df = pd.DataFrame({"x": [1, 2]})
    with pytest.raises(KeyError):
        clean_mta_df(df)

def test_clean_mta_df_does_not_modify_original():
    """Test that the original DataFrame is not mutated."""
    df = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-01"],
        "x": [2, 1],
    })
    original_dates = list(df["date"])

    clean_mta_df(df)

    # original df should remain unchanged
    assert list(df["date"]) == original_dates


def test_clean_mta_df_already_sorted():
    """Test that already-sorted data passes through correctly."""
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-01-02", "2020-01-03"],
        "x": [1, 2, 3],
    })

    out = clean_mta_df(df)

    assert out["date"].is_monotonic_increasing
    assert list(out["x"]) == [1, 2, 3]


# ---------- Tests for plot_ridership_recovery ----------

def _make_ridership_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2020-03-01", "2020-03-02", "2020-03-03"]),
        "subways_pct_of_comparable_pre_pandemic_day": [0.9, 0.5, 0.6],
        "buses_pct_of_comparable_pre_pandemic_day": [1.05, 0.6, 0.7],
        "lirr_pct_of_comparable_pre_pandemic_day": [0.8, 0.4, 0.5],
        "metro_north_pct_of_comparable_pre_pandemic_day": [0.88, 0.45, 0.55],
    })

def test_plot_ridership_recovery_returns_figure():
    """Test that the function returns a matplotlib Figure without error."""
    df = _make_ridership_df()
    fig = plot_ridership_recovery(df)
    assert isinstance(fig, matplotlib.figure.Figure)
    matplotlib.pyplot.close(fig)


def test_plot_ridership_recovery_missing_column_raises():
    """Test that KeyError is raised when a required column is missing."""
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-03-01"]),
        "subways_of_comparable_pre_pandemic_day": [0.9],
    })
    with pytest.raises(KeyError):
        plot_ridership_recovery(df)