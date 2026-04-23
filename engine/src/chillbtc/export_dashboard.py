"""Export dashboard annuel — format tableau annuel classique.

Génère ``engine/output/export_dashboard.csv`` avec :

- **Lignes années** (2016 → 2026 avec annotation si année partielle) :
  pour chaque année, perf annuelle % + portefeuille € (base 10 000 €) pour :
    - Stratégie cascade R1+R3 (convention strict_r1_def, frais 0,5 %/switch inclus)
    - HODL BTC pur
    - Surperformance strat vs HODL en points de pourcentage

- **Lignes stats agrégées** :
    - Rendement annualisé sur la période complète
    - Rendement annualisé sur les 5 dernières années complètes
    - Perte max sur une année calendaire
    - Drawdown max (monthly close-to-close, pas intra-mois)
    - Perf cumulée sur les 5 dernières années complètes
    - ROI total

Les chiffres viennent du backtest Python officiel (avec frais 0,5 %/switch) —
fidèle à ``engine/output/cascade_summary.json``, pas la version gsheet sans
frais.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from chillbtc.backtest import FEE_CONSERVATIVE, _trim_common_warmup
from chillbtc.cascade import (
    build_cascade_position,
    equity_from_cascade,
)
from chillbtc.data import load_or_fetch
from chillbtc.rules import fit_power_law, signal_power_law, signal_tsmom

# Paramètres figés (valeurs canoniques)
N_TSMOM = 11
K_LOW_PL = 0.6
K_HIGH_PL = 2.5
N_EXPONENT_PL = 5.8
CONVENTION = "strict_r1_def"
CAPITAL_INIT_EUR = 10000


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%".replace(".", ",")


def _fmt_eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


def _yearly_stats(equity: pd.Series) -> pd.DataFrame:
    """Pour chaque année civile, calcule :
    - perf annuelle (equity fin année / equity début année - 1)
    - portefeuille fin année (en €, base capital_init)
    - nb mois observés dans l'année (pour flagger année partielle)
    """
    eq = equity.copy()
    eq.index = pd.to_datetime(eq.index)

    # Pour chaque année, on prend la dernière valeur de l'année précédente comme base
    years = sorted(set(eq.index.year))
    rows = []
    for y in years:
        mask = eq.index.year == y
        year_slice = eq[mask]
        if len(year_slice) == 0:
            continue

        first_date = year_slice.index[0]
        last_date = year_slice.index[-1]
        end_val = float(year_slice.iloc[-1])

        # Base = dernière valeur de l'année précédente (ou première de l'année si pas de passé)
        prev_mask = eq.index.year == y - 1
        prev_slice = eq[prev_mask]
        if len(prev_slice) > 0:
            start_val = float(prev_slice.iloc[-1])
        else:
            # 1ʳᵉ année : on ne peut pas calculer une perf classique,
            # on prend la valeur initiale
            start_val = float(eq.iloc[0])
            # On considère la perf comme partielle
        perf = (end_val / start_val - 1) if start_val > 0 else 0.0
        rows.append({
            "year": y,
            "perf": perf,
            "end_val": end_val,
            "n_months": int(mask.sum()),
            "is_partial": mask.sum() < 12,
            "first_date": first_date.date().isoformat(),
            "last_date": last_date.date().isoformat(),
        })
    return pd.DataFrame(rows)


def _max_drawdown_monthly(equity: pd.Series) -> float:
    rolling_max = equity.cummax()
    dd = (equity - rolling_max) / rolling_max
    return float(dd.min())


def _cagr(start_val: float, end_val: float, n_years: float) -> float:
    if start_val <= 0 or n_years <= 0:
        return 0.0
    ratio = end_val / start_val
    if ratio <= 0:
        return 0.0
    return ratio ** (1 / n_years) - 1


def generate_dashboard_csv() -> Path:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))

    # Recalcule signaux + positions avec paramètres figés
    a_const, _ = fit_power_law(monthly, n_exponent=N_EXPONENT_PL)
    sig_r1 = signal_tsmom(monthly, n=N_TSMOM)
    sig_r3 = signal_power_law(
        monthly,
        k_low=K_LOW_PL,
        k_high=K_HIGH_PL,
        n_exponent=N_EXPONENT_PL,
        a_constant=a_const,
    )
    position = build_cascade_position(sig_r1, sig_r3, convention=CONVENTION)

    # Equity strat (avec frais, fidèle au backtest officiel)
    equity_strat = equity_from_cascade(
        monthly, position, fee_per_switch=FEE_CONSERVATIVE,
        capital_init=CAPITAL_INIT_EUR,
    )

    # Equity HODL pur (base CAPITAL_INIT)
    first_btc = float(monthly["close_usd"].iloc[0])
    equity_hodl = CAPITAL_INIT_EUR * monthly["close_usd"] / first_btc

    yearly_strat = _yearly_stats(equity_strat)
    yearly_hodl = _yearly_stats(equity_hodl)

    # Merge par année
    merged = yearly_strat.merge(
        yearly_hodl,
        on="year",
        suffixes=("_strat", "_hodl"),
    )

    # Stats agrégées
    n_total_months = len(monthly)
    # Aligné avec backtest officiel (metrics.cagr) : n_years = (n-1)/12
    n_years_total = (n_total_months - 1) / 12
    cagr_strat = _cagr(
        CAPITAL_INIT_EUR, float(equity_strat.iloc[-1]), n_years_total
    )
    cagr_hodl = _cagr(
        CAPITAL_INIT_EUR, float(equity_hodl.iloc[-1]), n_years_total
    )
    dd_strat = _max_drawdown_monthly(equity_strat)
    dd_hodl = _max_drawdown_monthly(equity_hodl)

    # Perte max sur 1 année calendaire (parmi les années complètes)
    complete = merged[~merged["is_partial_strat"]]
    if len(complete) > 0:
        worst_year_strat = float(complete["perf_strat"].min())
        worst_year_hodl = float(complete["perf_hodl"].min())
    else:
        worst_year_strat = worst_year_hodl = 0.0

    # Rendement annualisé sur les 5 dernières années complètes
    last_5_complete = complete.tail(5)
    if len(last_5_complete) >= 1:
        n_5y = len(last_5_complete)
        # Valeur de début = end_val de l'année juste avant la 1ʳᵉ des 5
        idx_first_5 = last_5_complete.index[0]
        prev_idx = idx_first_5 - 1
        if prev_idx in merged.index:
            start_5y_strat = float(merged.loc[prev_idx, "end_val_strat"])
            start_5y_hodl = float(merged.loc[prev_idx, "end_val_hodl"])
        else:
            start_5y_strat = start_5y_hodl = CAPITAL_INIT_EUR
        end_5y_strat = float(last_5_complete["end_val_strat"].iloc[-1])
        end_5y_hodl = float(last_5_complete["end_val_hodl"].iloc[-1])
        cagr_5y_strat = _cagr(start_5y_strat, end_5y_strat, n_5y)
        cagr_5y_hodl = _cagr(start_5y_hodl, end_5y_hodl, n_5y)
        perf_5y_strat = (end_5y_strat / start_5y_strat - 1) if start_5y_strat > 0 else 0.0
        perf_5y_hodl = (end_5y_hodl / start_5y_hodl - 1) if start_5y_hodl > 0 else 0.0
    else:
        cagr_5y_strat = cagr_5y_hodl = 0.0
        perf_5y_strat = perf_5y_hodl = 0.0

    # ROI total
    roi_strat = float(equity_strat.iloc[-1]) / CAPITAL_INIT_EUR - 1
    roi_hodl = float(equity_hodl.iloc[-1]) / CAPITAL_INIT_EUR - 1

    # --- Construction CSV ---
    out_csv = repo / "output" / "export_dashboard.csv"

    rows: list[list[str]] = []

    # Header principal
    rows.append([
        "Année",
        "Stratégie cascade R1+R3", "",
        "HODL BTC pur", "",
        "Surperf strat − HODL (pp)",
    ])
    rows.append([
        "",
        "Perf annuelle", "Portefeuille",
        "Perf annuelle", "Portefeuille",
        "",
    ])
    # Ligne capital initial
    rows.append([
        "(capital initial)",
        "", _fmt_eur(CAPITAL_INIT_EUR),
        "", _fmt_eur(CAPITAL_INIT_EUR),
        "",
    ])

    # Lignes années
    for _, r in merged.iterrows():
        year_label = str(int(r["year"]))
        if r["is_partial_strat"]:
            year_label += f" ({int(r['n_months_strat'])} mois)"
        surperf_pp = (r["perf_strat"] - r["perf_hodl"]) * 100
        rows.append([
            year_label,
            _fmt_pct(float(r["perf_strat"])),
            _fmt_eur(float(r["end_val_strat"])),
            _fmt_pct(float(r["perf_hodl"])),
            _fmt_eur(float(r["end_val_hodl"])),
            f"{surperf_pp:+.2f} pp".replace(".", ","),
        ])

    # Séparateur
    rows.append(["", "", "", "", "", ""])

    # Stats agrégées
    period_label = f"sur la période complète ({n_years_total:.1f} ans)"
    rows.append([
        f"Rendement annualisé {period_label}",
        _fmt_pct(cagr_strat), "",
        _fmt_pct(cagr_hodl), "",
        f"{(cagr_strat - cagr_hodl) * 100:+.2f} pp".replace(".", ","),
    ])
    rows.append([
        "Rendement annualisé sur les 5 dernières années complètes",
        _fmt_pct(cagr_5y_strat), "",
        _fmt_pct(cagr_5y_hodl), "",
        f"{(cagr_5y_strat - cagr_5y_hodl) * 100:+.2f} pp".replace(".", ","),
    ])
    rows.append([
        "Perte max sur 1 année calendaire",
        _fmt_pct(worst_year_strat), "",
        _fmt_pct(worst_year_hodl), "",
        f"{(worst_year_strat - worst_year_hodl) * 100:+.2f} pp".replace(".", ","),
    ])
    rows.append([
        "Drawdown max (sur equity mensuelle)",
        _fmt_pct(dd_strat), "",
        _fmt_pct(dd_hodl), "",
        f"{(dd_strat - dd_hodl) * 100:+.2f} pp".replace(".", ","),
    ])
    rows.append([
        "Perf cumulée sur les 5 dernières années complètes",
        _fmt_pct(perf_5y_strat), "",
        _fmt_pct(perf_5y_hodl), "",
        f"{(perf_5y_strat - perf_5y_hodl) * 100:+.2f} pp".replace(".", ","),
    ])
    rows.append([
        "ROI total",
        _fmt_pct(roi_strat), "",
        _fmt_pct(roi_hodl), "",
        f"{(roi_strat - roi_hodl) * 100:+.2f} pp".replace(".", ","),
    ])

    # Note frais
    rows.append(["", "", "", "", "", ""])
    rows.append([
        "Note : chiffres strat avec frais 0,5 %/switch inclus (fidèle au backtest Python officiel).",
        "", "", "", "", "",
    ])
    rows.append([
        f"Fenêtre backtest : {monthly.index.min().date()} → {monthly.index.max().date()} ({n_total_months} mois).",
        "", "", "", "", "",
    ])
    rows.append([
        f"Paramètres figés : R1 n={N_TSMOM}, R3 k_low={K_LOW_PL}/k_high={K_HIGH_PL}/N_exp={N_EXPONENT_PL}, convention {CONVENTION}.",
        "", "", "", "", "",
    ])

    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    return out_csv


def main() -> None:
    out = generate_dashboard_csv()
    print(f"Dashboard généré : {out}")
    print()
    with open(out) as f:
        content = f.readlines()
    for line in content:
        print(line.rstrip())


if __name__ == "__main__":
    main()
