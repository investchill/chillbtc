"""Shared fixtures for the ChillBTC test suite."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(scope="session")
def monthly_series() -> pd.DataFrame:
    """Load the committed monthly BTC OHLC cache.

    Returned DataFrame is indexed by end-of-month Timestamp and carries at
    least ``close_usd`` and ``days_since_genesis``.
    """
    cache = Path(__file__).resolve().parents[1] / "data" / "btc_monthly.csv"
    df = pd.read_csv(cache, parse_dates=["date"], index_col="date")
    return df
