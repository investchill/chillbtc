"""Optimisation protocols O1 (plateau), O2 (walk-forward), O3 (leave-one-cycle-out).

All three take a ``RuleSpec`` describing the rule, its param grid, and optionally
a ``fit_on_train`` callable used to recompute in-sample-sensitive hyperparameters
(Power Law's ``A`` constant) on the calibration slice only.

Objectives:
- "cagr"   : maximise CAGR (positive is better).
- "dd"     : minimise |max drawdown|, equivalently maximise max_drawdown which is negative.
- "sharpe" : maximise Sharpe.

Each ``run_Ox`` returns a dict with at least:
- ``params``   : chosen parameter point, compatible with ``rule_fn(monthly, **params)``.
- ``perf``     : dict of CAGR/DD/Sharpe/switches on the full history with those params.
- ``diagnostic``: optim-specific diagnostic (plateau width, WFE, cycle stability, ...).
- ``grid``     : the raw grid-search DataFrame (O1) or per-window table (O2/O3).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from chillbtc.metrics import (
    PERIODS_PER_YEAR,
    cagr,
    equity_from_signals,
    max_drawdown,
    n_switches,
    sharpe,
)

Objective = str  # "cagr" | "dd" | "sharpe"
Params = dict

OBJ_COL = {"cagr": "cagr", "dd": "max_dd", "sharpe": "sharpe"}


@dataclass
class RuleSpec:
    """Describes a rule for the optimiser.

    Attributes:
        name: short label ("R1", "R2", "R3").
        rule_fn: callable (monthly_df, **params) -> signals Series.
        param_grid: list of dicts, one per grid point. Each dict is passed as kwargs to rule_fn.
        warmup_months: min months the rule needs before emitting a valid signal.
        fit_on_train: optional callable (calib_df) -> dict of extra params merged into
            rule_fn's kwargs. Used by R3 to refit ``a_constant`` on the train slice.
        param_names: ordered tuple of grid-parameter names (for presentation).
    """

    name: str
    rule_fn: Callable[..., pd.Series]
    param_grid: list[Params]
    warmup_months: int
    fit_on_train: Callable[[pd.DataFrame], Params] | None = None
    param_names: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Core grid search
# ---------------------------------------------------------------------------


def _eval_params(
    monthly_full: pd.DataFrame,
    rule_fn: Callable,
    all_params: Params,
    fee: float,
    window_mask: pd.Series | None,
) -> dict:
    """Compute signals on full history, measure metrics on the window (or full)."""
    signals = rule_fn(monthly_full, **all_params)
    equity = equity_from_signals(monthly_full, signals, fee_per_switch=fee)
    if window_mask is None:
        eq_w, sig_w = equity, signals
    else:
        eq_w = equity.loc[window_mask]
        sig_w = signals.loc[window_mask]
    returns = eq_w.pct_change()
    return {
        "cagr": cagr(eq_w),
        "max_dd": max_drawdown(eq_w),
        "sharpe": sharpe(returns),
        "n_switches": n_switches(sig_w),
    }


def grid_search(
    spec: RuleSpec,
    monthly: pd.DataFrame,
    fee: float,
    calib_start: pd.Timestamp | None = None,
    calib_end: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, Params]:
    """Scan ``spec.param_grid`` and return per-point metrics + fixed train params.

    Metrics are computed on the [calib_start, calib_end] window if provided, else
    on the full monthly history.

    If ``spec.fit_on_train`` is set, it is called once on the calibration slice
    (train window) to compute extra params (e.g. Power Law's ``a_constant``), which
    are then frozen and injected into every grid point evaluation.
    """
    if calib_start is not None:
        window_mask = (monthly.index >= calib_start) & (monthly.index <= calib_end)
        calib_slice = monthly.loc[window_mask]
    else:
        window_mask = None
        calib_slice = monthly

    fixed = spec.fit_on_train(calib_slice) if spec.fit_on_train is not None else {}

    rows = []
    for point in spec.param_grid:
        all_params = {**point, **fixed}
        metrics = _eval_params(monthly, spec.rule_fn, all_params, fee, window_mask)
        rows.append({**point, **metrics})
    return pd.DataFrame(rows), fixed


def _argmax_objective(
    grid_df: pd.DataFrame,
    objective: Objective,
    min_switches: int = 0,
) -> tuple[int, bool]:
    """Row index of the grid point maximising the objective, plus a fallback flag.

    Uniform convention: we always maximise the column in ``OBJ_COL``. For "dd",
    the column is ``max_dd`` which is negative; the maximum is the least-negative
    drawdown, i.e. the smallest |dd|.

    Activity constraint: when ``min_switches > 0``, grid points with
    ``n_switches < min_switches`` are excluded before taking the argmax. This
    prevents picking a trivially-flat signal (0 switch → DD=0) on the "dd"
    objective. If every point fails the constraint, the unconstrained argmax is
    returned and the second value is True so callers can surface the fallback.
    """
    col = OBJ_COL[objective]
    if min_switches > 0 and "n_switches" in grid_df.columns:
        eligible = grid_df[grid_df["n_switches"] >= min_switches]
        if not eligible.empty:
            return int(eligible[col].idxmax()), False
        return int(grid_df[col].idxmax()), True
    return int(grid_df[col].idxmax()), False


def _min_switches_for(objective: Objective) -> int:
    """Activity floor per objective: 1 for "dd" (avoid flat-signal artefacts), 0 otherwise."""
    return 1 if objective == "dd" else 0


def _eval_on_full(
    spec: RuleSpec,
    monthly: pd.DataFrame,
    params: Params,
    extra: Params,
    fee: float,
) -> dict:
    """Full-history performance dict: cagr, max_dd, sharpe, n_switches, switches_per_year."""
    metrics = _eval_params(monthly, spec.rule_fn, {**params, **extra}, fee, None)
    n_years = len(monthly) / PERIODS_PER_YEAR
    metrics["switches_per_year"] = round(metrics["n_switches"] / n_years, 3) if n_years > 0 else 0.0
    return metrics


# ---------------------------------------------------------------------------
# O1 — Plateau of stability
# ---------------------------------------------------------------------------


def _plateau_mask(
    grid_df: pd.DataFrame,
    objective: Objective,
    rel_tol: float = 0.10,
    min_switches: int = 0,
) -> pd.Series:
    """Boolean mask: grid points whose objective is within ``rel_tol`` of the peak.

    Uniform definition: a point is in the plateau iff
        obj[p] >= peak - rel_tol * |peak|
    Valid for positive metrics (CAGR, Sharpe) and negative ones (max_dd).

    When ``min_switches > 0``, the peak and the plateau are computed on the
    activity-filtered subgrid, so flat-signal points (n_switches == 0) cannot
    pollute the plateau of the "dd" objective.
    """
    col = OBJ_COL[objective]
    if min_switches > 0 and "n_switches" in grid_df.columns:
        eligible = grid_df[grid_df["n_switches"] >= min_switches]
        if not eligible.empty:
            peak = eligible[col].max()
            threshold = peak - rel_tol * abs(peak)
            in_plateau = grid_df[col] >= threshold
            return in_plateau & (grid_df["n_switches"] >= min_switches)
    peak = grid_df[col].max()
    threshold = peak - rel_tol * abs(peak)
    return grid_df[col] >= threshold


def _plateau_center_1d(
    grid_df: pd.DataFrame,
    param_grid: list[Params],
    mask: pd.Series,
    param_name: str,
    peak_idx: int,
) -> tuple[Params, int]:
    """Largest contiguous run of plateau cells that contains the peak.

    Returns the original grid dict at the centre of the run (to preserve
    param dtypes such as int for R1's ``n``).
    """
    order = grid_df[param_name].argsort().values
    sorted_mask = mask.iloc[order].to_numpy()
    peak_pos_sorted = int(np.where(order == peak_idx)[0][0])

    if not sorted_mask[peak_pos_sorted]:
        return dict(param_grid[peak_idx]), 1

    lo = peak_pos_sorted
    while lo - 1 >= 0 and sorted_mask[lo - 1]:
        lo -= 1
    hi = peak_pos_sorted
    while hi + 1 < len(sorted_mask) and sorted_mask[hi + 1]:
        hi += 1

    center_pos = (lo + hi) // 2
    center_grid_idx = int(order[center_pos])
    return dict(param_grid[center_grid_idx]), hi - lo + 1


def _plateau_center_2d(
    grid_df: pd.DataFrame,
    param_grid: list[Params],
    mask: pd.Series,
    param_names: tuple[str, str],
    peak_idx: int,
) -> tuple[Params, int]:
    """4-connectivity connected component of plateau cells containing the peak.

    Returns the original grid dict at the centroid of the connected plateau
    (nearest plateau grid point to the mean coords), preserving param dtypes.
    """
    p1, p2 = param_names
    vals1 = sorted(grid_df[p1].unique())
    vals2 = sorted(grid_df[p2].unique())
    idx1 = {v: i for i, v in enumerate(vals1)}
    idx2 = {v: j for j, v in enumerate(vals2)}

    m = np.zeros((len(vals1), len(vals2)), dtype=bool)
    pos_to_row: dict[tuple[int, int], int] = {}
    for row_idx, row in grid_df.iterrows():
        i, j = idx1[row[p1]], idx2[row[p2]]
        m[i, j] = bool(mask.loc[row_idx])
        pos_to_row[(i, j)] = int(row_idx)

    peak_row = grid_df.loc[peak_idx]
    start = (idx1[peak_row[p1]], idx2[peak_row[p2]])

    if not m[start]:
        return dict(param_grid[peak_idx]), 1

    visited = np.zeros_like(m)
    stack = [start]
    component: list[tuple[int, int]] = []
    while stack:
        i, j = stack.pop()
        if visited[i, j] or not m[i, j]:
            continue
        visited[i, j] = True
        component.append((i, j))
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < m.shape[0] and 0 <= nj < m.shape[1] and not visited[ni, nj]:
                stack.append((ni, nj))

    mean_i = float(np.mean([c[0] for c in component]))
    mean_j = float(np.mean([c[1] for c in component]))
    # Pick the plateau cell whose (i, j) is closest (L1) to the centroid
    dists = [abs(i - mean_i) + abs(j - mean_j) for (i, j) in component]
    center_i, center_j = component[int(np.argmin(dists))]
    center_grid_idx = pos_to_row[(center_i, center_j)]
    return dict(param_grid[center_grid_idx]), len(component)


def run_O1(
    spec: RuleSpec,
    monthly: pd.DataFrame,
    objective: Objective,
    fee: float,
    rel_tol: float = 0.10,
) -> dict:
    """O1 — Plateau of stability.

    Runs a full-history grid search, identifies the connected plateau containing
    the peak, and returns the plateau centre as the chosen parameter point.

    Diagnostic:
        plateau_size / grid_size (width ratio), width_ok = ratio >= 0.3.
    """
    grid_df, extra = grid_search(spec, monthly, fee)
    min_switches = _min_switches_for(objective)
    peak_idx, activity_fallback = _argmax_objective(grid_df, objective, min_switches=min_switches)
    mask = _plateau_mask(grid_df, objective, rel_tol=rel_tol, min_switches=min_switches)

    if len(spec.param_names) == 1:
        params, size = _plateau_center_1d(
            grid_df, spec.param_grid, mask, spec.param_names[0], peak_idx
        )
    elif len(spec.param_names) == 2:
        params, size = _plateau_center_2d(
            grid_df, spec.param_grid, mask, spec.param_names, peak_idx
        )
    else:
        raise ValueError(f"O1 supports 1 or 2 params, got {len(spec.param_names)}")

    width_ratio = size / len(grid_df)
    perf = _eval_on_full(spec, monthly, params, extra, fee)

    return {
        "params": params,
        "extra_params_note": "A fitted on full history (in-sample, no train/test split)"
        if extra
        else None,
        "perf": perf,
        "diagnostic": {
            "plateau_size": int(size),
            "grid_size": int(len(grid_df)),
            "plateau_width_ratio": round(width_ratio, 3),
            "width_ok": bool(width_ratio >= 0.3),
            "peak_params": {k: float(grid_df.loc[peak_idx, k]) for k in spec.param_names},
            "peak_obj": round(float(grid_df.loc[peak_idx, OBJ_COL[objective]]), 4),
            "activity_constraint_active": bool(min_switches > 0),
            "activity_constraint_fallback": bool(activity_fallback),
        },
        "grid": grid_df,
    }


# ---------------------------------------------------------------------------
# O2 — Walk-forward
# ---------------------------------------------------------------------------


def _build_windows(
    monthly: pd.DataFrame,
    train_months: int,
    test_months: int,
    step_months: int,
    warmup_months: int,
) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    """Build rolling (train_start, train_end, test_start, test_end) tuples.

    The first window starts after ``warmup_months`` so the rule has enough history
    for its first valid signal.
    """
    idx = monthly.index
    if len(idx) < warmup_months + train_months + test_months:
        return []
    windows = []
    start_pos = warmup_months
    while start_pos + train_months + test_months <= len(idx):
        tr_s = idx[start_pos]
        tr_e = idx[start_pos + train_months - 1]
        te_s = idx[start_pos + train_months]
        te_e = idx[start_pos + train_months + test_months - 1]
        windows.append((tr_s, tr_e, te_s, te_e))
        start_pos += step_months
    return windows


def _retention(is_val: float, oos_val: float, objective: Objective) -> float:
    """How much of the in-sample quality is retained out-of-sample, in [0, 1].

    For CAGR/Sharpe (positive is better): retention = clip(OOS/IS, 0, 1) if IS > 0 else 0.
    For DD (negative, closer to 0 is better): retention = clip(|IS|/|OOS|, 0, 1).
    """
    if objective in {"cagr", "sharpe"}:
        if is_val <= 0:
            return 0.0
        return float(max(0.0, min(oos_val / is_val, 1.0)))
    # objective == "dd"
    if abs(oos_val) < 1e-9:
        return 1.0
    return float(max(0.0, min(abs(is_val) / abs(oos_val), 1.0)))


def run_O2(
    spec: RuleSpec,
    monthly: pd.DataFrame,
    objective: Objective,
    fee: float,
    train_months: int = 60,
    test_months: int = 24,
    step_months: int = 12,
) -> dict:
    """O2 — Walk-forward analysis.

    For each rolling window: grid-search on train → pick θ*; evaluate θ* on the
    test slice (with train-fitted extras frozen). Final params = per-axis median
    of θ*. WFE = mean retention ratio across windows.

    Criterion: WFE > 60 % (walk-forward efficiency threshold).
    """
    windows = _build_windows(monthly, train_months, test_months, step_months, spec.warmup_months)
    if not windows:
        raise ValueError(
            f"Not enough history for O2 (need {spec.warmup_months}+{train_months}+{test_months} "
            f"= {spec.warmup_months + train_months + test_months} months, have {len(monthly)})"
        )

    min_switches = _min_switches_for(objective)
    rows = []
    fallback_windows = 0
    for tr_s, tr_e, te_s, te_e in windows:
        train_grid, fixed = grid_search(spec, monthly, fee, calib_start=tr_s, calib_end=tr_e)
        best_idx, window_fallback = _argmax_objective(
            train_grid, objective, min_switches=min_switches
        )
        if window_fallback:
            fallback_windows += 1
        best_params = dict(spec.param_grid[best_idx])
        is_obj = float(train_grid.loc[best_idx, OBJ_COL[objective]])

        test_mask = (monthly.index >= te_s) & (monthly.index <= te_e)
        oos = _eval_params(monthly, spec.rule_fn, {**best_params, **fixed}, fee, test_mask)
        oos_obj = oos[OBJ_COL[objective]]

        rows.append({
            "train_start": tr_s,
            "train_end": tr_e,
            "test_start": te_s,
            "test_end": te_e,
            **{f"theta_{k}": v for k, v in best_params.items()},
            "is_obj": is_obj,
            "oos_obj": oos_obj,
            "retention": _retention(is_obj, oos_obj, objective),
            "activity_fallback": bool(window_fallback),
            **{f"oos_{k}": v for k, v in oos.items()},
        })

    per_window = pd.DataFrame(rows)
    wfe = float(per_window["retention"].mean())

    theta_median = {
        k: float(per_window[f"theta_{k}"].median()) for k in spec.param_names
    }
    # Snap median to the nearest grid point value
    snapped = _snap_to_grid(theta_median, spec.param_grid)

    # Final perf uses full history with:
    #  - snapped params
    #  - extras refit on the full history (pragmatic: the selected θ is meant to
    #    generalise, we evaluate it on all data). We flag this.
    _, final_extras = grid_search(spec, monthly, fee)  # reuses full history for extras
    perf = _eval_on_full(spec, monthly, snapped, final_extras, fee)

    return {
        "params": snapped,
        "extra_params_note": "median theta snapped to grid; final perf uses extras refit on full history",
        "perf": perf,
        "diagnostic": {
            "n_windows": len(windows),
            "train_months": train_months,
            "test_months": test_months,
            "step_months": step_months,
            "wfe": round(wfe, 3),
            "wfe_ok": bool(wfe >= 0.60),
            "theta_median": snapped,
            "theta_std": {
                k: round(float(per_window[f"theta_{k}"].std()), 3)
                for k in spec.param_names
            },
            "activity_constraint_active": bool(min_switches > 0),
            "activity_fallback_windows": int(fallback_windows),
        },
        "grid": per_window,
    }


def _snap_to_grid(params: Params, grid: list[Params]) -> Params:
    """Snap a (possibly off-grid) param dict to the nearest grid point.

    Returns the original grid dict (dtypes preserved, e.g. int for R1's ``n``).
    """
    keys = list(params.keys())
    arr = np.array([[float(p[k]) for k in keys] for p in grid])
    target = np.array([float(params[k]) for k in keys])
    dists = np.linalg.norm(arr - target, axis=1)
    best = int(np.argmin(dists))
    return dict(grid[best])


# ---------------------------------------------------------------------------
# O3 — Leave-one-cycle-out
# ---------------------------------------------------------------------------

# Cycles de halving. Cycle 1 is partially covered
# by Bitstamp data (starts 2014-11, not 2012-11). Cycle 4 is ongoing.
CYCLES: list[dict] = [
    {"id": 1, "start": pd.Timestamp("2012-11-01"), "end": pd.Timestamp("2016-07-31"), "complete": False},
    {"id": 2, "start": pd.Timestamp("2016-08-01"), "end": pd.Timestamp("2020-04-30"), "complete": True},
    {"id": 3, "start": pd.Timestamp("2020-05-01"), "end": pd.Timestamp("2024-03-31"), "complete": True},
    {"id": 4, "start": pd.Timestamp("2024-04-01"), "end": pd.Timestamp("2100-01-01"), "complete": False},
]


def _cycle_mask(monthly: pd.DataFrame, cycle: dict) -> pd.Series:
    """Boolean index mask for months inside the given cycle and present in data."""
    return (monthly.index >= cycle["start"]) & (monthly.index <= cycle["end"])


def run_O3(
    spec: RuleSpec,
    monthly: pd.DataFrame,
    objective: Objective,
    fee: float,
    test_cycle_ids: Iterable[int] = (1, 2, 3),
) -> dict:
    """O3 — Leave-one-cycle-out CV.

    For each test cycle in ``test_cycle_ids``: calibrate on the union of all other
    cycles in ``test_cycle_ids`` (+ any other cycle present in data except cycle 4),
    measure perf on the held-out cycle with train-fitted extras frozen.

    Criterion: perf_OOS ≥ 70 % of perf_IS_mean and params
    stable across folds.
    """
    available = [c for c in CYCLES if c["id"] in set(test_cycle_ids)]
    min_switches = _min_switches_for(objective)
    rows = []
    fallback_folds = 0

    for test_cycle in available:
        train_mask = pd.Series(False, index=monthly.index)
        for c in CYCLES:
            if c["id"] == test_cycle["id"]:
                continue
            if c["id"] == 4:
                continue  # never use cycle 4 in train
            if c["id"] not in set(test_cycle_ids):
                continue
            train_mask |= _cycle_mask(monthly, c)

        train_months = monthly.loc[train_mask]
        if len(train_months) < spec.warmup_months + 12:
            continue

        # Fit extras (e.g. R3's A) on the (possibly non-contiguous) train union
        fixed = spec.fit_on_train(train_months) if spec.fit_on_train is not None else {}
        # Grid search with a non-contiguous train mask
        train_grid = _regrid_with_mask(spec, monthly, fee, train_mask, fixed)

        best_idx, fold_fallback = _argmax_objective(
            train_grid, objective, min_switches=min_switches
        )
        if fold_fallback:
            fallback_folds += 1
        best_params = dict(spec.param_grid[best_idx])
        is_obj = float(train_grid.loc[best_idx, OBJ_COL[objective]])

        test_mask = _cycle_mask(monthly, test_cycle)
        oos = _eval_params(monthly, spec.rule_fn, {**best_params, **fixed}, fee, test_mask)
        oos_obj = oos[OBJ_COL[objective]]

        rows.append({
            "cycle_id": test_cycle["id"],
            "cycle_complete": test_cycle["complete"],
            "test_start": monthly.index[test_mask].min() if test_mask.any() else pd.NaT,
            "test_end": monthly.index[test_mask].max() if test_mask.any() else pd.NaT,
            **{f"theta_{k}": v for k, v in best_params.items()},
            "is_obj": is_obj,
            "oos_obj": oos_obj,
            "retention": _retention(is_obj, oos_obj, objective),
            "activity_fallback": bool(fold_fallback),
            **{f"oos_{k}": v for k, v in oos.items()},
        })

    per_fold = pd.DataFrame(rows)
    if per_fold.empty:
        raise ValueError("O3 produced no folds — check data coverage and cycle definitions.")

    retention = float(per_fold["retention"].mean())
    theta_median = {k: float(per_fold[f"theta_{k}"].median()) for k in spec.param_names}
    snapped = _snap_to_grid(theta_median, spec.param_grid)

    _, final_extras = grid_search(spec, monthly, fee)
    perf = _eval_on_full(spec, monthly, snapped, final_extras, fee)

    return {
        "params": snapped,
        "extra_params_note": "median theta snapped to grid; final perf uses extras refit on full history",
        "perf": perf,
        "diagnostic": {
            "n_folds": int(len(per_fold)),
            "retention": round(retention, 3),
            "retention_ok": bool(retention >= 0.70),
            "theta_median": snapped,
            "theta_std": {
                k: round(float(per_fold[f"theta_{k}"].std()), 3)
                for k in spec.param_names
            },
            "folds_with_partial_cycle": [
                int(r["cycle_id"]) for _, r in per_fold.iterrows() if not r["cycle_complete"]
            ],
            "activity_constraint_active": bool(min_switches > 0),
            "activity_fallback_folds": int(fallback_folds),
        },
        "grid": per_fold,
    }


def _regrid_with_mask(
    spec: RuleSpec, monthly: pd.DataFrame, fee: float, mask: pd.Series, fixed: Params
) -> pd.DataFrame:
    """Grid search with an arbitrary (possibly non-contiguous) boolean mask."""
    rows = []
    for point in spec.param_grid:
        metrics = _eval_params(monthly, spec.rule_fn, {**point, **fixed}, fee, mask)
        rows.append({**point, **metrics})
    return pd.DataFrame(rows)
