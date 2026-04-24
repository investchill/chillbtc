"""Phase C runner: 9 cells of the Latin square R × O, calibrated on a single objective each.

Mapping:

                O1 Plateau       O2 Walk-fwd      O3 Leave-cycle
    R1 TSMOM  → S1 (CAGR)        S2 (DD)          S3 (Sharpe)
    R2 Mayer  → S4 (DD)          S5 (Sharpe)      S6 (CAGR)
    R3 PLaw   → S7 (Sharpe)      S8 (CAGR)        S9 (DD)

Output: ``engine/output/phase_c_results.csv`` (one row per cell) +
``engine/output/phase_c_raw.json`` (raw grids for heatmaps, Phase D).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from chillbtc.data import load_or_fetch
from chillbtc.metrics import (
    cagr,
    equity_from_signals,
    max_drawdown,
    sharpe,
)
from chillbtc.optims import (
    RuleSpec,
    run_O1,
    run_O2,
    run_O3,
)
from chillbtc.rules import (
    fit_power_law,
    signal_mayer,
    signal_power_law,
    signal_tsmom,
)

FEE_CONSERVATIVE = 0.005  # 0.5 % per switch (Phase C baseline, conservative hypothesis)
OPTIM_FNS: dict[str, Callable] = {"O1": run_O1, "O2": run_O2, "O3": run_O3}


@dataclass
class Cell:
    cell_id: str
    rule_name: str
    optim_name: str
    objective: str


LATIN_SQUARE: list[Cell] = [
    Cell("S1", "R1", "O1", "cagr"),
    Cell("S2", "R1", "O2", "dd"),
    Cell("S3", "R1", "O3", "sharpe"),
    Cell("S4", "R2", "O1", "dd"),
    Cell("S5", "R2", "O2", "sharpe"),
    Cell("S6", "R2", "O3", "cagr"),
    Cell("S7", "R3", "O1", "sharpe"),
    Cell("S8", "R3", "O2", "cagr"),
    Cell("S9", "R3", "O3", "dd"),
]


# ---------------------------------------------------------------------------
# Rule specs — grid definitions (see rules.py for parameter plages)
# ---------------------------------------------------------------------------


def _r1_spec() -> RuleSpec:
    grid = [{"n": int(n)} for n in range(6, 19)]  # 6 .. 18 months
    return RuleSpec(
        name="R1",
        rule_fn=signal_tsmom,
        param_grid=grid,
        warmup_months=18,  # max N in grid
        fit_on_train=None,
        param_names=("n",),
    )


def _r2_spec() -> RuleSpec:
    grid = [
        {"k_low": round(kl, 2), "k_high": round(kh, 2)}
        for kl in np.arange(0.70, 1.21, 0.05)
        for kh in np.arange(2.0, 3.01, 0.10)
    ]
    return RuleSpec(
        name="R2",
        rule_fn=signal_mayer,
        param_grid=grid,
        warmup_months=10,  # ~200 trading days for SMA200d to materialise
        fit_on_train=None,
        param_names=("k_low", "k_high"),
    )


def _fit_power_law_on_train(calib_df: pd.DataFrame) -> dict:
    a, n = fit_power_law(calib_df)
    return {"a_constant": float(a), "n_exponent": float(n)}


def _r3_spec() -> RuleSpec:
    grid = [
        {"k_low": round(kl, 2), "k_high": round(kh, 2)}
        for kl in np.arange(0.40, 1.01, 0.10)
        for kh in np.arange(1.50, 3.01, 0.25)
    ]
    return RuleSpec(
        name="R3",
        rule_fn=signal_power_law,
        param_grid=grid,
        warmup_months=1,
        fit_on_train=_fit_power_law_on_train,
        param_names=("k_low", "k_high"),
    )


SPECS: dict[str, RuleSpec] = {
    "R1": _r1_spec(),
    "R2": _r2_spec(),
    "R3": _r3_spec(),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _hodl_perf(monthly: pd.DataFrame) -> dict:
    signals = pd.Series(1.0, index=monthly.index, name="hodl")
    equity = equity_from_signals(monthly, signals, fee_per_switch=0.0)
    returns = equity.pct_change()
    return {
        "cell_id": "HODL",
        "rule": "HODL",
        "optim": "-",
        "objective": "-",
        "params": "-",
        "cagr_pct": round(cagr(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
        "switches_per_year": 0.0,
        "wfe": None,
        "plateau_width": None,
        "retention_cycle": None,
        "width_ok": None,
        "wfe_ok": None,
        "retention_ok": None,
    }


def _run_cell(cell: Cell, monthly: pd.DataFrame, fee: float) -> tuple[dict, dict]:
    """Run one cell. Returns (summary_row_dict, raw_payload_dict)."""
    spec = SPECS[cell.rule_name]
    fn = OPTIM_FNS[cell.optim_name]
    result = fn(spec, monthly, cell.objective, fee)

    perf = result["perf"]
    diag = result["diagnostic"]

    summary = {
        "cell_id": cell.cell_id,
        "rule": cell.rule_name,
        "optim": cell.optim_name,
        "objective": cell.objective,
        "params": _format_params(result["params"]),
        "cagr_pct": round(perf["cagr"] * 100, 2),
        "max_dd_pct": round(perf["max_dd"] * 100, 2),
        "sharpe": round(perf["sharpe"], 3),
        "switches_per_year": round(perf["switches_per_year"], 3),
        "wfe": diag.get("wfe"),
        "plateau_width": diag.get("plateau_width_ratio"),
        "retention_cycle": diag.get("retention") if cell.optim_name == "O3" else None,
        "width_ok": diag.get("width_ok"),
        "wfe_ok": diag.get("wfe_ok"),
        "retention_ok": diag.get("retention_ok"),
    }

    # Raw payload: everything useful for Phase D heatmaps + audits.
    grid_df: pd.DataFrame = result["grid"]
    raw = {
        "cell_id": cell.cell_id,
        "rule": cell.rule_name,
        "optim": cell.optim_name,
        "objective": cell.objective,
        "params": result["params"],
        "extra_params_note": result.get("extra_params_note"),
        "perf": {k: float(v) if isinstance(v, (int, float, np.floating)) else v for k, v in perf.items()},
        "diagnostic": _json_safe(diag),
        "grid": _df_to_records_json_safe(grid_df),
    }
    return summary, raw


def _format_params(p: dict) -> str:
    return ", ".join(f"{k}={v:g}" for k, v in p.items())


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def _df_to_records_json_safe(df: pd.DataFrame) -> list[dict]:
    out = []
    for _, row in df.iterrows():
        rec = {}
        for k, v in row.items():
            if isinstance(v, pd.Timestamp):
                rec[k] = v.isoformat()
            elif isinstance(v, (np.integer, np.floating, np.bool_)):
                rec[k] = _json_safe(v)
            else:
                rec[k] = v
        out.append(rec)
    return out


def _trim_common_warmup(monthly: pd.DataFrame) -> pd.DataFrame:
    """Drop leading months where the slowest rule (R1 N=18 or SMA200d) has no signal,
    plus the last month if it is partial (Phase A data caveat on partial months).
    """
    max_warmup = max(SPECS[r].warmup_months for r in ("R1", "R2", "R3"))
    trimmed = monthly.iloc[max_warmup:].copy()
    # Drop the last row only if its index is in the current civil month
    # (= partial month by construction). A month-end index from the
    # *previous* civil month is the close we want, even if today is
    # only 1-2 days after it.
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    last = trimmed.index[-1]
    if last.year == today.year and last.month == today.month:
        trimmed = trimmed.iloc[:-1]
    return trimmed


def run_phase_c(fee: float = FEE_CONSERVATIVE, save_outputs: bool = True) -> pd.DataFrame:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly_raw = load_or_fetch(cache)
    monthly = _trim_common_warmup(monthly_raw)

    hodl_row = _hodl_perf(monthly)

    summaries: list[dict] = [hodl_row]
    raw_payloads: list[dict] = []

    for cell in LATIN_SQUARE:
        print(f"[{cell.cell_id}] {cell.rule_name} × {cell.optim_name} → obj={cell.objective}")
        summary, raw = _run_cell(cell, monthly, fee)
        summaries.append(summary)
        raw_payloads.append(raw)

    df = pd.DataFrame(summaries).set_index("cell_id")

    if save_outputs:
        out_dir = repo / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "phase_c_results.csv")
        with open(out_dir / "phase_c_raw.json", "w") as f:
            json.dump({
                "fee": fee,
                "window_start": monthly.index.min().isoformat(),
                "window_end": monthly.index.max().isoformat(),
                "n_months": len(monthly),
                "cells": raw_payloads,
            }, f, indent=2, default=_json_safe)
        print(f"\nResults saved to {out_dir / 'phase_c_results.csv'}")
        print(f"Raw grids saved to {out_dir / 'phase_c_raw.json'}")

    return df


def main() -> None:
    df = run_phase_c()
    print()
    print(df.to_string())


if __name__ == "__main__":
    main()
