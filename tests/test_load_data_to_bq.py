import pandas as pd
import pytest

from load_data_to_bq import DATA_SOURCES, validate_source_frame


def _valid_mta_frame(row_count: int = 1001) -> pd.DataFrame:
    dates = pd.date_range("2020-03-01", periods=row_count, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "subways_total_estimated_ridership": [1000000.0] * row_count,
            "subways_pct_of_comparable_pre_pandemic_day": [0.6] * row_count,
            "buses_total_estimated_ridership": [500000.0] * row_count,
            "buses_pct_of_comparable_pre_pandemic_day": [0.7] * row_count,
        }
    )


def test_validate_source_frame_accepts_complete_data():
    validate_source_frame(_valid_mta_frame(), DATA_SOURCES["mta"])


def test_validate_source_frame_rejects_missing_required_columns():
    df = _valid_mta_frame().drop(columns=["date"])

    with pytest.raises(RuntimeError, match="missing required columns"):
        validate_source_frame(df, DATA_SOURCES["mta"])


def test_validate_source_frame_warns_on_missing_optional_column(capsys):
    df = _valid_mta_frame().drop(columns=["buses_total_estimated_ridership"])

    validate_source_frame(df, DATA_SOURCES["mta"])

    out = capsys.readouterr().out
    assert "buses_total_estimated_ridership" in out
    assert "WARNING" in out


def test_validate_source_frame_rejects_too_few_rows():
    df = _valid_mta_frame(row_count=10)

    with pytest.raises(RuntimeError, match="expected at least"):
        validate_source_frame(df, DATA_SOURCES["mta"])


def test_validate_source_frame_rejects_late_start_date():
    df = _valid_mta_frame()
    df["date"] = pd.date_range("2021-01-01", periods=len(df), freq="D")

    with pytest.raises(RuntimeError, match="should include data"):
        validate_source_frame(df, DATA_SOURCES["mta"])
