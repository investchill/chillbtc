# Contribuer à ChillBTC

Ce document s'adresse aux développeuses et développeurs qui veulent cloner
le dépôt, faire tourner le backtest ou le signal mensuel, comprendre
l'architecture, ou proposer une contribution.

Pour l'utilisation end-user (« donne-moi juste le signal du mois »), tout
est dans le [`README.md`](README.md).

---

## 1. Installation dev (5 min)

### Prérequis

- **Python 3.13** (managé automatiquement par uv, pas besoin de l'installer à la main).
- **[uv](https://docs.astral.sh/uv/)** — le gestionnaire de dépendances Python utilisé par le projet.
  Installation :
  - macOS / Linux : `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows : `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### Setup

```bash
git clone https://github.com/investchill/chillbtc.git
cd chillbtc/engine
uv sync       # installe Python 3.13 + pandas + numpy + matplotlib + requests
```

### Vérifier que tout tourne

```bash
cd engine && uv run chillbtc-monthly --dry-run
```

Si la commande affiche un signal mensuel (R1 + R3 + dosage), c'est bon.

---

## 2. Commandes disponibles

Tous les entry points sont exposés via `uv run` depuis `engine/`.

```
uv run chillbtc-monthly      — signal mensuel (flag --dry-run pour test sans append journal)
uv run chillbtc-pages        — génère docs/{signaux,historique-annuel,historique-mensuel}.md
uv run chillbtc-backtest     — full backtest 9 cellules (phase C), écrit engine/output/
uv run chillbtc-phase-b      — sanity check règles R1/R2/R3 + métriques (CAGR/DD/Sharpe)
uv run chillbtc-phase-c      — sanity check optimisations O1/O2/O3
uv run chillbtc-fetch        — refresh cache daily Bitstamp (CryptoDataDownload)
uv run chillbtc-proto        — dashboard HODL prototype (non utilisé en live)
uv run chillbtc-methodology-figures  — régénère les 3 PNG de docs/methodologie.md
```

Le workflow GitHub Actions [`monthly-update.yml`](.github/workflows/monthly-update.yml)
appelle `chillbtc-monthly` puis `chillbtc-pages` chaque 1ᵉʳ du mois à
06:00 UTC.

---

## 3. Structure du repo

```
.
├── README.md                        — pitch + pointeurs vers les pages live
├── CONTRIBUTING.md                  — ce fichier
├── LICENSE                          — CC BY-NC-SA 4.0
├── docs/                            — landing + pages auto-générées (GitHub Pages)
│   ├── index.html                   — page d'accueil publique
│   ├── signaux.md                   — signal du mois courant (auto, 1ᵉʳ du mois)
│   ├── historique-annuel.md         — perf annuelle strat / HODL (auto)
│   ├── historique-mensuel.md        — toutes positions mensuelles (auto)
│   └── assets/                      — brand + styles CSS
├── engine/                          — projet Python (uv)
│   ├── pyproject.toml               — deps + entry points
│   ├── src/chillbtc/                — package Python
│   │   ├── rules.py                 — R1 TSMOM, R2 Mayer, R3 Power Law
│   │   ├── optims.py                — O1 plateau, O2 walk-forward, O3 LOCO
│   │   ├── backtest.py              — runner carré latin 9 cellules
│   │   ├── cascade.py               — cascade 2 signaux (mode C retenu)
│   │   ├── monthly_signal.py        — signal live mensuel
│   │   └── build_pages.py           — génération des 3 pages docs/*.md
│   ├── data/                        — cache OHLC daily/monthly/weekly Bitstamp
│   └── output/                      — artefacts backtest + live_journal.csv
└── .github/workflows/
    └── monthly-update.yml           — cron 06:00 UTC du 1ᵉʳ du mois
```

---

## 4. Flux de travail typiques

### Lancer le signal du mois (dev)

```bash
cd engine
uv run chillbtc-monthly                # refresh Bitstamp + signal + append journal
uv run chillbtc-monthly --dry-run      # pareil sans append
uv run chillbtc-pages                  # régénère les 3 docs/*.md
```

### Rejouer le backtest complet

```bash
cd engine && uv run chillbtc-backtest
```

Les artefacts tombent dans `engine/output/` :
`phase_c_results.csv`, `phase_c_raw.json`, `cascade_position.csv`,
`cascade_summary.json`, `mode_comparison.csv`, `figures/*.png`.

### Régénérer les figures

```bash
cd engine && uv run python -m chillbtc.report
```

### Explorer les 3 conventions de cascade

```bash
cd engine && uv run python -m chillbtc.cascade
```

Génère `cascade_position{,_symmetric,_strict_r3_def}.csv` +
`cascade_summary{...}.json` — la convention `strict_r1_def` est celle retenue.

### Lancer les tests

```bash
cd engine
uv sync --group dev              # installe pytest + pytest-cov
uv run --group dev pytest        # lance toute la suite (< 2 s)
uv run --group dev pytest -v     # avec détail test par test
```

La suite couvre les primitives R1 / R3, la cascade, les métriques
(CAGR / DD / Sharpe) et les helpers de présentation du signal mensuel.
Pas de réseau : tout tourne sur `engine/data/btc_monthly.csv` déjà
commité + des séries synthétiques.

---

## 5. CI — workflows

### 5.1 Tests (`test.yml`)

Déclenché sur chaque `push` ou `pull_request` vers `public` ou `main`,
ainsi qu'en manuel via `workflow_dispatch`. `uv sync --group dev` puis
`uv run --group dev pytest`. Doit être vert avant tout merge.

### 5.2 Mise à jour mensuelle (`monthly-update.yml`)

Un workflow dans `.github/workflows/monthly-update.yml`. Il :

1. Check out le repo (branche `public`).
2. Setup `uv` + Python 3.13.
3. `uv sync` depuis `engine/`.
4. `uv run chillbtc-monthly` — refresh cache daily Bitstamp, calcule
   le signal du mois clos, append au `engine/output/live_journal.csv`.
5. `uv run chillbtc-pages` — recalcule la cascade gelée, écrit
   `docs/{signaux,historique-annuel,historique-mensuel}.md`.
6. Commit & push automatique (`github-actions[bot]`) si diff non vide.

Déclencheurs :

- `schedule` cron `0 6 1 * *` (1ᵉʳ du mois à 06:00 UTC).
- `workflow_dispatch` manuel via l'onglet Actions.

---

## 6. Règles de contribution

### Scope architectural verrouillé

L'architecture **N-versioning 3+3 = 9 stratégies** est volontairement
contrainte pour limiter la surface d'overfit. Ne proposez pas :

- Une 4ᵉ règle (au-delà de R1 TSMOM, R2 Mayer, R3 Power Law) sans
  discussion préalable via issue.
- Une 4ᵉ famille d'optimisation (au-delà de O1 plateau, O2 walk-forward,
  O3 leave-one-cycle-out).
- Un moteur Bayesian / GA / SA en remplacement du grid search (overkill
  pour 1-2 paramètres × ~180 observations).

### Anti-overfit

- **1 ou 2 paramètres maximum** par règle. Une règle à 3+ paramètres
  sera refusée.
- **Plateau de stabilité exigé** : si seul le pic exact du grid search
  fonctionne, c'est de l'overfit, la règle est jetée.
- **Frais inclus** : tout backtest doit intégrer des frais, hypothèse
  conservatrice 0,5 % par switch (vs ~0,15-0,20 % réel Binance).

### Stratégie gelée

La stratégie est gelée depuis le **2026-05-01** jusqu'à la revue
annuelle suivante. Les PR qui touchent aux paramètres S2 / S8, à la
convention cascade `strict_r1_def`, ou au dosage 100/50/0 sont **gelées**
aussi.

Exceptions admises :

- Triggers META (faillite plateforme, dépegging stablecoin > 5 % > 7 j,
  changement réglementaire majeur).
- Bugs (comportement du code diffère de la doc).
- Améliorations qui ne changent pas les signaux produits
  (perf, lisibilité, tests, doc).

### Langue

- **Documentation utilisateur** (README, CONTRIBUTING) : français, tutoiement.
- **Code source** (identifiers, docstrings, commentaires) : anglais.
- **Messages de commit** : français ou anglais, préférence pour le
  style Conventional Commits (`feat:`, `fix:`, `chore:`, etc.).

### Process PR

1. Pour un changement non-trivial, ouvrir une **issue** d'abord pour
   discuter l'approche.
2. Fork → branche dédiée → PR vers `main`.
3. Le workflow `monthly-update.yml` doit pouvoir s'exécuter sans erreur
   (testable manuellement via `workflow_dispatch`).
4. Pas de force-push sur des branches partagées.

---

## 7. License

Le projet est publié sous **[CC BY-NC-SA 4.0](LICENSE)**
(Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International).

En ouvrant une PR, tu acceptes que ta contribution soit publiée sous
cette même licence. Attribution au projet **ChillBTC**, usage
non-commercial uniquement, partage à l'identique.

---

## 8. Contact

- **Issues GitHub** — préférence pour les discussions techniques.
- **Mail** — `chillbtc@zaclys.net` pour tout autre contact.

Pas un conseil en investissement. Les performances passées ne préjugent
pas des performances futures.
