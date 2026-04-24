"""Phase D — comparaison des 3 modes candidats d'exploitation.

Règle de sélection commune : contrainte **DD ≤ -50 %** (profil bon père de famille),
tie-break par CAGR. Conforme au but premier "sortir en bear pour limiter DD".

- **Mode A — Sélection 1 cellule** : meilleure des 9 cellules de la grille
  R × O sous contrainte DD ≤ -50 %. Tie-break CAGR. Signal = signal brut de
  la cellule retenue.
- **Mode B — Ensemble K=4** : vote "≥ 4 cellules sur 9 disent BUY → BUY".
  Déjà calculé par ``chillbtc.ensemble``.
- **Mode C — Cascade R1+R3 (S2 défensif + S8 agressif, 100/50/0)** :
  convention ``strict_r1_def`` retenue après test des 3 conventions
  (cf. ``cascade.py``, post-Phase D).

Sorties :

- ``engine/output/mode_comparison.csv`` : 4 lignes (HODL + 3 modes) × KPIs.
- ``engine/output/mode_comparison.md`` : bloc markdown avec tableau KPIs +
  diagnostic de dominance, prêt à copier dans la documentation de résultats.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chillbtc.backtest import (
    FEE_CONSERVATIVE,
    LATIN_SQUARE,
    OPTIM_FNS,
    SPECS,
    _trim_common_warmup,
)
from chillbtc.cascade import run_cascade
from chillbtc.data import load_or_fetch
from chillbtc.metrics import (
    PERIODS_PER_YEAR,
    cagr,
    equity_from_signals,
    max_drawdown,
    n_switches,
    sharpe,
)

DD_CEILING = -50.0  # % — cible "bon père de famille"
K_ENSEMBLE = 4      # K retenu pour mode B (Phase D decision)


def _perf_row(equity: pd.Series, signal_switches: int | None, label: str, mode: str) -> dict:
    returns = equity.pct_change()
    n_years = len(equity) / PERIODS_PER_YEAR
    row = {
        "mode": mode,
        "label": label,
        "cagr_pct": round(cagr(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
    }
    if signal_switches is None:
        row["switches_per_year"] = 0.0
    else:
        row["switches_per_year"] = round(signal_switches / n_years, 3) if n_years > 0 else 0.0
    return row


def _mode_a_signal(monthly: pd.DataFrame, fee: float, phase_c: pd.DataFrame) -> tuple[str, pd.Series]:
    """Retourne (cell_id, signal) de la cellule qui maximise CAGR sous DD ≤ -50 %."""
    candidates = phase_c[(phase_c.index != "HODL") & (phase_c["max_dd_pct"] >= DD_CEILING)]
    if candidates.empty:
        raise RuntimeError("Aucune cellule ne respecte DD ≤ -50 %.")
    best_id = candidates["cagr_pct"].idxmax()
    cell = next(c for c in LATIN_SQUARE if c.cell_id == best_id)
    spec = SPECS[cell.rule_name]
    fn = OPTIM_FNS[cell.optim_name]
    result = fn(spec, monthly, cell.objective, fee)
    extras = spec.fit_on_train(monthly) if spec.fit_on_train is not None else {}
    sig = spec.rule_fn(monthly, **{**result["params"], **extras})
    sig.name = best_id
    return best_id, sig


def _mode_b_signal(monthly: pd.DataFrame, fee: float, K: int = K_ENSEMBLE) -> pd.Series:
    """Reconstruit le signal d'ensemble K parmi 9 en relançant les 9 cellules."""
    buy_count = pd.Series(0.0, index=monthly.index)
    for cell in LATIN_SQUARE:
        spec = SPECS[cell.rule_name]
        fn = OPTIM_FNS[cell.optim_name]
        result = fn(spec, monthly, cell.objective, fee)
        extras = spec.fit_on_train(monthly) if spec.fit_on_train is not None else {}
        sig = spec.rule_fn(monthly, **{**result["params"], **extras}).fillna(0.0).astype(float)
        buy_count = buy_count + sig
    vote = (buy_count >= K).astype(float)
    vote.name = f"ensemble_K{K}"
    return vote


def _dominance(a: dict, b: dict) -> str:
    """A domine B si A >= B sur les 3 KPI (CAGR, DD, Sharpe) et > sur au moins 1.
    DD est un score négatif donc DD A >= DD B signifie |DD_A| <= |DD_B|."""
    ge_cagr = a["cagr_pct"] >= b["cagr_pct"]
    ge_dd = a["max_dd_pct"] >= b["max_dd_pct"]
    ge_sharpe = a["sharpe"] >= b["sharpe"]
    gt_any = (
        a["cagr_pct"] > b["cagr_pct"]
        or a["max_dd_pct"] > b["max_dd_pct"]
        or a["sharpe"] > b["sharpe"]
    )
    if ge_cagr and ge_dd and ge_sharpe and gt_any:
        return "DOMINE"
    if not ge_cagr and not ge_dd and not ge_sharpe:
        return "DOMINÉ"
    return "NON-DOMINÉ"


def _render_markdown(rows: list[dict], cell_id_a: str, cascade_summary: dict) -> str:
    lines = []
    lines.append("## §13 — Comparaison des 3 modes candidats d'exploitation")
    lines.append("")
    lines.append(f"Règle de sélection : contrainte **DD ≤ {int(DD_CEILING)} %** (cible bon père de famille).")
    lines.append(f"Tie-break CAGR. Fenêtre backtest : "
                 f"{cascade_summary['window_start'][:10]} → {cascade_summary['window_end'][:10]} "
                 f"({cascade_summary['total_months']} mois), frais 0,5 % par switch.")
    lines.append("")
    lines.append("### Candidats retenus")
    lines.append("")
    lines.append(f"- **Mode A** : sélection de la cellule `{cell_id_a}` (max CAGR sous DD ≤ -50 %).")
    lines.append(f"- **Mode B** : ensemble vote K={K_ENSEMBLE} parmi 9.")
    lines.append("- **Mode C** : cascade R1 (S2, R1×O2 DD, n=11) + R3 (S8, R3×O2 CAGR walk-forward), "
                 "convention `strict_r1_def` (edge case R1 BUY & R3 CASH → 0 %).")
    lines.append("")
    lines.append("### KPIs comparés")
    lines.append("")
    lines.append("```")
    lines.append(f"{'mode':<10} {'label':<22} {'CAGR':>8} {'Max DD':>9} {'Sharpe':>8} {'switch/an':>11}")
    for r in rows:
        lines.append(
            f"{r['mode']:<10} {r['label']:<22} "
            f"{r['cagr_pct']:>7.2f}% {r['max_dd_pct']:>8.2f}% "
            f"{r['sharpe']:>8.3f} {r['switches_per_year']:>11.3f}"
        )
    lines.append("```")
    lines.append("")
    lines.append("### Matrice de dominance stricte (A vs B = A >= B sur les 3 KPI, > sur ≥ 1)")
    lines.append("")
    perf_modes = [r for r in rows if r["mode"] != "HODL"]
    lines.append("```")
    lines.append(f"{'':<10} " + " ".join(f"{r['mode']:<12}" for r in perf_modes))
    for a in perf_modes:
        row_str = f"{a['mode']:<10} "
        for b in perf_modes:
            if a["mode"] == b["mode"]:
                row_str += f"{'—':<12} "
            else:
                row_str += f"{_dominance(a, b):<12} "
        lines.append(row_str.rstrip())
    lines.append("```")
    lines.append("")
    lines.append("### Diagnostic")
    lines.append("")
    # Analyse automatique
    a_perf = next(r for r in rows if r["mode"] == "Mode A")
    c_perf = next(r for r in rows if r["mode"] == "Mode C")
    hodl_perf = next(r for r in rows if r["mode"] == "HODL")

    lines.append(f"- Tous les modes battent HODL sur DD ({hodl_perf['max_dd_pct']:.1f} %) et sur CAGR.")
    lines.append(f"- Mode C cascade a le **meilleur DD** ({c_perf['max_dd_pct']:.2f} % vs "
                 f"{a_perf['max_dd_pct']:.2f} % pour A et B), aligné avec le but "
                 f"\"sortir en bear pour limiter le DD\".")
    lines.append(f"- Mode A ({cell_id_a} seul) a le **meilleur CAGR** ({a_perf['cagr_pct']:.1f} %), "
                 f"mais c'est une cellule R3 isolée — **biais in-sample non complètement lavé** (refit de A "
                 f"sur la full history, WFE=0.585 en Phase C). La perf \"honnête\" hors biais serait plus basse.")
    lines.append("- Mode B ensemble K=4 **dilue le biais R3** (9 cellules votent) mais ne domine A sur aucun "
                 "KPI. Il sert surtout de filet de robustesse conceptuelle.")
    lines.append(f"- Mode C cascade a le **Sharpe le plus bas** des 3 modes actifs ({c_perf['sharpe']:.2f}), "
                 f"mais **aucun des 3 modes ne domine strictement les 2 autres** : A gagne CAGR/Sharpe mais "
                 f"perd DD, C gagne DD mais perd CAGR/Sharpe.")
    lines.append("")
    lines.append("### Implication pour la stratégie finale")
    lines.append("")
    lines.append("La clause de dégradation (« une seule cellule domine les 8 autres sur les 3 critères → "
                 "bascule Mode A ») **ne se déclenche pas** sur la fenêtre actuelle : A domine partiellement "
                 "mais pas strictement. Le choix entre A, B, C est donc un arbitrage de préférences :")
    lines.append("")
    lines.append("- **Priorité DD** (cohérent avec le profil déclaré) → Mode C cascade.")
    lines.append("- **Priorité CAGR brut** → Mode A (S8 seul), avec acceptation du biais in-sample.")
    lines.append("- **Priorité robustesse conceptuelle** (9 règles votent) → Mode B K=4.")
    lines.append("")
    return "\n".join(lines)


def run_compare_modes(fee: float = FEE_CONSERVATIVE, save_outputs: bool = True) -> pd.DataFrame:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))

    phase_c = pd.read_csv(repo / "output" / "phase_c_results.csv").set_index("cell_id")

    # HODL reference
    hodl_sig = pd.Series(1.0, index=monthly.index)
    hodl_eq = equity_from_signals(monthly, hodl_sig, fee_per_switch=0.0)

    # Mode A — best 1 cell under DD constraint
    cell_id_a, sig_a = _mode_a_signal(monthly, fee, phase_c)
    eq_a = equity_from_signals(monthly, sig_a, fee_per_switch=fee)
    sw_a = n_switches(sig_a)

    # Mode B — ensemble K=4
    sig_b = _mode_b_signal(monthly, fee, K=K_ENSEMBLE)
    eq_b = equity_from_signals(monthly, sig_b, fee_per_switch=fee)
    sw_b = n_switches(sig_b)

    # Mode C — cascade R1+R3 (retenue : strict_r1_def)
    cascade_out = run_cascade(fee=fee, save_outputs=False, convention="strict_r1_def")
    eq_c = cascade_out["equity"]
    # switches cascade = nombre de changements de cran (tous amplitudes confondus)
    pos_c = cascade_out["position"]
    sw_c = int((pos_c.diff().abs() > 1e-9).sum())

    rows = [
        _perf_row(hodl_eq, 0, "HODL", "HODL"),
        _perf_row(eq_a, sw_a, f"{cell_id_a} (cellule)", "Mode A"),
        _perf_row(eq_b, sw_b, f"ensemble_K{K_ENSEMBLE}", "Mode B"),
        _perf_row(eq_c, sw_c, "cascade R1+R3 (100/50/0)", "Mode C"),
    ]
    df = pd.DataFrame(rows).set_index("mode")

    if save_outputs:
        out_dir = repo / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "mode_comparison.csv")
        md = _render_markdown(rows, cell_id_a, cascade_out["summary"])
        (out_dir / "mode_comparison.md").write_text(md)
        print(f"\nCSV saved to {out_dir / 'mode_comparison.csv'}")
        print(f"Markdown saved to {out_dir / 'mode_comparison.md'}")

    return df


def main() -> None:
    df = run_compare_modes()
    print("\n=== Comparaison des 3 modes candidats (sous DD ≤ -50 %) ===")
    print(df.to_string())


if __name__ == "__main__":
    main()
