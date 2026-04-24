"""Unit tests for the cascade position builder.

``build_cascade_position`` is a pure function over two binary Series,
so we test all four (def, agg) cells for each of the three supported
conventions (``strict_r1_def``, ``symmetric``, ``strict_r3_def``).
"""

from __future__ import annotations

import pandas as pd
import pytest

from chillbtc.cascade import build_cascade_position


def _sig(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-31", periods=len(values), freq="ME")
    return pd.Series(values, index=idx, dtype=float)


# ----- strict_r1_def (convention retenue) ---------------------------------

def test_strict_r1_def_both_buy_returns_full():
    pos = build_cascade_position(_sig([1.0]), _sig([1.0]), convention="strict_r1_def")
    assert pos.iloc[0] == 1.0


def test_strict_r1_def_both_cash_returns_zero():
    pos = build_cascade_position(_sig([0.0]), _sig([0.0]), convention="strict_r1_def")
    assert pos.iloc[0] == 0.0


def test_strict_r1_def_only_agg_buy_returns_half():
    """R1 CASH + R3 BUY → 50 % (pré-alerte tendance)."""
    pos = build_cascade_position(_sig([0.0]), _sig([1.0]), convention="strict_r1_def")
    assert pos.iloc[0] == 0.5


def test_strict_r1_def_edge_only_def_buy_returns_zero():
    """Edge case R1 BUY + R3 CASH : R3 CASH prime → 0 %."""
    pos = build_cascade_position(_sig([1.0]), _sig([0.0]), convention="strict_r1_def")
    assert pos.iloc[0] == 0.0


# ----- symmetric ----------------------------------------------------------

def test_symmetric_any_disagreement_returns_half():
    pos = build_cascade_position(_sig([1.0, 0.0]), _sig([0.0, 1.0]), convention="symmetric")
    assert pos.iloc[0] == 0.5
    assert pos.iloc[1] == 0.5


# ----- strict_r3_def ------------------------------------------------------

def test_strict_r3_def_swaps_edge():
    """R3 devient défensif : R1 BUY + R3 CASH → 0.5, R1 CASH + R3 BUY → 0.0."""
    pos = build_cascade_position(_sig([1.0, 0.0]), _sig([0.0, 1.0]), convention="strict_r3_def")
    assert pos.iloc[0] == 0.5
    assert pos.iloc[1] == 0.0


# ----- unknown convention -------------------------------------------------

def test_unknown_convention_raises():
    with pytest.raises(ValueError, match="unknown convention"):
        build_cascade_position(_sig([1.0]), _sig([1.0]), convention="not_a_mode")


def test_nan_signals_are_treated_as_cash():
    """Warmup NaN on either signal collapses to CASH state, position = 0."""
    pos = build_cascade_position(_sig([float("nan")]), _sig([1.0]), convention="strict_r1_def")
    assert pos.iloc[0] == 0.5  # NaN def → 0 (CASH) + agg BUY = only_agg_buy → 0.5
