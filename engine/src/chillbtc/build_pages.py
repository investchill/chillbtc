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

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
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

# Front-matter Jekyll injecté en tête des pages auto-générées pour que
# GitHub Pages applique le layout commun (_layouts/page.html). Préservé à
# chaque regénération mensuelle puisque produit par le builder lui-même.
JEKYLL_FRONTMATTER = {
    "signaux.md": (
        "---\n"
        "layout: page\n"
        "title: Signal du mois\n"
        "description: L'allocation BTC à appliquer ce mois-ci, et les 2 signaux sous-jacents.\n"
        "---\n\n"
    ),
    "historique-annuel.md": (
        "---\n"
        "layout: page\n"
        "title: Historique annuel\n"
        "description: Performance annuelle ChillBTC vs HODL depuis 2015.\n"
        "---\n\n"
    ),
    "historique-mensuel.md": (
        "---\n"
        "layout: page\n"
        "title: Historique mensuel\n"
        "description: Toutes les positions mois par mois depuis 2015.\n"
        "---\n\n"
    ),
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
    return "ACHAT" if s == 1.0 else "CASH"


def _now_utc_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def build_signaux_md(journal_df: pd.DataFrame) -> str:
    """Page 1 — signal du mois courant + 6 derniers mois."""
    journal_df = journal_df.sort_values("date").reset_index(drop=True)
    last = journal_df.iloc[-1]
    last_date = pd.Timestamp(last["date"])
    cloture_str = f"{last_date.day:02d} {MOIS_FR[last_date.month]} {last_date.year}"

    pos_pct = float(last["position_pct"]) / 100.0
    sig_r1 = float(last["signal_r1"])
    sig_r3 = float(last["signal_r3"])
    ret_11m = float(last["return_11m"])
    close = float(last["close_btc_usd"])
    ratio_pl = float(last["ratio_price_fair_pl"])
    a_const = float(last["a_constant"])

    # Fallback : si le journal a été backfillé depuis cascade_position.csv,
    # ratio_pl et a_const sont vides → on les recalcule à la volée avec
    # la config gelée (A figée), équivalent à ce que produit live.
    if pd.isna(ratio_pl) or pd.isna(a_const):
        a_const = A_POWER_LAW
        days = (last_date - pd.Timestamp("2009-01-03")).days
        fair = 10 ** (a_const + N_EXP_R3 * np.log10(days))
        ratio_pl = close / fair

    # Allocation card — Design 1 (deux cartes BTC + USDC côte-à-côte).
    btc_pct_int = int(round(pos_pct * 100))
    usdc_pct_int = 100 - btc_pct_int
    state_emoji = _emoji_pos(pos_pct)
    btc_dim = " alloc-dim" if btc_pct_int == 0 else ""
    usdc_dim = " alloc-dim" if usdc_pct_int == 0 else ""

    alloc_html = (
        '<div class="signal-alloc">\n'
        f'  <div class="alloc-card alloc-btc{btc_dim}">\n'
        f'    <div class="alloc-state">{state_emoji}</div>\n'
        f'    <div class="alloc-pct">{btc_pct_int} %</div>\n'
        '    <div class="alloc-label">BTC</div>\n'
        '  </div>\n'
        f'  <div class="alloc-card alloc-usdc{usdc_dim}">\n'
        f'    <div class="alloc-state">{state_emoji}</div>\n'
        f'    <div class="alloc-pct">{usdc_pct_int} %</div>\n'
        '    <div class="alloc-label">USDC</div>\n'
        '  </div>\n'
        '</div>'
    )

    # Signal table — ligne Tendance + ligne Valorisation, tags pastel.
    r1_value_str = f"{ret_11m:+.1%}"
    r1_num_class = "positive" if ret_11m >= 0 else "negative"
    r3_value_str = f"{ratio_pl:.2f}"
    r1_decision_class = "achat" if sig_r1 == 1.0 else "cash"
    r3_decision_class = "achat" if sig_r3 == 1.0 else "cash"

    signal_table_html = (
        '<table class="signal-table">\n'
        '  <thead>\n'
        '    <tr>\n'
        '      <th>Signal</th>\n'
        '      <th class="num-col">Valeur</th>\n'
        '      <th class="arrow-col"></th>\n'
        '      <th>Décision</th>\n'
        '    </tr>\n'
        '  </thead>\n'
        '  <tbody>\n'
        '    <tr>\n'
        '      <td>Tendance <span class="signal-sub">(TSMOM 11 m)</span></td>\n'
        f'      <td class="num {r1_num_class}">{r1_value_str}</td>\n'
        '      <td class="arrow">→</td>\n'
        f'      <td><span class="decision {r1_decision_class}">'
        f'{_emoji_sig(sig_r1)} {_label_sig(sig_r1)}</span></td>\n'
        '    </tr>\n'
        '    <tr>\n'
        '      <td>Valorisation <span class="signal-sub">(Power Law)</span></td>\n'
        f'      <td class="num">{r3_value_str}</td>\n'
        '      <td class="arrow">→</td>\n'
        f'      <td><span class="decision {r3_decision_class}">'
        f'{_emoji_sig(sig_r3)} {_label_sig(sig_r3)}</span></td>\n'
        '    </tr>\n'
        '  </tbody>\n'
        '</table>'
    )

    lines = [
        "# Signal BTC",
        "",
        "> 📖 [Comprendre les 2 signaux et la méthodologie](methodologie.md)",
        "",
        alloc_html,
        "",
        "## Signaux du mois",
        "",
        signal_table_html,
        "",
        "## Contexte",
        "",
        f"- Prix BTC à la clôture du **{cloture_str}** : "
        f"**{close:,.0f} USD**".replace(",", " "),
        f"- Constante A Power Law : {a_const:.3f} "
        "(figée jusqu'à la prochaine revue annuelle)",
        "",
    ]

    # Section "N derniers mois" : titre dynamique, skip si <= 1 ligne
    # (le mois en cours est déjà affiché plus haut).
    n = min(6, len(journal_df))
    if n > 1:
        lines += [f"## {n} derniers mois", ""]
        last_n = journal_df.tail(n).iloc[::-1]
        for _, row in last_n.iterrows():
            d = pd.Timestamp(row["date"])
            p = float(row["position_pct"]) / 100.0
            r1 = float(row["signal_r1"])
            r3 = float(row["signal_r3"])
            lines.append(
                f"- **{d.year}-{d.month:02d}** : {_emoji_pos(p)} {int(p * 100)} % "
                f"— tendance {_label_sig(r1)}, valorisation {_label_sig(r3)}"
            )
        lines.append("")

    lines += [f"_Dernière mise à jour : {_now_utc_str()} (auto)._", ""]
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


def _yearly_dd(values: pd.Series) -> dict[int, float]:
    """DD max intra-année sur l'equity mensuelle (peak reset chaque 1ᵉʳ janvier).

    Pour la 1ʳᵉ et la dernière année partielles, calcul sur la fenêtre dispo.
    """
    df = pd.DataFrame({"v": values})
    df["year"] = df.index.year
    out: dict[int, float] = {}
    for year in sorted(df["year"].unique()):
        ydf = df[df["year"] == year]
        running_max = ydf["v"].cummax()
        dd_series = ydf["v"] / running_max - 1
        out[year] = float(dd_series.min())
    return out


def _annualized_n_years(values: pd.Series, n_years: int) -> float | None:
    """Perf annualisée sur les ``n_years`` dernières années (rolling = 12n mois).

    Retourne None si la série ne couvre pas assez de mois.
    """
    if len(values) <= n_years * 12:
        return None
    start = values.iloc[-(n_years * 12 + 1)]
    end = values.iloc[-1]
    return (end / start) ** (1 / n_years) - 1


def _annualized_total(values: pd.Series) -> float:
    """CAGR depuis le 1ᵉʳ point de la série."""
    n_years = len(values) / 12
    return (values.iloc[-1] / values.iloc[0]) ** (1 / n_years) - 1


def _max_dd_total(values: pd.Series) -> float:
    """DD max global sur toute la série."""
    running_max = values.cummax()
    dd = values / running_max - 1
    return float(dd.min())


def build_historique_annuel_md(table: pd.DataFrame) -> str:
    """Page 2 — tableau ASCII bloc-code, format inspiré de l'ancien README.

    Colonnes : année | perf strat | perf HODL | DD strat | DD HODL.
    Récap en dessous : perf annualisée 3/5/depuis-start, DD max global.
    """
    eq = table["equity_cascade"]
    btc = table["btc_close"]
    hodl = btc / btc.iloc[0] * eq.iloc[0]

    strat_ret = _yearly_returns(eq)
    hodl_ret_map = {y: r for y, r, _ in _yearly_returns(hodl)}
    strat_dd = _yearly_dd(eq)
    hodl_dd = _yearly_dd(hodl)

    start_str = f"{table.index[0].year}-{table.index[0].month:02d}"

    # Tableau ASCII
    table_lines = [
        "  année    perf ChillBTC    perf HODL   baisse max ChillBTC   baisse max HODL",
        "  ----------------------------------------------------------------------------",
    ]
    for year, ret_s, partial in strat_ret:
        ret_h = hodl_ret_map.get(year, 0.0)
        dd_s = strat_dd[year] * 100
        dd_h = hodl_dd[year] * 100
        marker = " *" if partial else "  "
        table_lines.append(
            f"  {year}{marker}   "
            f"{ret_s*100:+12.1f}%    "
            f"{ret_h*100:+8.1f}%   "
            f"{dd_s:+18.1f}%   "
            f"{dd_h:+14.1f}%"
        )
    table_lines.append("  ----------------------------------------------------------------------------")

    # Récap
    a3_s = _annualized_n_years(eq, 3)
    a5_s = _annualized_n_years(eq, 5)
    aT_s = _annualized_total(eq)
    a3_h = _annualized_n_years(hodl, 3)
    a5_h = _annualized_n_years(hodl, 5)
    aT_h = _annualized_total(hodl)
    dd_total_s = _max_dd_total(eq) * 100
    dd_total_h = _max_dd_total(hodl) * 100

    def _fmt_pair(s: float | None, h: float | None) -> str:
        s_str = f"{s*100:+6.1f}%" if s is not None else "  n/a "
        h_str = f"{h*100:+6.1f}%" if h is not None else "  n/a "
        return f"ChillBTC {s_str}   |   HODL {h_str}"

    pad = 32
    table_lines += [
        f"  {'Perf annualisée 3 ans'.ljust(pad)} : {_fmt_pair(a3_s, a3_h)}",
        f"  {'Perf annualisée 5 ans'.ljust(pad)} : {_fmt_pair(a5_s, a5_h)}",
        f"  {f'Perf annualisée depuis {start_str}'.ljust(pad)} : "
        f"{_fmt_pair(aT_s, aT_h)}",
        f"  {f'baisse max depuis {start_str}'.ljust(pad)} : "
        f"ChillBTC {dd_total_s:+6.1f}%   |   HODL {dd_total_h:+6.1f}%",
    ]

    lines = [
        "# Historique annuel — Stratégie ChillBTC vs HODL",
        "",
        "> **HODL** = acheter et garder, stratégie passive de référence "
        "(ne rien faire, conserver ses BTC en permanence). "
        "**baisse max** = plus grosse baisse temporaire du portefeuille "
        "dans l'année, sur papier (perte non-réalisée, tu n'as pas vendu).",
        "",
        f"Performances annuelles depuis {start_str} "
        f"(données CDD Bitstamp 2014-11, moins {N_TSMOM} mois d'amorçage tendance (TSMOM)). "
        "Les années marquées `*` sont partielles (démarrage de la simulation, année en cours).",
        "",
        "```",
        *table_lines,
        "```",
        "",
        "**Comment lire** :",
        "",
        "- **perf** : bilan entre le 31 décembre N-1 et le 31 décembre N. "
        "Ce qui s'est passé entre les deux dates n'est pas visible ici.",
        "- **baisse max** : la plus grosse baisse temporaire du portefeuille "
        "pendant l'année, **sur papier** (c'est une perte non-réalisée, tu n'as "
        "pas vendu). Exemple : un portefeuille qui passe de 100 à 70 puis remonte "
        "à 90 a une baisse max de -30 %, même si le résultat final n'est que -10 %.",
        "- **Perf annualisée 3 / 5 ans** : moyenne géométrique des 36 / 60 "
        "derniers mois (rolling, pas calendaire).",
        "",
        f"_Dernière mise à jour : {_now_utc_str()} (auto)._",
        "",
    ]
    return "\n".join(lines)


def build_historique_mensuel_md(table: pd.DataFrame) -> str:
    """Page 3 — toutes lignes mensuelles depuis 2014-11.

    Format : tableau ASCII bloc-code, colonnes mois / alloc / BTC close /
    perf strat mensuelle / perf HODL mensuelle. Ordre inversé.
    """
    eq = table["equity_cascade"]
    btc = table["btc_close"]
    pos_effective = table["position"].shift(1).fillna(0.0)
    hodl = btc / btc.iloc[0] * eq.iloc[0]

    strat_monthly = eq.pct_change()
    hodl_monthly = hodl.pct_change()

    start_str = f"{table.index[0].year}-{table.index[0].month:02d}"

    table_lines = [
        "  mois     alloc      BTC USD    ChillBTC    HODL",
        "  ------------------------------------------------",
    ]
    for date in reversed(table.index):
        p = float(pos_effective.loc[date])
        sm = strat_monthly.loc[date]
        hm = hodl_monthly.loc[date]
        bt = float(btc.loc[date])
        emoji = _emoji_pos(p)
        bt_str = f"{bt:>7,.0f}".replace(",", " ")
        if pd.isna(sm) or pd.isna(hm):
            line = (
                f"  {date.year}-{date.month:02d}  {emoji} {int(p*100):3d} %   "
                f"{bt_str}    (début de la simulation)"
            )
        else:
            line = (
                f"  {date.year}-{date.month:02d}  {emoji} {int(p*100):3d} %   "
                f"{bt_str}   {float(sm)*100:+5.1f}%  {float(hm)*100:+5.1f}%"
            )
        table_lines.append(line)

    lines = [
        "# Historique mensuel — Stratégie ChillBTC vs HODL",
        "",
        "> **HODL** = acheter et garder, stratégie passive de référence "
        "(ne rien faire, conserver ses BTC en permanence).",
        "",
        f"Une ligne par mois depuis {start_str} "
        f"(données CDD Bitstamp 2014-11, moins {N_TSMOM} mois d'amorçage tendance (TSMOM)).",
        "",
        "**Comment lire** :",
        "",
        "- **mois** : mois calendaire. Ligne `2025-11` = novembre 2025.",
        "- **alloc** : position détenue **pendant** ce mois, décidée sur "
        "la clôture du mois précédent. Ligne `2025-11` → alloc appliquée "
        "du 1ᵉʳ au 30 novembre, calculée sur la clôture du 31 octobre.",
        "- **BTC USD** : prix de clôture du **dernier jour du mois**. "
        "Ligne `2025-11` → clôture du 30 novembre.",
        "- **ChillBTC / HODL** : variation **mensuelle** du portefeuille "
        "(clôture du mois précédent → clôture du mois courant).",
        "",
        "```",
        *table_lines,
        "```",
        "",
        f"_Dernière mise à jour : {_now_utc_str()} (auto)._",
        "",
    ]
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
        path.write_text(JEKYLL_FRONTMATTER[name] + content, encoding="utf-8")
        print(f"  ✅ {path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
