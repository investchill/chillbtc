"""Performance metrics + signal-to-equity simulator.

Conventions:
- ``signals[t]`` is the signal computed at month-end ``t`` (binary 1=BUY, 0=CASH).
- The position taken effectively for month ``t+1`` is ``signals[t]``.
- A switch fires when ``signals[t-1] != signals[t-2]``, costing ``fee_per_switch``
  on the strategy return at month ``t``.
- Initial position is CASH (no position before any signal exists).
- NaN signals are treated as CASH (during warmup periods).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = 12  # monthly data


def cagr(equity: pd.Series) -> float:
    """Compound Annual Growth Rate, computed on the full equity series."""
    if len(equity) < 2:
        return 0.0
    n_years = (len(equity) - 1) / PERIODS_PER_YEAR
    if n_years <= 0:
        return 0.0
    ratio = equity.iloc[-1] / equity.iloc[0]
    if ratio <= 0:
        return 0.0
    return float(ratio ** (1 / n_years) - 1)


def max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown as a negative fraction (e.g. -0.75 for -75%)."""
    if len(equity) == 0:
        return 0.0
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    return float(drawdown.min())


def sharpe(returns: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Annualised Sharpe ratio with zero risk-free rate."""
    r = returns.dropna()
    if len(r) < 2 or r.std() == 0:
        return 0.0
    return float((r.mean() / r.std()) * np.sqrt(periods_per_year))


def equity_from_signals(
    monthly: pd.DataFrame,
    signals: pd.Series,
    fee_per_switch: float = 0.005,
    capital_init: float = 100.0,
) -> pd.Series:
    """Apply binary signals to the BTC monthly returns and return the equity curve."""
    btc_returns = monthly["close_usd"].pct_change()
    sig = signals.astype(float).fillna(0.0)
    position = sig.shift(1).fillna(0.0)
    prev_position = position.shift(1).fillna(0.0)
    is_switch = (position != prev_position).astype(float)
    strat_returns = position * btc_returns - is_switch * fee_per_switch
    strat_returns = strat_returns.fillna(0.0)
    equity = capital_init * (1 + strat_returns).cumprod()
    equity.name = "equity"
    return equity


def n_switches(signals: pd.Series) -> int:
    """Total number of BUY/CASH switches over the period."""
    sig = signals.astype(float).fillna(0.0)
    return int((sig.diff().abs() > 0).sum())


def summarize(
    equity: pd.Series,
    signals: pd.Series | None = None,
    name: str = "strategy",
) -> dict:
    """Compact dict summary used for printing and result tables."""
    returns = equity.pct_change()
    out: dict = {
        "name": name,
        "cagr_pct": round(cagr(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
        "final_equity": round(float(equity.iloc[-1]), 2),
    }
    if signals is not None:
        n = n_switches(signals)
        n_years = len(equity) / PERIODS_PER_YEAR
        out["n_switches"] = n
        out["switches_per_year"] = round(n / n_years, 2) if n_years > 0 else 0.0
    return out
