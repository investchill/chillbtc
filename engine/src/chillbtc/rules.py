"""Signal rules R1, R2, R3.

Each rule takes a monthly DataFrame (with at least ``close_usd``,
``days_since_genesis``) and returns a Series of binary signals:
1 = BUY (long BTC), 0 = CASH (in USDC), NaN = signal undefined
(typically warmup periods).

The signals are then fed to ``metrics.equity_from_signals`` to build the
equity curve.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def signal_tsmom(monthly: pd.DataFrame, n: int = 12) -> pd.Series:
    """R1 — Time-Series Momentum.

    BUY (1) if the price return over the past ``n`` months is strictly
    positive, else CASH (0). The first ``n`` months are NaN.

    Reference: Moskowitz, Ooi, Pedersen, *Time Series Momentum*,
    Journal of Financial Economics, 2012.
    """
    return_n = monthly["close_usd"].pct_change(n)
    signal = pd.Series(np.nan, index=monthly.index, name="signal_tsmom")
    valid = return_n.notna()
    signal.loc[valid] = (return_n.loc[valid] > 0).astype(float)
    return signal


def _hysteresis_band(ratio: pd.Series, k_low: float, k_high: float) -> pd.Series:
    """Generic hysteresis-band classifier.

    Returns a binary Series: BUY (1) when ratio first dips below k_low,
    holds BUY until ratio rises above k_high, then switches to CASH (0).
    NaN ratios produce NaN signals (warmup).
    """
    states = pd.Series(np.nan, index=ratio.index)
    prev_state = 0
    for t, r in ratio.items():
        if pd.isna(r):
            states.loc[t] = np.nan
            continue
        if prev_state == 1:
            new_state = 0 if r > k_high else 1
        else:
            new_state = 1 if r < k_low else 0
        states.loc[t] = float(new_state)
        prev_state = new_state
    return states


def signal_mayer(
    monthly: pd.DataFrame,
    k_low: float = 1.0,
    k_high: float = 2.4,
    use_daily_sma200: bool = True,
    sma_window_months: int = 7,
) -> pd.Series:
    """R2 — Mayer Multiple band.

    Mayer Multiple = close / SMA200d (canonical) or = close / SMA(N months)
    (monthly approximation). Set ``use_daily_sma200=False`` to fall back to
    the monthly approximation; this is useful when the ``sma_200d`` column is
    not available in ``monthly``.

    Hysteresis: enter BUY when MM < k_low (accumulation zone), exit to CASH
    when MM > k_high (overheated zone). Default k_high = 2.4 is Mayer's
    historically backtested optimum.
    """
    if use_daily_sma200 and "sma_200d" in monthly.columns:
        sma = monthly["sma_200d"]
    else:
        sma = monthly["close_usd"].rolling(sma_window_months).mean()
    mm = monthly["close_usd"] / sma
    return _hysteresis_band(mm, k_low, k_high).rename("signal_mayer")


def fit_power_law(monthly: pd.DataFrame, n_exponent: float = 5.8) -> tuple[float, float]:
    """Fit the constant A in log10(price) = A + N * log10(days).

    Returns (a_constant, n_exponent_used). N is fixed (Santostasi's value
    by default); only A is calibrated as the mean residual.
    """
    days = monthly["days_since_genesis"].astype(float)
    log_days = np.log10(days.values)
    log_close = np.log10(monthly["close_usd"].values)
    a = float(np.mean(log_close - n_exponent * log_days))
    return a, n_exponent


def power_law_fair_value(
    monthly: pd.DataFrame,
    a_constant: float | None = None,
    n_exponent: float = 5.8,
) -> pd.Series:
    """Compute fair_PL(t) = 10 ^ (A + N * log10(days_since_genesis))."""
    if a_constant is None:
        a_constant, _ = fit_power_law(monthly, n_exponent)
    days = monthly["days_since_genesis"].astype(float)
    log_fair = a_constant + n_exponent * np.log10(days.values)
    return pd.Series(10**log_fair, index=monthly.index, name="fair_pl")


def signal_power_law(
    monthly: pd.DataFrame,
    k_low: float = 0.7,
    k_high: float = 2.0,
    n_exponent: float = 5.8,
    a_constant: float | None = None,
) -> pd.Series:
    """R3 — Power Law band (Santostasi).

    Hysteresis band on the ratio price / fair_PL. By default A is fitted
    from the full series (replaced by walk-forward training in Phase C).

    Reference: Santostasi, G., *The Bitcoin Power Law Theory*, Medium, 2018+.
    """
    fair = power_law_fair_value(monthly, a_constant, n_exponent)
    plm = monthly["close_usd"] / fair
    return _hysteresis_band(plm, k_low, k_high).rename("signal_power_law")
