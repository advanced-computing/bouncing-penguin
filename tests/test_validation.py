import pandas as pd
import pandera as pa
import pytest

from validation import validate_mta_data


def test_valid_data():
    """Test that valid data passes validation."""
    df = pd.DataFrame(
        {
            "date": ["2020-03-01", "2020-03-02"],
            "subways_total_estimated_ridership": [1000000.0, 1100000.0],
            "subways_of_comparable_pre_pandemic_day": [0.5, 0.6],
            "buses_total_estimated_ridership": [500000.0, 550000.0],
            "buses_of_comparable_pre_pandemic_day": [0.6, 0.65],
            "lirr_total_estimated_ridership": [100000.0, 110000.0],
            "lirr_of_comparable_pre_pandemic_day": [0.4, 0.45],
            "metro_north_total_estimated_ridership": [80000.0, 85000.0],
            "metro_north_of_comparable_pre_pandemic_day": [0.35, 0.4],
            "bridges_and_tunnels_total_traffic": [700000.0, 720000.0],
            "bridges_and_tunnels_of_comparable_pre_pandemic_day": [0.9, 0.92],
        }
    )
    result = validate_mta_data(df)
    assert len(result) == 2


def test_valid_current_column_names():
    """Test that current _pct_ recovery column names pass validation."""
    df = pd.DataFrame(
        {
            "date": ["2020-03-01"],
            "subways_total_estimated_ridership": [1000000.0],
            "subways_pct_of_comparable_pre_pandemic_day": [0.5],
            "buses_total_estimated_ridership": [500000.0],
            "buses_pct_of_comparable_pre_pandemic_day": [0.6],
            "lirr_total_estimated_ridership": [100000.0],
            "lirr_pct_of_comparable_pre_pandemic_day": [0.4],
            "metro_north_total_estimated_ridership": [80000.0],
            "metro_north_pct_of_comparable_pre_pandemic_day": [0.35],
            "bridges_and_tunnels_total_traffic": [700000.0],
            "bridges_and_tunnels_pct_of_comparable_pre_pandemic_day": [0.9],
        }
    )
    result = validate_mta_data(df)
    assert len(result) == 1


def test_negative_ridership_fails():
    """Test that negative ridership values fail validation."""
    df = pd.DataFrame(
        {
            "date": ["2020-03-01"],
            "subways_total_estimated_ridership": [-100.0],
            "subways_of_comparable_pre_pandemic_day": [0.5],
            "buses_total_estimated_ridership": [500000.0],
            "buses_of_comparable_pre_pandemic_day": [0.6],
            "lirr_total_estimated_ridership": [100000.0],
            "lirr_of_comparable_pre_pandemic_day": [0.4],
            "metro_north_total_estimated_ridership": [80000.0],
            "metro_north_of_comparable_pre_pandemic_day": [0.35],
            "bridges_and_tunnels_total_traffic": [700000.0],
            "bridges_and_tunnels_of_comparable_pre_pandemic_day": [0.9],
        }
    )
    with pytest.raises(pa.errors.SchemaError):
        validate_mta_data(df)


def test_ratio_exceeds_max_fails():
    """Test that pre-pandemic ratio > 2.0 fails validation."""
    df = pd.DataFrame(
        {
            "date": ["2020-03-01"],
            "subways_total_estimated_ridership": [1000000.0],
            "subways_of_comparable_pre_pandemic_day": [3.0],
            "buses_total_estimated_ridership": [500000.0],
            "buses_of_comparable_pre_pandemic_day": [0.6],
            "lirr_total_estimated_ridership": [100000.0],
            "lirr_of_comparable_pre_pandemic_day": [0.4],
            "metro_north_total_estimated_ridership": [80000.0],
            "metro_north_of_comparable_pre_pandemic_day": [0.35],
            "bridges_and_tunnels_total_traffic": [700000.0],
            "bridges_and_tunnels_of_comparable_pre_pandemic_day": [0.9],
        }
    )
    with pytest.raises(pa.errors.SchemaError):
        validate_mta_data(df)


def test_missing_date_fails():
    """Test that null dates fail validation."""
    df = pd.DataFrame(
        {
            "date": [None],
            "subways_total_estimated_ridership": [1000000.0],
            "subways_of_comparable_pre_pandemic_day": [0.5],
            "buses_total_estimated_ridership": [500000.0],
            "buses_of_comparable_pre_pandemic_day": [0.6],
            "lirr_total_estimated_ridership": [100000.0],
            "lirr_of_comparable_pre_pandemic_day": [0.4],
            "metro_north_total_estimated_ridership": [80000.0],
            "metro_north_of_comparable_pre_pandemic_day": [0.35],
            "bridges_and_tunnels_total_traffic": [700000.0],
            "bridges_and_tunnels_of_comparable_pre_pandemic_day": [0.9],
        }
    )
    with pytest.raises(pa.errors.SchemaError):
        validate_mta_data(df)
