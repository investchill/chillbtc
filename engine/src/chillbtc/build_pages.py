# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# Copyright © 2026 ChillBTC
"""Génère les 3 pages auto-update du repo public.

Lit ``live_journal.csv`` (signal du mois courant + récents) et recalcule
le backtest historique cascade R1+R3 (pages 2 & 3). Écrit dans ``docs/`` :

- ``signaux.md`` — signal du mois courant + 6 derniers mois
- ``historique-annuel.md`` — perf annuelle stratégie / HODL depuis 2014
- ``historique-mensuel.md`` — toutes lignes mensuelles depuis 2014-11

Le workflow GitHub Actions appelle ``chillbtc-monthly`` (qui rafraîchit
les données et appende la dernière ligne au journal) avant ``chillbtc-pages``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from chillbtc.backtest import FEE_CONSERVATIVE
from chillbtc.cascade import build_cascade_position, equity_from_cascade
from chillbtc.data import load_or_fetch
from chillbtc.monthly_signal import (
    A_POWER_LAW,
    CONVENTION,
    K_HIGH_R3,
    K_LOW_R3,
    N_EXP_R3,
    N_TSMOM,
    _drop_partial_current_month,
)
from chillbtc.rules import signal_power_law, signal_tsmom

MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _emoji_pos(p: float) -> str:
    if p >= 0.99:
        return "🟢"
    if p >= 0.49:
        return "🟡"
    return "🔴"


def _label_pos(p: float) -> str:
    if p == 1.0:
        return "100 % BTC"
    if p == 0.5:
        return "50 % BTC + 50 % USDC"
    return "0 % BTC (100 % USDC)"


def _emoji_sig(s: float) -> str:
    return "✅" if s == 1.0 else "❌"


def _label_sig(s: float) -> str:
    return "BUY" if s == 1.0 else "CASH"


def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_signaux_md(journal_df: pd.DataFrame) -> str:
    """Page 1 — signal du mois courant + 6 derniers mois."""
    journal_df = journal_df.sort_values("date").reset_index(drop=True)
    last = journal_df.iloc[-1]
    last_date = pd.Timestamp(last["date"])
    mois = f"{MOIS_FR[last_date.month]} {last_date.year}"

    pos_pct = float(last["position_pct"]) / 100.0
    sig_r1 = float(last["signal_r1"])
    sig_r3 = float(last["signal_r3"])
    ret_11m = float(last["return_11m"])
    ratio_pl = float(last["ratio_price_fair_pl"])
    close = float(last["close_btc_usd"])
    a_const = float(last["a_constant"])

    lines = [
        f"# Signal BTC — {mois}",
        "",
        f"## {_emoji_pos(pos_pct)} {_label_pos(pos_pct)}",
        "",
        "## Signaux du mois",
        "",
        f"- **R1 TSMOM 11m** : {ret_11m:+.1%}  →  {_emoji_sig(sig_r1)} {_label_sig(sig_r1)}",
        f"- **R3 Power Law** : {ratio_pl:.2f}  →  {_emoji_sig(sig_r3)} {_label_sig(sig_r3)}",
        "",
        "## Contexte",
        "",
        f"- Prix BTC clôture mois : **{close:,.0f} USD**".replace(",", " "),
        f"- Constante A Power Law : {a_const:.3f} "
        "(figée jusqu'à la prochaine revue annuelle, 1ᵉʳ janvier)",
        "",
        "## 6 derniers mois",
        "",
    ]

    last_6 = journal_df.tail(6).iloc[::-1]
    for _, row in last_6.iterrows():
        d = pd.Timestamp(row["date"])
        p = float(row["position_pct"]) / 100.0
        r1 = float(row["signal_r1"])
        r3 = float(row["signal_r3"])
        lines.append(
            f"- **{d.year}-{d.month:02d}** : {_emoji_pos(p)} {int(p * 100)} % "
            f"— R1 {_label_sig(r1)}, R3 {_label_sig(r3)}"
        )

    lines += ["", f"_Dernière mise à jour : {_now_utc_str()} (auto)._", ""]
    return "\n".join(lines)


def _yearly_returns(values: pd.Series) -> list[tuple[int, float, bool]]:
    """Retourne ``[(year, return_annuel, partial_year), ...]``.

    - 1ʳᵉ année du backtest : return calculé depuis le 1ᵉʳ point dispo (partielle).
    - Année en cours : return calculé depuis le close de décembre N-1 (partielle).
    - Années pleines : return = close_dec_N / close_dec_N-1 - 1.
    """
    df = pd.DataFrame({"v": values})
    df["year"] = df.index.year
    out = []
    years = sorted(df["year"].unique())
    first_year = years[0]
    last_year = years[-1]
    for year in years:
        ydf = df[df["year"] == year]
        if year == first_year:
            start = values.iloc[0]
        else:
            prev = df[df["year"] == year - 1]
            start = prev["v"].iloc[-1]
        end = ydf["v"].iloc[-1]
        partial = (year == first_year) or (year == last_year and len(ydf) < 12)
        out.append((year, end / start - 1, partial))
    return out


def build_historique_annuel_md(table: pd.DataFrame) -> str:
    """Page 2 — perf annuelle stratégie / HODL.

    Deux séries présentées en parallèle, sans colonne delta (cf. spec).
    """
    eq = table["equity_cascade"]
    btc = table["btc_close"]
    hodl = btc / btc.iloc[0] * eq.iloc[0]

    strat_ret = _yearly_returns(eq)
    hodl_ret = _yearly_returns(hodl)

    start_str = f"{table.index[0].year}-{table.index[0].month:02d}"
    lines = [
        "# Historique annuel — Stratégie ChillBTC vs HODL",
        "",
        f"Performances annuelles depuis {start_str} "
        f"(données CDD Bitstamp 2014-11, moins {N_TSMOM} mois de warm-up R1 TSMOM). "
        "L'année de démarrage et l'année en cours sont partielles.",
        "",
        "## Stratégie ChillBTC (cascade R1 + R3, mode C)",
        "",
    ]
    for year, ret, partial in strat_ret:
        suffix = " _(partielle)_" if partial else ""
        lines.append(f"- **{year}** : {ret:+.1%}{suffix}")

    lines += [
        "",
        "## HODL (buy-and-hold BTC)",
        "",
    ]
    for year, ret, partial in hodl_ret:
        suffix = " _(partielle)_" if partial else ""
        lines.append(f"- **{year}** : {ret:+.1%}{suffix}")

    lines += ["", f"_Dernière mise à jour : {_now_utc_str()} (auto)._", ""]
    return "\n".join(lines)


def build_historique_mensuel_md(table: pd.DataFrame) -> str:
    """Page 3 — toutes lignes mensuelles depuis 2014-11.

    Format : ``AAAA-MM | alloc | perf cumul strat | perf cumul HODL``.
    """
    eq = table["equity_cascade"]
    btc = table["btc_close"]
    pos = table["position"]
    hodl = btc / btc.iloc[0] * eq.iloc[0]

    eq_cum = eq / eq.iloc[0] - 1
    hodl_cum = hodl / hodl.iloc[0] - 1

    start_str = f"{table.index[0].year}-{table.index[0].month:02d}"
    lines = [
        "# Historique mensuel — Stratégie ChillBTC vs HODL",
        "",
        f"Une ligne par mois depuis {start_str} "
        f"(données CDD Bitstamp 2014-11, moins {N_TSMOM} mois de warm-up R1 TSMOM). "
        "`perf cumul` = capitalisation depuis la base 100, en pourcentage.",
        "",
    ]
    for date in table.index:
        p = float(pos.loc[date])
        ec = float(eq_cum.loc[date])
        hc = float(hodl_cum.loc[date])
        emoji = _emoji_pos(p)
        lines.append(
            f"- **{date.year}-{date.month:02d}** : {emoji} {int(p * 100):3d} % "
            f"| strat {ec:+8.1%} | HODL {hc:+8.1%}"
        )

    lines += ["", f"_Dernière mise à jour : {_now_utc_str()} (auto)._", ""]
    return "\n".join(lines)


def _compute_frozen_cascade_history(monthly_csv: Path) -> pd.DataFrame:
    """Recalcule l'historique du backtest avec la **config gelée**.

    Cohérent avec ``monthly_signal.py`` (params figés, A figée — pas de
    refit walk-forward). Démarrage = 1ᵉʳ mois où R1 a un signal valide
    (= mois ``N_TSMOM + 1``-ième après le début des données CDD).

    Pas d'usage de ``_trim_common_warmup`` (legacy backtest exploratoire
    qui drop 18 mois pour couvrir le grid R1 n=6..18 ; la cascade gelée
    n'a besoin que de ``N_TSMOM = 11`` mois).
    """
    monthly = _drop_partial_current_month(load_or_fetch(monthly_csv))

    r1 = signal_tsmom(monthly, n=N_TSMOM)
    r3 = signal_power_law(
        monthly,
        k_low=K_LOW_R3,
        k_high=K_HIGH_R3,
        n_exponent=N_EXP_R3,
        a_constant=A_POWER_LAW,
    )

    first_valid = r1.first_valid_index()
    monthly = monthly.loc[first_valid:]
    r1 = r1.loc[first_valid:]
    r3 = r3.loc[first_valid:]

    position = build_cascade_position(r1, r3, convention=CONVENTION)
    equity = equity_from_cascade(monthly, position, fee_per_switch=FEE_CONSERVATIVE)

    return pd.DataFrame({
        "btc_close": monthly["close_usd"],
        "position": position,
        "equity_cascade": equity,
    })


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    engine_root = Path(__file__).resolve().parents[2]

    journal_csv = engine_root / "output" / "live_journal.csv"
    if not journal_csv.exists():
        raise FileNotFoundError(
            f"{journal_csv} introuvable. Lance d'abord `uv run chillbtc-monthly`."
        )
    journal = pd.read_csv(journal_csv)
    if journal.empty:
        raise ValueError(
            f"{journal_csv} est vide. Lance d'abord `uv run chillbtc-monthly`."
        )

    print("Recalcul backtest historique cascade R1+R3 (config gelée)...")
    monthly_csv = engine_root / "data" / "btc_monthly.csv"
    table = _compute_frozen_cascade_history(monthly_csv)
    print(
        f"  Fenêtre : {table.index[0].date()} → {table.index[-1].date()} "
        f"({len(table)} mois, warm-up R1 n={N_TSMOM})"
    )

    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    pages = {
        "signaux.md": build_signaux_md(journal),
        "historique-annuel.md": build_historique_annuel_md(table),
        "historique-mensuel.md": build_historique_mensuel_md(table),
    }
    for name, content in pages.items():
        path = docs_dir / name
        path.write_text(content, encoding="utf-8")
        print(f"  ✅ {path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
