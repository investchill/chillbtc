# Comparaison cadence — mensuel vs hebdo

**Side experiment** : stratégie frozen 2026-05-01 intacte. Objectif : répondre à la question *« passer en check hebdo dimanche soir vaut-il le coup vs le mensuel 1ᵉʳ du mois ? »*. Mode C cascade R1+R3 (`strict_r1_def`), paramètres figés : R1 TSMOM n=11 mois = 48 semaines, R3 Power Law k_low=0.6, k_high=2.5, N_exponent=5.8, constante A refit sur full série (même politique que la cascade mensuelle). Signaux évalués au close fin de mois (mensuel) ou au close du dimanche (hebdo). Friction proportionnelle au turnover (switch 1→0.5 coûte 0.5 × fee).

## Frais 0.2 % par switch

```
Métrique                Mensuel        Hebdo         Δ (hebdo − mensuel)
CAGR                      77.43 %      78.89 %    +1.46 pp
Max Drawdown             -40.32 %     -36.02 %    +4.30 pp
Sharpe annualisé          1.276        1.594      +0.318
Switches (total)           12           11        -1
Switches / an              1.21         1.05      -0.16
Turnover cumulé            7.00         7.00      +0.00
Equity finale (base 100) 28109.85     44390.49     ×1.58

Fenêtre mensuel  : 2016-05-31 → 2026-03-31 (119 mois)
Fenêtre hebdo    : 2015-11-01 → 2026-04-12 (546 semaines)
```

## Frais 0.5 % par switch

```
Métrique                Mensuel        Hebdo         Δ (hebdo − mensuel)
CAGR                      80.11 %      78.51 %    -1.60 pp
Max Drawdown             -40.32 %     -36.12 %    +4.20 pp
Sharpe annualisé          1.303        1.589      +0.286
Switches (total)           10           11        +1
Switches / an              1.01         1.05      +0.04
Turnover cumulé            6.00         7.00      +1.00
Equity finale (base 100) 32562.56     43418.88     ×1.33

Fenêtre mensuel  : 2016-05-31 → 2026-03-31 (119 mois)
Fenêtre hebdo    : 2015-11-01 → 2026-04-12 (546 semaines)
```

## Verdict

- **Frais 0.2 %** — ΔCAGR : +1.46 pp · gain DD : +4.30 pp (positif = hebdo protège mieux) · ΔSharpe : +0.318 · Δswitches/an : -0.16 → **OUI clair**
- **Frais 0.5 %** — ΔCAGR : -1.60 pp · gain DD : +4.20 pp (positif = hebdo protège mieux) · ΔSharpe : +0.286 · Δswitches/an : +0.04 → **OUI clair**

Seuils utilisés : *OUI clair* = gain DD ≥ 3 pp ET ΔSharpe ≥ +0.10. *Marginal* = gain DD ≥ 1 pp OU ΔSharpe ≥ +0.05. En dessous, *NON* : le hebdo ne justifie pas l'effort 4× par rapport au mensuel set-and-forget.