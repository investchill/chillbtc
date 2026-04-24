"""Unit tests for metrics.py — CAGR, max drawdown, Sharpe.

All tests use hand-computed reference values on short synthetic series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from chillbtc.metrics import cagr, max_drawdown, n_switches, sharpe


def test_cagr_one_year_10pct():
    """Equity from 100 to 110 over exactly 12 monthly steps → CAGR 10 %."""
    idx = pd.date_range("2020-01-31", periods=13, freq="ME")
    equity = pd.Series(np.linspace(100.0, 110.0, 13), index=idx)
    assert cagr(equity) == pytest.approx(0.10, rel=1e-6)


def test_cagr_short_series_returns_zero():
    equity = pd.Series([100.0])
    assert cagr(equity) == 0.0


def test_cagr_negative_equity_returns_zero():
    """Non-positive final ratio short-circuits to 0 (defensive)."""
    equity = pd.Series([100.0, 50.0, 0.0])
    assert cagr(equity) == 0.0


def test_max_drawdown_known_series():
    """[100, 120, 60, 90] → cummax [100,120,120,120] → min dd = (60-120)/120 = -0.5."""
    equity = pd.Series([100.0, 120.0, 60.0, 90.0])
    assert max_drawdown(equity) == pytest.approx(-0.5, rel=1e-9)


def test_max_drawdown_monotone_series_returns_zero():
    equity = pd.Series([100.0, 110.0, 121.0, 133.1])
    assert max_drawdown(equity) == 0.0


def test_sharpe_constant_returns_zero():
    """Zero-volatility returns → Sharpe ratio clamped to 0."""
    returns = pd.Series([0.01] * 24)
    assert sharpe(returns) == 0.0


def test_sharpe_short_series_returns_zero():
    returns = pd.Series([0.05])
    assert sharpe(returns) == 0.0


def test_n_switches_counts_transitions():
    sig = pd.Series([1.0, 1.0, 0.0, 0.0, 1.0, 0.0, 1.0])
    assert n_switches(sig) == 4
