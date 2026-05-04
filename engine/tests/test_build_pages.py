"""Unit tests for build_pages.py — CAGR helpers used by the public pages.

Garde-fou de régression contre le bug off-by-one historique :
``_annualized_total`` doit diviser par ``(len-1)/12`` (nombre d'intervalles
mensuels) et non ``len/12`` (nombre de points), sinon le CAGR affiché est
sous-estimé d'environ 1/12 ans.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from chillbtc.build_pages import _annualized_n_years, _annualized_total


def test_annualized_total_one_year_exact_10pct():
    """Equity 1.0 → 1.10 sur 13 points (12 intervalles = 1 an) → CAGR 10 %."""
    idx = pd.date_range("2020-01-31", periods=13, freq="ME")
    equity = pd.Series([1.0 * (1.10 ** (i / 12)) for i in range(13)], index=idx)
    assert _annualized_total(equity) == pytest.approx(0.10, rel=1e-9)


def test_annualized_total_two_years_exact_44pct():
    """Equity 1.0 → 1.44 sur 25 points (24 intervalles = 2 ans) → CAGR 20 %."""
    idx = pd.date_range("2020-01-31", periods=25, freq="ME")
    equity = pd.Series([1.0 * (1.20 ** (i / 12)) for i in range(25)], index=idx)
    assert _annualized_total(equity) == pytest.approx(0.20, rel=1e-9)


def test_annualized_total_rejects_off_by_one_formula():
    """Régression-guard explicite : la formule fautive ``len/12`` doit donner
    un résultat différent du CAGR vrai sur une série non-triviale, sinon le
    test serait vacuous. On vérifie que l'implémentation NE matche PAS
    cette formule.
    """
    idx = pd.date_range("2015-10-31", periods=127, freq="ME")
    equity = pd.Series([1.0 * (1.50 ** (i / 12)) for i in range(127)], index=idx)
    # Formule correcte : 126 intervalles / 12 = 10.5 ans → CAGR exactement 50 %.
    assert _annualized_total(equity) == pytest.approx(0.50, rel=1e-9)
    # La formule fautive aurait donné un CAGR sensiblement plus bas.
    buggy = (equity.iloc[-1] / equity.iloc[0]) ** (1 / (len(equity) / 12)) - 1
    assert not math.isclose(_annualized_total(equity), buggy, rel_tol=1e-4)


def test_annualized_total_short_series_returns_nan():
    """Série de longueur < 2 → NaN (garde défensive)."""
    assert math.isnan(_annualized_total(pd.Series([1.0])))
    assert math.isnan(_annualized_total(pd.Series([], dtype=float)))


def test_annualized_n_years_three_year_window():
    """Equity géométrique 15 % sur 37 points → CAGR 3 ans = 15 %."""
    idx = pd.date_range("2020-01-31", periods=60, freq="ME")
    equity = pd.Series([1.0 * (1.15 ** (i / 12)) for i in range(60)], index=idx)
    assert _annualized_n_years(equity, 3) == pytest.approx(0.15, rel=1e-9)


def test_annualized_n_years_returns_none_when_too_short():
    """Si la série ne couvre pas 12*n_years intervalles, retour None."""
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    equity = pd.Series([1.0] * 24, index=idx)
    assert _annualized_n_years(equity, 3) is None
