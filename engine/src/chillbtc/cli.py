# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# Copyright © 2026 ChillBTC
"""Phase E — CLI unifié pour l'exploitation mensuelle de la stratégie BTC.

Lancement unique (plus de menu interactif) : affiche à la suite
  (1) le signal du mois (appelle ``monthly_signal.run_monthly_signal``),
  (2) le récap des 10 derniers mois,
  (3) le récap annuel depuis le début.

Source de vérité pour les récaps : ``engine/output/live_journal.csv``.
- Lignes ``source=backfill`` : calculées par le bootstrap depuis le backtest.
- Lignes ``source=live`` : ajoutées par ``chillbtc-monthly`` chaque 1er du mois.

Si le journal est absent ou vide, ``_ensure_journal()`` lance automatiquement
``bootstrap_journal()`` avant la séquence d'affichage.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from chillbtc.backtest import FEE_CONSERVATIVE
from chillbtc.monthly_signal import (
    LIVE_JOURNAL_HEADER,
    N_TSMOM,
    emoji_position,
    run_monthly_signal,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _journal_path() -> Path:
    return _repo_root() / "output" / "live_journal.csv"


def _load_journal() -> pd.DataFrame | None:
    path = _journal_path()
    if not path.exists() or path.stat().st_size == 0:
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        return None
    return df.sort_values("date").reset_index(drop=True)


def _compute_equity(df: pd.DataFrame, fee: float = FEE_CONSERVATIVE) -> pd.DataFrame:
    """Ajoute ret_strat, ret_hodl, equity_strat, equity_hodl au journal.

    Convention identique à ``cascade.equity_from_cascade`` : friction
    proportionnelle au turnover, position effective décalée d'un mois
    (position[t] engagée sur t+1).
    """
    out = df.copy()
    out["close_btc_usd"] = out["close_btc_usd"].astype(float)
    out["position_pct"] = out["position_pct"].astype(float)
    out["pos"] = out["position_pct"] / 100.0
    out["ret_hodl"] = out["close_btc_usd"].pct_change().fillna(0.0)
    effective = out["pos"].shift(1).fillna(0.0)
    out["effective_pct"] = effective * 100.0
    prev = effective.shift(1).fillna(0.0)
    turnover = (effective - prev).abs()
    out["ret_strat"] = (effective * out["ret_hodl"] - turnover * fee).fillna(0.0)
    out["equity_strat"] = 100.0 * (1 + out["ret_strat"]).cumprod()
    out["equity_hodl"] = 100.0 * (1 + out["ret_hodl"]).cumprod()
    return out


def bootstrap_journal() -> None:
    """Remplit ``live_journal.csv`` depuis le backtest officiel Phase D.

    Source : ``engine/output/cascade_position.csv`` (mode C cascade R1+R3,
    walk-forward, validé 2026-04-18). Les colonnes ``ratio_price_fair_pl`` et
    ``a_constant`` ne sont pas reproductibles telles quelles depuis un backtest
    walk-forward (elles changent fenêtre par fenêtre) → laissées vides pour
    les lignes ``backfill``. À partir du 1ᵉʳ mai 2026, ``chillbtc-monthly`` append
    des lignes ``source=live`` qui, elles, renseignent ces colonnes.
    """
    path = _journal_path()
    if path.exists() and path.stat().st_size > 0:
        resp = input(f"  {path.name} existe déjà. Écraser ? [o/N] ").strip().lower()
        if resp != "o":
            print("  Annulé.\n")
            return

    repo = _repo_root()
    cascade_csv = repo / "output" / "cascade_position.csv"
    if not cascade_csv.exists():
        print(f"\n  ⚠  {cascade_csv.name} manquant. Lance d'abord :")
        print("     cd engine && uv run chillbtc-backtest\n")
        return

    cascade = pd.read_csv(cascade_csv, parse_dates=["date"])
    cascade = cascade.sort_values("date").reset_index(drop=True)
    ret_11 = cascade["btc_close"].pct_change(N_TSMOM)

    rows = []
    for i, row in cascade.iterrows():
        r1 = int(row["def_signal"])
        r3 = int(row["agg_signal"])
        pos = float(row["position"])
        r1_lbl = "BUY" if r1 == 1 else "CASH"
        r3_lbl = "BUY" if r3 == 1 else "CASH"
        r11 = ret_11.iloc[i]
        rows.append({
            "date": row["date"].date().isoformat(),
            "close_btc_usd": f"{row['btc_close']:.2f}",
            "return_11m": f"{r11:.6f}" if pd.notna(r11) else "",
            "signal_r1": r1,
            "ratio_price_fair_pl": "",
            "a_constant": "",
            "signal_r3": r3,
            "position_pct": f"{pos * 100:.0f}",
            "diagnostic_fr": f"R1 {r1_lbl} & R3 {r3_lbl} → {pos * 100:.0f} % BTC (Phase D walk-forward)",
            "source": "backfill",
        })

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIVE_JOURNAL_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"  Journal bootstrappé depuis {cascade_csv.name} : {path}")
    print(f"  {len(rows)} lignes écrites, de {rows[0]['date']} à {rows[-1]['date']}.\n")


def _ensure_journal() -> bool:
    """Garantit que ``live_journal.csv`` existe et est non vide.

    Si absent/vide, lance automatiquement ``bootstrap_journal()`` (silencieux
    côté prompt, verbeux côté log). Retourne True si le journal est prêt.
    """
    path = _journal_path()
    if path.exists() and path.stat().st_size > 0:
        return True
    print("\n  (journal absent → bootstrap automatique depuis le backtest…)")
    bootstrap_journal()
    return path.exists() and path.stat().st_size > 0


def recap_monthly(n_months: int = 10) -> None:
    if not _ensure_journal():
        return
    df = _load_journal()
    if df is None:
        return
    df = _compute_equity(df)
    n = min(n_months, len(df) - 1)
    last = df.tail(n + 1)

    bar = "═" * 64
    print()
    print(bar)
    print(f"  Récap des {n} derniers mois")
    print(bar)
    print(f"  {'mois':<10} {'close BTC':>11}  {'expo.':<9}  {'perf strat':>12} {'perf HODL':>12}")
    print("  " + "─" * 62)
    for _, row in last.iloc[1:].iterrows():
        mois = row["date"].strftime("%Y-%m")
        close = f"{row['close_btc_usd']:>11,.0f}".replace(",", " ")
        eff = row["effective_pct"]
        expo = f"{emoji_position(eff / 100.0)} {eff:>3.0f} %"
        ps = f"{row['ret_strat']:+7.2%}"
        ph = f"{row['ret_hodl']:+7.2%}"
        print(f"  {mois:<10} {close:>11}  {expo:<9}  {ps:>12} {ph:>12}")

    total_strat = last["equity_strat"].iloc[-1] / last["equity_strat"].iloc[0] - 1
    total_hodl = last["equity_hodl"].iloc[-1] / last["equity_hodl"].iloc[0] - 1
    print("  " + "─" * 62)
    print(f"  Total {n}m : strat {total_strat:+.1%}   |   HODL {total_hodl:+.1%}")
    print(bar)
    print()


def recap_yearly() -> None:
    if not _ensure_journal():
        return
    df = _load_journal()
    if df is None:
        return
    df = _compute_equity(df)
    df["year"] = df["date"].dt.year
    years = sorted(df["year"].unique())

    bar = "=" * 86
    print()
    print(bar)
    print(f"  Récap annuel ({years[0]} → {years[-1]})")
    print(bar)
    print(f"  {'année':<6} {'perf strat':>12} {'perf HODL':>12} {'delta':>10} "
          f"{'DD max strat':>14} {'DD max HODL':>14}")
    print("  " + "-" * 72)

    for year in years:
        year_df = df[df["year"] == year]
        idx_first = year_df.index[0]
        if idx_first == 0:
            eq_strat_begin = 100.0
            eq_hodl_begin = 100.0
        else:
            prev = df.loc[idx_first - 1]
            eq_strat_begin = prev["equity_strat"]
            eq_hodl_begin = prev["equity_hodl"]
        eq_strat_end = year_df["equity_strat"].iloc[-1]
        eq_hodl_end = year_df["equity_hodl"].iloc[-1]
        perf_strat = eq_strat_end / eq_strat_begin - 1
        perf_hodl = eq_hodl_end / eq_hodl_begin - 1
        delta = perf_strat - perf_hodl

        # DD intra-année rebasé au début de l'année (pour strat et HODL)
        strat_intra = year_df["equity_strat"] / eq_strat_begin
        dd_strat = (strat_intra / strat_intra.cummax() - 1).min()
        hodl_intra = year_df["equity_hodl"] / eq_hodl_begin
        dd_hodl = (hodl_intra / hodl_intra.cummax() - 1).min()

        print(f"  {year:<6} {perf_strat:>+12.1%} {perf_hodl:>+12.1%} {delta:>+10.1%} "
              f"{dd_strat:>+14.1%} {dd_hodl:>+14.1%}")

    # Perf annualisée (CAGR) sur 3 fenêtres : 5 ans, 10 ans, depuis le début.
    end_date = df["date"].iloc[-1]
    eq_strat_end = df["equity_strat"].iloc[-1]
    eq_hodl_end = df["equity_hodl"].iloc[-1]

    def _cagr_window(years_back: int | None) -> tuple[float, float, str] | None:
        if years_back is None:
            start_idx = 0
            label = f"depuis {years[0]}"
        else:
            cutoff = end_date - pd.DateOffset(years=years_back)
            mask = df["date"] <= cutoff
            if not mask.any():
                return None
            start_idx = int(df.index[mask][-1])
            label = f"{years_back} ans"
        eq_strat_start = df["equity_strat"].iloc[start_idx]
        eq_hodl_start = df["equity_hodl"].iloc[start_idx]
        days = (end_date - df["date"].iloc[start_idx]).days
        if days <= 0 or eq_strat_start <= 0 or eq_hodl_start <= 0:
            return None
        n = days / 365.25
        cagr_strat = (eq_strat_end / eq_strat_start) ** (1 / n) - 1
        cagr_hodl = (eq_hodl_end / eq_hodl_start) ** (1 / n) - 1
        return cagr_strat, cagr_hodl, label

    print("  " + "-" * 72)
    for yb in (3, 5, 10, None):
        res = _cagr_window(yb)
        if res is None:
            continue
        cagr_strat, cagr_hodl, label = res
        tag = f"Perf annualisée {label}"
        print(f"  {tag:<28}: strat {cagr_strat:+.1%}   |   HODL {cagr_hodl:+.1%}")

    # DD max global (peak-to-trough) sur toute l'histoire du journal.
    max_dd_strat = (df["equity_strat"] / df["equity_strat"].cummax() - 1).min()
    max_dd_hodl = (df["equity_hodl"] / df["equity_hodl"].cummax() - 1).min()
    tag = f"DD max depuis {years[0]}"
    print(f"  {tag:<28}: strat {max_dd_strat:+.1%}   |   HODL {max_dd_hodl:+.1%}")
    print(bar)
    print()


def main() -> None:
    """Exécution linéaire : signal du mois, puis récap 10 mois, puis récap annuel."""
    print()
    print("  BTC — Exploitation mensuelle (stratégie gelée 2026-05-01)")
    print("  ---------------------------------------------------------")
    if not _ensure_journal():
        return
    run_monthly_signal(dry_run=False)
    recap_monthly(10)
    recap_yearly()


if __name__ == "__main__":
    main()
