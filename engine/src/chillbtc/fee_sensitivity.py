"""Phase D — fee sensitivity.

Re-runs the 9-cell Latin square at two fee levels and reports the per-cell delta:

- fee=0.005  (0.5 %, Phase C pessimistic baseline)
- fee=0.0015 (0.15 %, realistic Binance + BNB)

Each rule is *re-optimised* at each fee level (grid search + O1/O2/O3), so the
chosen parameters can differ between the two runs. A ``params_changed`` flag
flags cells where the optimum moves.

Output: ``engine/output/fee_sensitivity.csv``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chillbtc.backtest import run_phase_c

FEE_BASELINE = 0.005
FEE_REALISTIC = 0.0015


def run_fee_sensitivity(save_output: bool = True) -> pd.DataFrame:
    """Run both fee levels and build the comparison DataFrame indexed by cell_id."""
    print(f"\n=== Baseline run (fee={FEE_BASELINE:.4f}) ===")
    df_baseline = run_phase_c(fee=FEE_BASELINE, save_outputs=False)
    print(f"\n=== Realistic run (fee={FEE_REALISTIC:.4f}) ===")
    df_realistic = run_phase_c(fee=FEE_REALISTIC, save_outputs=False)

    # Index is cell_id from run_phase_c
    cols_keep = ["rule", "optim", "objective", "params", "cagr_pct",
                 "max_dd_pct", "sharpe", "switches_per_year"]
    left = df_baseline[cols_keep].add_suffix("_fee05")
    right = df_realistic[cols_keep].add_suffix("_fee015")
    merged = left.join(right, how="outer")

    # Percentage-point deltas for CAGR and DD (already expressed in %).
    merged["d_cagr_pp"] = (merged["cagr_pct_fee015"] - merged["cagr_pct_fee05"]).round(2)
    merged["d_dd_pp"] = (merged["max_dd_pct_fee015"] - merged["max_dd_pct_fee05"]).round(2)
    merged["d_sharpe"] = (merged["sharpe_fee015"] - merged["sharpe_fee05"]).round(3)
    merged["d_switches_per_year"] = (
        merged["switches_per_year_fee015"] - merged["switches_per_year_fee05"]
    ).round(3)
    merged["params_changed"] = merged["params_fee05"] != merged["params_fee015"]

    # Move the key rule/optim/objective (same on both sides) to the front for readability.
    front = ["rule_fee05", "optim_fee05", "objective_fee05"]
    rename = {"rule_fee05": "rule", "optim_fee05": "optim", "objective_fee05": "objective"}
    merged = merged.rename(columns=rename)
    front = list(rename.values())
    drop_dups = ["rule_fee015", "optim_fee015", "objective_fee015"]
    merged = merged.drop(columns=drop_dups)
    ordered = front + [c for c in merged.columns if c not in front]
    merged = merged[ordered]

    if save_output:
        out_dir = Path(__file__).resolve().parents[2] / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "fee_sensitivity.csv"
        merged.to_csv(path)
        print(f"\nFee sensitivity saved to {path}")

    return merged


def main() -> None:
    df = run_fee_sensitivity()
    print("\n=== Fee sensitivity (0.5 % → 0.15 %) ===")
    view_cols = [
        "rule", "optim", "objective",
        "params_fee05", "params_fee015", "params_changed",
        "cagr_pct_fee05", "cagr_pct_fee015", "d_cagr_pp",
        "max_dd_pct_fee05", "max_dd_pct_fee015", "d_dd_pp",
        "sharpe_fee05", "sharpe_fee015", "d_sharpe",
        "switches_per_year_fee05", "switches_per_year_fee015", "d_switches_per_year",
    ]
    print(df[view_cols].to_string())


if __name__ == "__main__":
    main()
