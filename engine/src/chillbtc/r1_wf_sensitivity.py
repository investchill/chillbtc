"""Phase D — R1 walk-forward sensitivity.

Diagnostic only: does a shorter walk-forward (train=48, test=18) give R1 enough
windows to make S2's WFE statistically meaningful?

- Baseline  : train=60, test=24, step=12 → ~1 window on the 119-month window.
- Short     : train=48, test=18, step=12 → ~4 windows expected.

Objective: "dd" (matches S2 in the Latin square). Fee: 0.005 (Phase C baseline).

Does not modify the Latin square: the main backtest stays on (60, 24, 12). If
the finding is conclusive, bake in via RuleSpec or cell-level override later.

Output: ``engine/output/r1_wf_sensitivity.csv`` (one row per window, with a
``config`` label) + a summary table printed to stdout.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chillbtc.backtest import FEE_CONSERVATIVE, SPECS, _trim_common_warmup
from chillbtc.data import load_or_fetch
from chillbtc.optims import run_O2

OBJECTIVE = "dd"
CONFIGS = [
    ("baseline_60_24_12", 60, 24, 12),
    ("short_48_18_12", 48, 18, 12),
]


def _summary_row(label: str, train: int, test: int, step: int, result: dict) -> dict:
    diag = result["diagnostic"]
    perf = result["perf"]
    return {
        "config": label,
        "train_months": train,
        "test_months": test,
        "step_months": step,
        "n_windows": diag["n_windows"],
        "theta_median_n": diag["theta_median"]["n"],
        "theta_std_n": diag["theta_std"]["n"],
        "wfe": diag["wfe"],
        "wfe_ok": diag["wfe_ok"],
        "final_cagr_pct": round(perf["cagr"] * 100, 2),
        "final_max_dd_pct": round(perf["max_dd"] * 100, 2),
        "final_sharpe": round(perf["sharpe"], 3),
        "final_switches_per_year": round(perf["switches_per_year"], 3),
    }


def run_r1_wf_sensitivity(save_output: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run both walk-forward configs and return (summary_df, per_window_df)."""
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))
    spec = SPECS["R1"]

    summaries: list[dict] = []
    per_window_frames: list[pd.DataFrame] = []

    for label, train, test, step in CONFIGS:
        print(f"\n=== R1 walk-forward [{label}] (obj={OBJECTIVE}) ===")
        result = run_O2(
            spec, monthly, OBJECTIVE, FEE_CONSERVATIVE,
            train_months=train, test_months=test, step_months=step,
        )
        summaries.append(_summary_row(label, train, test, step, result))

        # Attach the config label to each window row for CSV export
        pw = result["grid"].copy()
        pw.insert(0, "config", label)
        per_window_frames.append(pw)

    summary_df = pd.DataFrame(summaries)
    per_window_df = pd.concat(per_window_frames, ignore_index=True)

    if save_output:
        out_dir = repo / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "r1_wf_sensitivity.csv"
        summary_df.to_csv(out_dir / "r1_wf_sensitivity_summary.csv", index=False)
        per_window_df.to_csv(path, index=False)
        print(f"\nSummary saved to {out_dir / 'r1_wf_sensitivity_summary.csv'}")
        print(f"Per-window detail saved to {path}")

    return summary_df, per_window_df


def main() -> None:
    summary_df, per_window_df = run_r1_wf_sensitivity()
    print("\n=== Summary ===")
    print(summary_df.to_string(index=False))
    print("\n=== Per-window detail ===")
    print(per_window_df.to_string(index=False))


if __name__ == "__main__":
    main()
