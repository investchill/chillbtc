"""Export gsheet — backtest + simulateur perso + what-if futur.

Génère ``engine/output/export_gsheet_backtest.csv`` avec :

- **Section 1 (ligne 1)** : 3 cellules d'input modifiables dans gsheet
  (``date_entrée`` en B1, ``montant_€`` en E1, ``btc_futur_usd`` en H1).
- **Section 2 (lignes 4 → 4+N)** : backtest historique 119 mois (2016-05 → 2026-03)
  avec 7 colonnes :
    - ``date``, ``btc_close``, ``position`` : valeurs statiques.
    - ``equity_strat_base100``, ``equity_hodl_base100`` : formules gsheet
      (base 100 à la 1ʳᵉ ligne).
    - ``equity_perso_strat``, ``equity_perso_hodl`` : formules conditionnelles
      sur ``$B$1`` (date d'entrée) et ``$E$1`` (montant), 0 avant la date,
      puis composent à partir du montant.
- **Section 3 (2 lignes what-if en bas)** : projection 2026-05-31 avec
  ``$H$1`` comme prix BTC hypothétique. Formules calculent return_11m,
  signal R1, ratio prix/fair_PL, signal R3 (hystérésis depuis état courant
  BUY), position cascade.

Caveat : les formules **ignorent les frais 0,5 %/switch** (cf. caveat
monthly process §J3). Impact ≈ 0,5 %/an. Le backtest Python
``cascade.py`` est la source officielle des chiffres avec frais.

L'état R3 au 2026-04-30 est hardcodé comme BUY (dernière observation
backtest : agg=1 fin mars 2026, ratio=0.55 < k_low=0.6). À réactualiser
chaque mois quand le script live ``chillbtc-monthly`` confirme l'état.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

from chillbtc.backtest import _trim_common_warmup
from chillbtc.cascade import build_cascade_position
from chillbtc.data import load_or_fetch
from chillbtc.rules import fit_power_law, signal_power_law, signal_tsmom

# Paramètres figés (valeurs canoniques)
N_TSMOM = 11
K_LOW_PL = 0.6
K_HIGH_PL = 2.5
N_EXPONENT_PL = 5.8
CONVENTION = "strict_r1_def"

# État R3 au 2026-04-30 (dernière obs backtest = BUY, ratio ~0.55)
# À réactualiser au besoin via monthly_signal.py chaque 1ᵉʳ du mois
R3_STATE_CURRENT = "BUY"

# Date cible what-if
FUTUR_DATE = pd.Timestamp("2026-05-31")
GENESIS = pd.Timestamp("2009-01-03")

# Inputs par défaut (B1, E1, H1) — modifiables dans gsheet
DEFAULT_DATE_ENTREE = "2024-04-30"
DEFAULT_MONTANT_EUR = 10000
DEFAULT_BTC_FUTUR = 70000


def generate_export_csv() -> Path:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))

    # Recalcule signaux et positions avec les paramètres figés
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

    # Référence 11 mois avant la date what-if (pour calcul return_11m)
    ref_date_for_r1 = FUTUR_DATE - pd.DateOffset(months=N_TSMOM)
    # Chercher la plus proche fin de mois disponible dans monthly
    ref_date_idx = monthly.index.searchsorted(ref_date_for_r1)
    if ref_date_idx >= len(monthly):
        ref_date_idx = len(monthly) - 1
    ref_date_used = monthly.index[ref_date_idx]
    btc_ref_r1 = float(monthly.loc[ref_date_used, "close_usd"])

    # fair_PL au 2026-05-31 = 10^(A + N * log10(days_since_genesis))
    days_futur = (FUTUR_DATE - GENESIS).days
    fair_pl_futur = 10 ** (a_const + N_EXPONENT_PL * np.log10(days_futur))

    out_csv = repo / "output" / "export_gsheet_backtest.csv"

    rows: list[list[str]] = []

    # Ligne 1 : inputs utilisateur (cellules modifiables B1, E1, H1)
    rows.append([
        "date_entrée", DEFAULT_DATE_ENTREE, "",
        "montant_€", str(DEFAULT_MONTANT_EUR), "",
        "btc_futur_usd", str(DEFAULT_BTC_FUTUR),
    ])
    # Ligne 2 : description
    rows.append([
        "Modifie B1 (date), E1 (montant), H1 (prix BTC futur) pour explorer",
        "", "", "", "", "", "", "",
    ])
    # Ligne 3 : headers
    rows.append([
        "date", "btc_close", "position",
        "equity_strat_base100", "equity_hodl_base100",
        "equity_perso_strat", "equity_perso_hodl",
    ])

    first_data_row = 4  # numéro de ligne gsheet (1-indexé) de la 1ʳᵉ ligne de data
    n = len(monthly)

    for i, (dt, row) in enumerate(monthly.iterrows()):
        r = first_data_row + i
        btc = float(row["close_usd"])
        pos = float(position.loc[dt])

        if i == 0:
            # 1ʳᵉ ligne : base 100, equity perso démarre seulement si date entrée <= date courante
            eq_strat = "100"
            eq_hodl = "100"
            eq_perso_strat = f'=IF(A{r}<$B$1,0,IF(A{r}=$B$1,$E$1,0))'
            eq_perso_hodl = f'=IF(A{r}<$B$1,0,IF(A{r}=$B$1,$E$1,0))'
        else:
            # Lignes suivantes : composition
            eq_strat = f'=D{r-1}*(1+C{r-1}*(B{r}/B{r-1}-1))'
            eq_hodl = f'=100*B{r}/B${first_data_row}'
            eq_perso_strat = (
                f'=IF(A{r}<$B$1,0,'
                f'IF(A{r-1}<$B$1,$E$1,'
                f'F{r-1}*(1+C{r-1}*(B{r}/B{r-1}-1))))'
            )
            eq_perso_hodl = (
                f'=IF(A{r}<$B$1,0,'
                f'IF(A{r-1}<$B$1,$E$1,'
                f'G{r-1}*B{r}/B{r-1}))'
            )

        rows.append([
            dt.date().isoformat(),
            f"{btc:.2f}",
            f"{pos:.1f}",
            eq_strat,
            eq_hodl,
            eq_perso_strat,
            eq_perso_hodl,
        ])

    last_data_row = first_data_row + n - 1

    # Ligne vide séparateur
    rows.append([""] * 8)
    # Ligne titre what-if
    rows.append([
        f"=== WHAT-IF projection 2026-05-31 "
        f"(hystérèse R3 démarrée état {R3_STATE_CURRENT}) ===",
        "", "", "", "", "", "", "",
    ])
    # Ligne headers what-if
    rows.append([
        "date", "btc_close_hypothetique",
        "return_11m", "signal_r1",
        "ratio_prix_fair_pl", "signal_r3",
        "position_cible_pct", "",
    ])

    whatif_row = last_data_row + 4  # ligne vide + titre + header + 1
    # Formules what-if
    # return_11m = $H$1 / btc_ref - 1 (ref = close fin mois 11 mois avant futur_date)
    return_11m_formula = f'=$H$1/{btc_ref_r1:.2f}-1'
    # signal R1 : BUY si return > 0
    signal_r1_formula = f'=IF(C{whatif_row}>0,"BUY","CASH")'
    # ratio = $H$1 / fair_pl (fair_pl hardcodé calculé à l'export)
    ratio_formula = f'=$H$1/{fair_pl_futur:.2f}'
    # signal R3 hystérésis depuis état BUY : reste BUY si ratio < 2.5, sinon CASH
    if R3_STATE_CURRENT == "BUY":
        signal_r3_formula = (
            f'=IF(E{whatif_row}>{K_HIGH_PL},"CASH","BUY")'
        )
    else:  # état CASH précédent : ne revient en BUY que si ratio < k_low
        signal_r3_formula = (
            f'=IF(E{whatif_row}<{K_LOW_PL},"BUY","CASH")'
        )
    # position cascade strict_r1_def
    position_formula = (
        f'=IF(F{whatif_row}="CASH",0,'
        f'IF(D{whatif_row}="BUY",100,50))'
    )

    rows.append([
        "2026-05-31",
        "=$H$1",
        return_11m_formula,
        signal_r1_formula,
        ratio_formula,
        signal_r3_formula,
        position_formula,
        "",
    ])

    # Ligne méta : rappel des valeurs de référence
    rows.append([
        f"(référence : prix {ref_date_used.date()} = ${btc_ref_r1:,.0f}, "
        f"fair_PL 2026-05-31 ≈ ${fair_pl_futur:,.0f}, "
        f"A = {a_const:.4f})",
        "", "", "", "", "", "", "",
    ])

    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        for line in rows:
            writer.writerow(line)

    return out_csv


def main() -> None:
    out = generate_export_csv()
    print(f"Export gsheet généré : {out}")
    # Affiche les 5 premières lignes et les 4 dernières pour inspection
    with open(out) as f:
        content = f.readlines()
    print()
    print("=== 5 premières lignes ===")
    for line in content[:5]:
        print(line.rstrip())
    print()
    print("=== 4 dernières lignes ===")
    for line in content[-4:]:
        print(line.rstrip())


if __name__ == "__main__":
    main()
