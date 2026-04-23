"""Post-Phase-D what-if: simple "bottom detector" heuristics + entry-only HODL
comparison vs the frozen cascade (entry+exit).

Context
-------
Answers two questions from the explication note (section 10, ideas 1 and 4):

- Idea 1: do simple trader-style bottom detectors actually identify bottoms?
- Idea 4: what is the value of having an exit rule on top of a good entry?

Does NOT modify the live strategy. Uses the monthly BTC data already cached.

Detectors
---------
- D1_dd40           : BTC is ≤ -40 % below its trailing 12-month max
- D2_dd50           : BTC is ≤ -50 % below its trailing 12-month max
- D3_pl_bargain     : ratio price / Power Law fair value < 0.5
- D4_rsi_oversold   : 14-month RSI < 30

Power Law parameters (A, N) are the frozen-strategy values from
the frozen strategy (A = -16.917, N = 5.8).

Ex-post "true bottoms" used for proximity scoring: Dec 2018, Nov 2022,
with a ±3 month tolerance.

Entry-only strategy
-------------------
For each detector, build a single-switch strategy:
- CASH from the start of the evaluation window until the first trigger.
- BUY 100 % BTC at the first trigger's month-end, HODL forever after.
- One switch, one fee (0.5 %), no exit.

Comparison
----------
Entry-only vs cascade baseline vs HODL pure, on the cascade's evaluation
window 2016-05-31 → 2026-03-31 (monthly, 119 months).

Output
------
- ``engine/output/bottom_detector_summary.csv`` : per-detector stats
- ``engine/output/entry_only_vs_cascade.csv``   : per-strategy CAGR/DD/Sharpe
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from chillbtc.metrics import cagr, max_drawdown, sharpe

FEE_PER_SWITCH = 0.005
CAPITAL_INIT = 100.0
A_POWER_LAW = -16.917
N_POWER_LAW = 5.8

TRUE_BOTTOMS = [pd.Timestamp("2018-12-31"), pd.Timestamp("2022-11-30")]
TRUE_BOTTOM_TOLERANCE_MONTHS = 3


def compute_rsi_monthly(returns: pd.Series, period: int = 14) -> pd.Series:
    gains = returns.where(returns > 0, 0.0)
    losses = -returns.where(returns < 0, 0.0)
    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def compute_detectors(monthly: pd.DataFrame) -> pd.DataFrame:
    df = monthly.copy()
    df["trailing_ath_12m"] = df["close_usd"].rolling(window=12).max()
    df["pct_from_ath"] = df["close_usd"] / df["trailing_ath_12m"] - 1.0
    df["D1_dd40"] = df["pct_from_ath"] <= -0.40
    df["D2_dd50"] = df["pct_from_ath"] <= -0.50

    df["fair_pl"] = 10.0 ** (A_POWER_LAW + N_POWER_LAW * np.log10(df["days_since_genesis"]))
    df["pl_ratio"] = df["close_usd"] / df["fair_pl"]
    df["D3_pl_bargain"] = df["pl_ratio"] < 0.5

    df["rsi_14m"] = compute_rsi_monthly(df["return_1m"], period=14)
    df["D4_rsi_oversold"] = df["rsi_14m"] < 30
    return df


def months_diff(a: pd.Timestamp, b: pd.Timestamp) -> int:
    return abs((a.year - b.year) * 12 + (a.month - b.month))


def is_near_true_bottom(date: pd.Timestamp) -> bool:
    return any(months_diff(date, b) <= TRUE_BOTTOM_TOLERANCE_MONTHS for b in TRUE_BOTTOMS)


def evaluate_detector(df: pd.DataFrame, detector_col: str) -> dict:
    triggers = df.index[df[detector_col].fillna(False)]
    n_triggers = len(triggers)
    if n_triggers == 0:
        return {
            "detector": detector_col,
            "n_triggers": 0,
            "first_trigger": None,
            "last_trigger": None,
            "avg_fr_3m_pct": None,
            "avg_fr_6m_pct": None,
            "avg_fr_12m_pct": None,
            "avg_fr_24m_pct": None,
            "win_rate_12m_pct": None,
            "n_near_true_bottom": 0,
        }

    close = df["close_usd"]
    forward = {"3m": [], "6m": [], "12m": [], "24m": []}
    for t in triggers:
        i = df.index.get_loc(t)
        for label, n in (("3m", 3), ("6m", 6), ("12m", 12), ("24m", 24)):
            j = i + n
            if j < len(df):
                forward[label].append(float(close.iloc[j] / close.loc[t] - 1.0))

    def _avg(lst: list[float]) -> float | None:
        return round(float(np.mean(lst)) * 100, 2) if lst else None

    fr12 = forward["12m"]
    win_rate = (
        round(float(np.mean(np.array(fr12) > 0)) * 100, 2) if fr12 else None
    )
    near_true = sum(is_near_true_bottom(t) for t in triggers)

    return {
        "detector": detector_col,
        "n_triggers": int(n_triggers),
        "first_trigger": str(triggers.min().date()),
        "last_trigger": str(triggers.max().date()),
        "avg_fr_3m_pct": _avg(forward["3m"]),
        "avg_fr_6m_pct": _avg(forward["6m"]),
        "avg_fr_12m_pct": _avg(forward["12m"]),
        "avg_fr_24m_pct": _avg(forward["24m"]),
        "win_rate_12m_pct": win_rate,
        "n_near_true_bottom": int(near_true),
    }


def simulate_entry_only(
    df: pd.DataFrame,
    detector_col: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    fee: float = FEE_PER_SWITCH,
    capital_init: float = CAPITAL_INIT,
) -> tuple[pd.Series | None, pd.Timestamp | None]:
    window = df.loc[start:end]
    fires = window.index[window[detector_col].fillna(False)]
    if len(fires) == 0:
        equity = pd.Series(capital_init, index=window.index, name="equity")
        return equity, None

    first_trigger = fires[0]
    position = pd.Series(0.0, index=window.index)
    position.loc[first_trigger:] = 1.0

    btc_returns = window["close_usd"].pct_change().fillna(0.0)
    prev_pos = position.shift(1).fillna(0.0)
    is_switch = (position != prev_pos).astype(float)
    strat_ret = prev_pos * btc_returns - is_switch * fee
    equity = capital_init * (1.0 + strat_ret).cumprod()
    equity.name = "equity"
    return equity, first_trigger


def metrics_of(equity: pd.Series) -> dict:
    returns = equity.pct_change()
    return {
        "cagr_pct": round(cagr(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
        "final_equity": round(float(equity.iloc[-1]), 2),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    monthly = (
        pd.read_csv(root / "data" / "btc_monthly.csv", parse_dates=["date"], index_col="date")
        .dropna(subset=["close_usd"])
        .sort_index()
    )
    df = compute_detectors(monthly)

    print("=" * 88)
    print("PART 1 — Detector quality (forward returns + proximity to true cycle bottoms)")
    print("=" * 88)
    detector_rows = []
    for col in ["D1_dd40", "D2_dd50", "D3_pl_bargain", "D4_rsi_oversold"]:
        r = evaluate_detector(df, col)
        detector_rows.append(r)
        print(f"\n{col}")
        print(f"  n_triggers (over {df.index.min().date()} → {df.index.max().date()}) : {r['n_triggers']}")
        print(f"  first_trigger    : {r['first_trigger']}")
        print(f"  last_trigger     : {r['last_trigger']}")
        print(f"  avg fwd return 3m  : {r['avg_fr_3m_pct']} %")
        print(f"  avg fwd return 6m  : {r['avg_fr_6m_pct']} %")
        print(f"  avg fwd return 12m : {r['avg_fr_12m_pct']} %")
        print(f"  avg fwd return 24m : {r['avg_fr_24m_pct']} %")
        print(f"  win rate 12m      : {r['win_rate_12m_pct']} %")
        print(f"  near true bottom  : {r['n_near_true_bottom']} / {r['n_triggers']}  (within ±3m of Dec 2018 or Nov 2022)")

    cascade_csv = root / "output" / "cascade_position.csv"
    cascade = pd.read_csv(cascade_csv, parse_dates=["date"]).set_index("date")
    eval_start = cascade.index.min()
    eval_end = cascade.index.max()

    print("\n" + "=" * 88)
    print(f"PART 2 — Entry-only HODL vs cascade baseline  ({eval_start.date()} → {eval_end.date()})")
    print("=" * 88)

    comparison_rows = []

    for col in ["D1_dd40", "D2_dd50", "D3_pl_bargain", "D4_rsi_oversold"]:
        equity, first_trigger = simulate_entry_only(df, col, eval_start, eval_end)
        m = metrics_of(equity)
        m["strategy"] = f"entry_only_{col}"
        m["first_trigger_in_window"] = str(first_trigger.date()) if first_trigger else "never"
        comparison_rows.append(m)

    hodl_close = df["close_usd"].loc[eval_start:eval_end]
    hodl_equity = CAPITAL_INIT * (hodl_close / hodl_close.iloc[0])
    m_hodl = metrics_of(hodl_equity)
    m_hodl["strategy"] = "hodl_reference"
    m_hodl["first_trigger_in_window"] = str(eval_start.date())
    comparison_rows.append(m_hodl)

    cascade_eq = cascade["equity_cascade"]
    m_cascade = metrics_of(cascade_eq)
    m_cascade["strategy"] = "cascade_baseline"
    m_cascade["first_trigger_in_window"] = str(eval_start.date())
    comparison_rows.append(m_cascade)

    header = f"{'strategy':<30}  {'first_entry':<13}  {'CAGR':>7}  {'max_DD':>8}  {'Sharpe':>7}  {'final':>9}"
    print(f"\n{header}")
    print("-" * len(header))
    for m in comparison_rows:
        print(
            f"{m['strategy']:<30}  {m['first_trigger_in_window']:<13}  "
            f"{m['cagr_pct']:>6.2f}%  {m['max_dd_pct']:>7.2f}%  "
            f"{m['sharpe']:>7.3f}  {m['final_equity']:>9.0f}"
        )

    summary_df = pd.DataFrame(detector_rows)
    summary_df.to_csv(root / "output" / "bottom_detector_summary.csv", index=False)
    compare_df = pd.DataFrame(comparison_rows)
    compare_df.to_csv(root / "output" / "entry_only_vs_cascade.csv", index=False)

    print(f"\nSaved: {root / 'output' / 'bottom_detector_summary.csv'}")
    print(f"Saved: {root / 'output' / 'entry_only_vs_cascade.csv'}")


if __name__ == "__main__":
    main()
