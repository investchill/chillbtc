"""Side experiment — Monthly vs Weekly cadence comparison for Mode C cascade.

Runs the frozen Mode C cascade at both cadences (monthly via ``cascade.run_cascade``,
weekly via ``cascade_weekly.run_cascade_weekly``) under two fee assumptions:
0.2 % (realistic Binance) and 0.5 % (conservative backtest).

Never modifies the monthly frozen outputs: the monthly cascade is re-run with
``save_outputs=False``.

Produces two files in ``engine/output/``:
- ``cadence_comparison.csv`` : raw scenario stats (4 rows)
- ``cadence_comparison.md``  : human-readable side-by-side report
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chillbtc.cascade import run_cascade
from chillbtc.cascade_weekly import run_cascade_weekly

FEES = (0.002, 0.005)


def run_all_scenarios() -> pd.DataFrame:
    rows: list[dict] = []
    for fee in FEES:
        out_m = run_cascade(fee=fee, save_outputs=False)
        sm = out_m["summary"]
        rows.append(
            {
                "cadence": "monthly",
                "fee_pct": round(fee * 100, 2),
                "cagr_pct": sm["cagr_pct"],
                "max_dd_pct": sm["max_dd_pct"],
                "sharpe": sm["sharpe"],
                "n_switches": sm["n_switches"],
                "switches_per_year": sm["switches_per_year"],
                "total_turnover": sm["total_turnover"],
                "final_equity": round(float(out_m["equity"].iloc[-1]), 2),
                "window_start": sm["window_start"][:10],
                "window_end": sm["window_end"][:10],
                "n_periods": sm["total_months"],
            }
        )

        save_w = fee == 0.005
        out_w = run_cascade_weekly(fee=fee, save_outputs=save_w)
        sw = out_w["summary"]
        rows.append(
            {
                "cadence": "weekly",
                "fee_pct": round(fee * 100, 2),
                "cagr_pct": sw["cagr_pct"],
                "max_dd_pct": sw["max_dd_pct"],
                "sharpe": sw["sharpe"],
                "n_switches": sw["n_switches"],
                "switches_per_year": sw["switches_per_year"],
                "total_turnover": sw["total_turnover"],
                "final_equity": sw["final_equity"],
                "window_start": sw["window_start"][:10],
                "window_end": sw["window_end"][:10],
                "n_periods": sw["n_periods"],
            }
        )
    return pd.DataFrame(rows)


def _verdict(df: pd.DataFrame) -> str:
    """Verdict sur trois critères décisifs.

    Rappel sur les signes (DD est stocké en négatif, ex. -40.3 %) :
    - ``d_dd = we_dd - mo_dd`` est **positif** quand hebdo protège mieux
      (ex. -36 − (-40) = +4 pp de protection gagnée).
    - ``d_cagr`` positif = hebdo gagne en CAGR.
    - ``d_sharpe`` positif = hebdo plus efficient risque-ajusté.
    """
    lines = ["## Verdict\n"]
    for fee in FEES:
        sub = df[df["fee_pct"] == round(fee * 100, 2)]
        mo = sub[sub["cadence"] == "monthly"].iloc[0]
        we = sub[sub["cadence"] == "weekly"].iloc[0]
        d_cagr = we["cagr_pct"] - mo["cagr_pct"]
        dd_gain_pp = we["max_dd_pct"] - mo["max_dd_pct"]  # positif = gain
        d_sh = we["sharpe"] - mo["sharpe"]
        d_sw = we["switches_per_year"] - mo["switches_per_year"]

        if dd_gain_pp >= 3.0 and d_sh >= 0.10:
            verdict = "OUI clair"
        elif dd_gain_pp >= 1.0 or d_sh >= 0.05:
            verdict = "marginal"
        else:
            verdict = "NON"

        lines.append(
            f"- **Frais {fee*100:.1f} %** — ΔCAGR : {d_cagr:+.2f} pp · "
            f"gain DD : {dd_gain_pp:+.2f} pp (positif = hebdo protège mieux) · "
            f"ΔSharpe : {d_sh:+.3f} · Δswitches/an : {d_sw:+.2f} → "
            f"**{verdict}**"
        )
    lines.append("")
    lines.append(
        "Seuils utilisés : *OUI clair* = gain DD ≥ 3 pp ET ΔSharpe ≥ +0.10. "
        "*Marginal* = gain DD ≥ 1 pp OU ΔSharpe ≥ +0.05. "
        "En dessous, *NON* : le hebdo ne justifie pas l'effort 4× par rapport "
        "au mensuel set-and-forget."
    )
    return "\n".join(lines)


def render_markdown(df: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("# Comparaison cadence — mensuel vs hebdo\n")
    lines.append(
        "**Side experiment** : stratégie frozen 2026-05-01 intacte. Objectif : "
        "répondre à la question *« passer en check hebdo dimanche soir vaut-il "
        "le coup vs le mensuel 1ᵉʳ du mois ? »*. Mode C cascade R1+R3 "
        "(`strict_r1_def`), paramètres figés : R1 TSMOM n=11 mois = 48 "
        "semaines, R3 Power Law k_low=0.6, k_high=2.5, N_exponent=5.8, "
        "constante A refit sur full série (même politique que la cascade "
        "mensuelle). Signaux évalués au close fin de mois (mensuel) ou au "
        "close du dimanche (hebdo). Friction proportionnelle au turnover "
        "(switch 1→0.5 coûte 0.5 × fee).\n"
    )

    for fee in FEES:
        sub = df[df["fee_pct"] == round(fee * 100, 2)]
        mo = sub[sub["cadence"] == "monthly"].iloc[0]
        we = sub[sub["cadence"] == "weekly"].iloc[0]

        lines.append(f"## Frais {fee*100:.1f} % par switch\n")
        lines.append("```")
        lines.append(
            "Métrique                Mensuel        Hebdo         Δ (hebdo − mensuel)"
        )
        lines.append(
            f"CAGR                    {mo['cagr_pct']:7.2f} %    "
            f"{we['cagr_pct']:7.2f} %    {we['cagr_pct'] - mo['cagr_pct']:+.2f} pp"
        )
        lines.append(
            f"Max Drawdown            {mo['max_dd_pct']:7.2f} %    "
            f"{we['max_dd_pct']:7.2f} %    {we['max_dd_pct'] - mo['max_dd_pct']:+.2f} pp"
        )
        lines.append(
            f"Sharpe annualisé        {mo['sharpe']:7.3f}      "
            f"{we['sharpe']:7.3f}      {we['sharpe'] - mo['sharpe']:+.3f}"
        )
        lines.append(
            f"Switches (total)        {int(mo['n_switches']):5d}        "
            f"{int(we['n_switches']):5d}        "
            f"{int(we['n_switches'] - mo['n_switches']):+d}"
        )
        lines.append(
            f"Switches / an           {mo['switches_per_year']:7.2f}      "
            f"{we['switches_per_year']:7.2f}      "
            f"{we['switches_per_year'] - mo['switches_per_year']:+.2f}"
        )
        lines.append(
            f"Turnover cumulé         {mo['total_turnover']:7.2f}      "
            f"{we['total_turnover']:7.2f}      "
            f"{we['total_turnover'] - mo['total_turnover']:+.2f}"
        )
        lines.append(
            f"Equity finale (base 100) {mo['final_equity']:8.2f}     "
            f"{we['final_equity']:8.2f}     "
            f"×{we['final_equity']/mo['final_equity']:.2f}"
        )
        lines.append("")
        lines.append(
            f"Fenêtre mensuel  : {mo['window_start']} → {mo['window_end']} "
            f"({mo['n_periods']} mois)"
        )
        lines.append(
            f"Fenêtre hebdo    : {we['window_start']} → {we['window_end']} "
            f"({we['n_periods']} semaines)"
        )
        lines.append("```\n")

    lines.append(_verdict(df))
    return "\n".join(lines)


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    df = run_all_scenarios()
    out_csv = repo / "output" / "cadence_comparison.csv"
    out_md = repo / "output" / "cadence_comparison.md"
    df.to_csv(out_csv, index=False)
    out_md.write_text(render_markdown(df))
    print("\n=== Comparaison cadence ===")
    print(df.to_string(index=False))
    print(f"\nSaved {out_csv}")
    print(f"Saved {out_md}")


if __name__ == "__main__":
    main()
