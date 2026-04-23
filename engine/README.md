# ChillBTC — engine Python

Package Python de la stratégie ChillBTC : règles de signal, optimisations,
backtest en carré latin 9 cellules, cascade 2-signaux, CLI unifié.

## Prérequis

- **Python 3.13** (géré automatiquement par `uv`).
- **[uv](https://docs.astral.sh/uv/)** — gestionnaire de dépendances.

## Installation

```bash
git clone https://github.com/investchill/chillbtc.git
cd chillbtc/engine
uv sync       # installe Python 3.13 + pandas + numpy + matplotlib + requests
```

## Commandes principales

```bash
uv run chillbtc              # CLI unifié : signal mensuel + récap 10 mois + récap annuel
uv run chillbtc-monthly      # Signal mensuel seul (--dry-run pour tester)
uv run chillbtc-backtest     # Backtest complet des 9 cellules du carré latin
uv run chillbtc-phase-b      # Sanity check règles R1/R2/R3 + métriques
uv run chillbtc-phase-c      # Sanity check optimisations O1/O2/O3
uv run chillbtc-fetch        # Refresh cache daily Bitstamp (CryptoDataDownload)
```

Liste complète dans `pyproject.toml` (section `[project.scripts]`).

## Architecture

- `rules.py` — signaux R1 (TSMOM), R2 (Mayer Multiple), R3 (Power Law)
- `optims.py` — optimisations O1 (plateau), O2 (walk-forward), O3 (leave-one-cycle-out)
- `backtest.py` — runner des 9 cellules R × O (carré latin CAGR / DD / Sharpe)
- `cascade.py` — cascade 2 signaux (mode retenu en production, dosage 100/50/0)
- `monthly_signal.py` — signal live mensuel
- `cli.py` — CLI unifié (entry point `chillbtc`)
- `data.py` / `data_weekly.py` — fetch cache OHLC daily/weekly Bitstamp
- `metrics.py` — CAGR, max DD, Sharpe, equity curves from signals

## Sorties

Les artefacts générés tombent dans `engine/output/` :

- CSV : `phase_c_results.csv`, `cascade_position.csv`, `mode_comparison.csv`, `live_journal.csv`
- JSON : `phase_c_raw.json`, `cascade_summary.json`
- PNG : `figures/*.png` (courbes d'équité, drawdowns, heatmaps)

## License

CC BY-NC-SA 4.0 — voir [`../LICENSE`](../LICENSE).
