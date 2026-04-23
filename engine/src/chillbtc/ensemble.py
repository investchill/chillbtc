"""Phase D — ensemble K/9 over the Latin square.

Each of the nine cells (S1..S9) is calibrated on its own objective (CAGR / DD /
Sharpe) by its own optimisation protocol (O1 / O2 / O3). The ensemble signal at
month t is 1 (BUY) iff at least K of the nine cells emit BUY at t, 0 (CASH)
otherwise. The sweep reports the ensemble performance for K = 1..9 on the
same trimmed monthly window as Phase C (`2016-05 → 2026-03`).

The purpose is diagnostic: compare the ensemble at each K with HODL and with
the best-of-9 individual cells on (CAGR, DD, Sharpe, switches/an), with no
a-priori KPI ranking. The final sélection-vs-ensemble decision is deferred to
the frozen strategy doc.

Outputs:
- ``engine/output/ensemble_sweep.csv``   : one row per K in 1..9 + HODL row.
- ``engine/output/ensemble_signals.csv`` : per-month signals (S1..S9 + votes
  K=1..9), useful for audit and for a future dashboard.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chillbtc.backtest import (
    FEE_CONSERVATIVE,
    LATIN_SQUARE,
    OPTIM_FNS,
    SPECS,
    Cell,
    _hodl_perf,
    _trim_common_warmup,
)
from chillbtc.data import load_or_fetch
from chillbtc.metrics import (
    PERIODS_PER_YEAR,
    cagr,
    equity_from_signals,
    max_drawdown,
    n_switches,
    sharpe,
)


def _cell_signal(cell: Cell, monthly: pd.DataFrame, fee: float) -> tuple[pd.Series, dict]:
    """Run the cell's optimiser and regenerate its monthly BUY/CASH signal.

    Extras (R3's fitted A, n) are refit on the full trimmed history, consistent
    with the "final perf" convention used by run_O2 / run_O3 in optims.py.
    """
    spec = SPECS[cell.rule_name]
    fn = OPTIM_FNS[cell.optim_name]
    result = fn(spec, monthly, cell.objective, fee)
    extras = spec.fit_on_train(monthly) if spec.fit_on_train is not None else {}
    signal = spec.rule_fn(monthly, **{**result["params"], **extras})
    signal.name = cell.cell_id
    summary = {
        "cell_id": cell.cell_id,
        "rule": cell.rule_name,
        "optim": cell.optim_name,
        "objective": cell.objective,
        "params": result["params"],
        "perf": result["perf"],
    }
    return signal, summary


def _perf_row(equity: pd.Series, signal: pd.Series, label: str) -> dict:
    returns = equity.pct_change()
    n_years = len(equity) / PERIODS_PER_YEAR
    sw = n_switches(signal)
    return {
        "label": label,
        "cagr_pct": round(cagr(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
        "n_switches": int(sw),
        "switches_per_year": round(sw / n_years, 3) if n_years > 0 else 0.0,
        "activity_months": int((signal > 0).sum()),
        "total_months": int(len(signal)),
    }


def run_ensemble(fee: float = FEE_CONSERVATIVE, save_outputs: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute per-cell signals, build the K=1..9 vote, return (sweep_df, signals_df)."""
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))

    # 1. Per-cell signals + summaries
    signals: dict[str, pd.Series] = {}
    cell_summaries: list[dict] = []
    for cell in LATIN_SQUARE:
        print(f"[{cell.cell_id}] {cell.rule_name} × {cell.optim_name} → obj={cell.objective}")
        sig, summary = _cell_signal(cell, monthly, fee)
        signals[cell.cell_id] = sig
        cell_summaries.append(summary)

    signals_df = pd.DataFrame(signals)  # index = month, columns = S1..S9
    assert signals_df.shape[1] == 9, f"expected 9 signals, got {signals_df.shape[1]}"

    # 2. Votes for each K in 1..9
    buy_count = signals_df.sum(axis=1)
    for K in range(1, 10):
        signals_df[f"vote_K{K}"] = (buy_count >= K).astype(float)

    # 3. Sweep: perf per K + HODL reference + each cell
    rows: list[dict] = []

    hodl = _hodl_perf(monthly)
    rows.append({
        "label": "HODL",
        "cagr_pct": hodl["cagr_pct"],
        "max_dd_pct": hodl["max_dd_pct"],
        "sharpe": hodl["sharpe"],
        "n_switches": 0,
        "switches_per_year": 0.0,
        "activity_months": int(len(monthly)),
        "total_months": int(len(monthly)),
    })

    for K in range(1, 10):
        ensemble_sig = signals_df[f"vote_K{K}"]
        equity = equity_from_signals(monthly, ensemble_sig, fee_per_switch=fee)
        rows.append(_perf_row(equity, ensemble_sig, f"ensemble_K{K}"))

    for cell_id, sig in signals.items():
        equity = equity_from_signals(monthly, sig, fee_per_switch=fee)
        rows.append(_perf_row(equity, sig, cell_id))

    sweep_df = pd.DataFrame(rows).set_index("label")

    if save_outputs:
        out_dir = repo / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        sweep_df.to_csv(out_dir / "ensemble_sweep.csv")
        signals_df.to_csv(out_dir / "ensemble_signals.csv")
        print(f"\nSweep saved to {out_dir / 'ensemble_sweep.csv'}")
        print(f"Signals saved to {out_dir / 'ensemble_signals.csv'}")

    return sweep_df, signals_df


def main() -> None:
    sweep_df, signals_df = run_ensemble()
    print("\n=== Ensemble sweep (K=1..9) + HODL + cells ===")
    print(sweep_df.to_string())
    print(f"\nSignals table: {signals_df.shape[0]} months × {signals_df.shape[1]} columns (9 cells + 9 votes)")


if __name__ == "__main__":
    main()
