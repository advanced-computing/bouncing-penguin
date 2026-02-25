import pandas as pd
import pytest
from utils import clean_mta_df

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