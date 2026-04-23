"""Post-Phase-D what-if: adding stop-loss / break-even / take-profit overlays
on top of the frozen cascade (R1 defensive + R3 aggressive, 100/50/0 dosing).

Context
-------
Answers the question a trader friend asks: "Your monthly cascade has no SL,
no BE, no TP — that's reckless, right?". This script runs the same 10-year
backtest as the frozen strategy, but layered with classic intra-month
risk-management overlays, so we can compare empirically.

Does NOT touch the live strategy. Uses daily BTC close (Bitstamp via CDD) and
the frozen monthly cascade positions from ``cascade_position.csv``.

Overlay rules tested
--------------------
- baseline       : no overlay (reference)
- SL_{20,30,40}  : stop-loss at -20/-30/-40 % below entry price
- BE_{30,50}     : once +30/+50 % profit is reached, lock SL at entry
- TP_{100,200}   : take-profit at +100/+200 % above entry price

Execution rules
---------------
- Cascade reads the monthly signal on every month-end date (even if the
  position did not change); resets overlay state.
- Overlay triggers are checked on every intra-month daily close, using the
  tracked entry price of the currently held leg.
- When overlay fires, position goes to 0 and stays there until the next
  month-end (classic "wait for next signal" rule).
- Entry price on a cascade add (0 → 0.5, 0 → 1, 0.5 → 1) is set to the
  month-end daily close, with weighted averaging on partial adds.
- Fees: 0.5 % per unit of ``|Δposition|`` per switch (matches cascade.py).

Output
------
- ``engine/output/sl_be_tp_experiment.csv`` : one row per variant, columns
  CAGR, max DD, Sharpe (annualised daily), final equity, overlay fires,
  total switches, switches/year.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from chillbtc.data import fetch_bitstamp_daily

FEE_PER_SWITCH = 0.005
CAPITAL_INIT = 100.0
TRADING_DAYS_PER_YEAR = 365  # BTC trades 7 days a week


@dataclass
class OverlayResult:
    new_position: float
    new_be_locked: bool


OverlayFn = Callable[[float, float | None, float, bool], OverlayResult]


def overlay_baseline(pos: float, entry: float | None, price: float, be_locked: bool) -> OverlayResult:
    return OverlayResult(pos, be_locked)


def make_overlay_sl(sl_pct: float) -> OverlayFn:
    def fn(pos, entry, price, be_locked):
        if entry is None or pos <= 0:
            return OverlayResult(pos, be_locked)
        if price / entry - 1.0 <= -sl_pct:
            return OverlayResult(0.0, be_locked)
        return OverlayResult(pos, be_locked)
    return fn


def make_overlay_tp(tp_pct: float) -> OverlayFn:
    def fn(pos, entry, price, be_locked):
        if entry is None or pos <= 0:
            return OverlayResult(pos, be_locked)
        if price / entry - 1.0 >= tp_pct:
            return OverlayResult(0.0, be_locked)
        return OverlayResult(pos, be_locked)
    return fn


def make_overlay_be(trigger_pct: float) -> OverlayFn:
    def fn(pos, entry, price, be_locked):
        if entry is None or pos <= 0:
            return OverlayResult(pos, be_locked)
        gain = price / entry - 1.0
        new_lock = be_locked or (gain >= trigger_pct)
        if new_lock and price <= entry:
            return OverlayResult(0.0, new_lock)
        return OverlayResult(pos, new_lock)
    return fn


def simulate_overlay(
    daily_close: pd.Series,
    cascade_monthly_signal: pd.Series,
    overlay_fn: OverlayFn,
    fee: float = FEE_PER_SWITCH,
    capital_init: float = CAPITAL_INIT,
) -> pd.DataFrame:
    """Return a daily DataFrame (close, effective_position, entry_price,
    switch_magnitude, overlay_fired, strat_return, equity)."""
    monthly_set = set(cascade_monthly_signal.index.to_pydatetime().tolist())
    n = len(daily_close)
    dates = daily_close.index
    prices = daily_close.values

    is_month_end_day = np.array([d.to_pydatetime() in monthly_set for d in dates])

    effective = np.zeros(n)
    entry_prices_out = np.zeros(n)
    switches = np.zeros(n)
    overlay_fires = np.zeros(n, dtype=bool)

    cur_pos = 0.0
    cur_entry: float | None = None
    be_locked = False
    overlay_blocked_this_month = False

    for i in range(n):
        price_today = float(prices[i])

        if is_month_end_day[i]:
            target = float(cascade_monthly_signal.loc[dates[i]])
            overlay_blocked_this_month = False
            be_locked = False
            if target != cur_pos:
                switches[i] = abs(target - cur_pos)
                if target == 0:
                    cur_entry = None
                elif cur_pos == 0:
                    cur_entry = price_today
                elif target > cur_pos:
                    # add to position — weighted avg
                    assert cur_entry is not None
                    cur_entry = (cur_entry * cur_pos + price_today * (target - cur_pos)) / target
                # target < cur_pos and target > 0: partial sell, keep entry
                cur_pos = target
                if cur_pos == 0:
                    cur_entry = None
        else:
            if cur_pos > 0 and not overlay_blocked_this_month and cur_entry is not None:
                r = overlay_fn(cur_pos, cur_entry, price_today, be_locked)
                be_locked = r.new_be_locked
                if r.new_position != cur_pos:
                    switches[i] = abs(r.new_position - cur_pos)
                    overlay_fires[i] = True
                    cur_pos = r.new_position
                    if cur_pos == 0:
                        cur_entry = None
                        overlay_blocked_this_month = True

        effective[i] = cur_pos
        entry_prices_out[i] = cur_entry if cur_entry is not None else 0.0

    daily_returns = daily_close.pct_change().fillna(0.0).values
    prev_pos = np.concatenate([[0.0], effective[:-1]])
    strat_ret = prev_pos * daily_returns - switches * fee
    equity = capital_init * np.cumprod(1.0 + strat_ret)

    return pd.DataFrame(
        {
            "close": prices,
            "effective_position": effective,
            "entry_price": entry_prices_out,
            "switch_magnitude": switches,
            "overlay_fired": overlay_fires,
            "strat_return": strat_ret,
            "equity": equity,
        },
        index=dates,
    )


def simulate_hodl(daily_close: pd.Series, capital_init: float = CAPITAL_INIT) -> pd.DataFrame:
    daily_returns = daily_close.pct_change().fillna(0.0)
    equity = capital_init * (1.0 + daily_returns).cumprod()
    return pd.DataFrame({"close": daily_close, "equity": equity})


def compute_metrics(equity: pd.Series) -> dict:
    n_days = (equity.index[-1] - equity.index[0]).days
    n_years = n_days / 365.25 if n_days > 0 else 1.0
    ratio = float(equity.iloc[-1] / equity.iloc[0])
    cagr_val = ratio ** (1.0 / n_years) - 1.0 if ratio > 0 else 0.0

    rolling_max = equity.cummax()
    max_dd_val = float(((equity - rolling_max) / rolling_max).min())

    returns = equity.pct_change().dropna()
    if returns.std() > 0:
        sharpe_val = float((returns.mean() / returns.std()) * math.sqrt(TRADING_DAYS_PER_YEAR))
    else:
        sharpe_val = 0.0

    return {
        "cagr_pct": round(cagr_val * 100, 2),
        "max_dd_pct": round(max_dd_val * 100, 2),
        "sharpe_daily_annualised": round(sharpe_val, 3),
        "final_equity": round(float(equity.iloc[-1]), 2),
    }


def main() -> pd.DataFrame:
    root = Path(__file__).resolve().parents[2]
    cache_daily = root / "data" / "btc_daily.csv"

    if cache_daily.exists():
        daily = pd.read_csv(cache_daily, parse_dates=["date"], index_col="date")
        print(f"Loaded daily cache: {len(daily)} rows, {daily.index.min().date()} → {daily.index.max().date()}")
    else:
        print("Fetching Bitstamp daily (one-off)…")
        daily = fetch_bitstamp_daily()
        cache_daily.parent.mkdir(parents=True, exist_ok=True)
        daily.to_csv(cache_daily)
        print(f"Cached: {cache_daily}")

    daily_close = daily["close_usd"].sort_index()

    cascade_csv = root / "output" / "cascade_position.csv"
    cascade = pd.read_csv(cascade_csv, parse_dates=["date"])
    cascade_monthly_signal = cascade.set_index("date")["position"].astype(float)

    start = cascade_monthly_signal.index.min()
    end = cascade_monthly_signal.index.max()
    daily_close = daily_close.loc[(daily_close.index >= start) & (daily_close.index <= end)]

    print(f"Simulation window: {daily_close.index.min().date()} → {daily_close.index.max().date()}  "
          f"({len(daily_close)} daily points)")

    variants: dict[str, OverlayFn] = {
        "baseline_cascade": overlay_baseline,
        "SL_20": make_overlay_sl(0.20),
        "SL_30": make_overlay_sl(0.30),
        "SL_40": make_overlay_sl(0.40),
        "BE_trigger_30": make_overlay_be(0.30),
        "BE_trigger_50": make_overlay_be(0.50),
        "TP_100": make_overlay_tp(1.00),
        "TP_200": make_overlay_tp(2.00),
    }

    rows = []
    for name, fn in variants.items():
        df = simulate_overlay(daily_close, cascade_monthly_signal, fn)
        m = compute_metrics(df["equity"])
        n_fires = int(df["overlay_fired"].sum())
        n_switches = int((df["switch_magnitude"] > 0).sum())
        n_years = (df.index[-1] - df.index[0]).days / 365.25
        rows.append(
            {
                "variant": name,
                "cagr_pct": m["cagr_pct"],
                "max_dd_pct": m["max_dd_pct"],
                "sharpe_daily_annualised": m["sharpe_daily_annualised"],
                "final_equity": m["final_equity"],
                "n_overlay_fires": n_fires,
                "n_switches_total": n_switches,
                "switches_per_year": round(n_switches / n_years, 2),
            }
        )

    hodl_df = simulate_hodl(daily_close)
    mh = compute_metrics(hodl_df["equity"])
    rows.append(
        {
            "variant": "hodl",
            "cagr_pct": mh["cagr_pct"],
            "max_dd_pct": mh["max_dd_pct"],
            "sharpe_daily_annualised": mh["sharpe_daily_annualised"],
            "final_equity": mh["final_equity"],
            "n_overlay_fires": 0,
            "n_switches_total": 0,
            "switches_per_year": 0.0,
        }
    )

    out_df = pd.DataFrame(rows)
    out_csv = root / "output" / "sl_be_tp_experiment.csv"
    out_df.to_csv(out_csv, index=False)

    print("\n=== Summary ===")
    print(out_df.to_string(index=False))
    print(f"\nSaved: {out_csv}")

    return out_df


if __name__ == "__main__":
    main()
