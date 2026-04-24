"""Unit tests for R1 / R3 signal primitives.

R1 tests assert the sign of the 11-month return on four historically
unambiguous months (bull 2017-12, bear 2018-12, bull 2020-12, bear
2022-06). R3 tests validate the Power Law fair-value formula and the
hysteresis-band state machine on a synthetic ratio series.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from chillbtc.rules import (
    _hysteresis_band,
    fit_power_law,
    power_law_fair_value,
    signal_power_law,
    signal_tsmom,
)

# ----- R1 — Time-Series Momentum (n = 11) ---------------------------------

def test_signal_tsmom_bull_2017_12(monthly_series):
    sig = signal_tsmom(monthly_series, n=11)
    assert sig.loc["2017-12-31"] == 1.0


def test_signal_tsmom_bear_2018_12(monthly_series):
    sig = signal_tsmom(monthly_series, n=11)
    assert sig.loc["2018-12-31"] == 0.0


def test_signal_tsmom_bull_2020_12(monthly_series):
    sig = signal_tsmom(monthly_series, n=11)
    assert sig.loc["2020-12-31"] == 1.0


def test_signal_tsmom_bear_2022_06(monthly_series):
    sig = signal_tsmom(monthly_series, n=11)
    assert sig.loc["2022-06-30"] == 0.0


def test_signal_tsmom_warmup_nan(monthly_series):
    sig = signal_tsmom(monthly_series, n=11)
    assert sig.iloc[:11].isna().all()
    assert not sig.iloc[11:].isna().any()


# ----- R3 — Power Law fair value ------------------------------------------

def test_power_law_fair_value_known_point():
    """fair_PL(days=3284) with A=-16.917, N=5.8 equals 10^(A + N*log10(3284))."""
    df = pd.DataFrame({"close_usd": [13880.0], "days_since_genesis": [3284]})
    fair = power_law_fair_value(df, a_constant=-16.917, n_exponent=5.8)
    expected = 10 ** (-16.917 + 5.8 * math.log10(3284))
    assert fair.iloc[0] == pytest.approx(expected, rel=1e-9)


def test_fit_power_law_returns_finite_constant(monthly_series):
    a, n = fit_power_law(monthly_series, n_exponent=5.8)
    assert math.isfinite(a)
    assert n == 5.8


# ----- R3 — hysteresis band state machine ---------------------------------

def test_hysteresis_band_entry_and_exit():
    """From CASH: enter BUY when ratio dips below k_low; exit when above k_high."""
    ratio = pd.Series([np.nan, 0.5, 0.5, 0.8, 1.5, 2.1, 2.6, 2.3, 1.9, 0.5])
    out = _hysteresis_band(ratio, k_low=0.6, k_high=2.5)
    expected = [np.nan, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    for got, want in zip(out.tolist(), expected, strict=True):
        if pd.isna(want):
            assert pd.isna(got)
        else:
            assert got == want


def test_hysteresis_band_threshold_is_strict():
    """r == k_low should NOT re-enter BUY (strict inequality)."""
    ratio = pd.Series([np.nan, 0.8, 2.6, 0.6])  # 0.6 is k_low, strict <
    out = _hysteresis_band(ratio, k_low=0.6, k_high=2.5)
    assert out.iloc[-1] == 0.0


def test_signal_power_law_returns_named_series(monthly_series):
    sig = signal_power_law(
        monthly_series, k_low=0.6, k_high=2.5, n_exponent=5.8, a_constant=-16.917
    )
    assert sig.name == "signal_power_law"
    assert sig.index.equals(monthly_series.index)
