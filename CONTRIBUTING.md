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
cd .. && ./chill              # wrapper racine, signal du mois + récaps
```

Si `./chill` renvoie un signal et les récaps 10 mois / annuel, c'est bon.

---

## 2. Commandes disponibles

Tous les entry points sont exposés via `uv run` depuis `engine/`.

```
uv run chillbtc              — signal mensuel + récap 10 mois + récap annuel (CLI unifié)
uv run chillbtc-monthly      — uniquement le signal mensuel (flag --dry-run pour test)
uv run chillbtc-backtest     — full backtest 9 cellules (phase C), écrit engine/output/
uv run chillbtc-phase-b      — sanity check règles R1/R2/R3 + métriques (CAGR/DD/Sharpe)
uv run chillbtc-phase-c      — sanity check optimisations O1/O2/O3
uv run chillbtc-fetch        — refresh cache daily Bitstamp (CryptoDataDownload)
uv run chillbtc-proto        — dashboard HODL prototype (non utilisé en live)
```

Depuis la racine du repo, le wrapper `./chill` est équivalent à
`cd engine && uv run chillbtc`.

Sur macOS, `./chill` déhide d'abord le `.venv` au cas où iCloud aurait
re-appliqué le flag `hidden` (cf. commentaire en tête du script).

---

## 3. Structure du repo

```
.
├── README.md                        — pitch + install end-user
├── CONTRIBUTING.md                  — ce fichier
├── LICENSE                          — CC BY-NC-SA 4.0
├── chill                            — wrapper racine (lance le CLI)
├── docs/                            — landing page (GitHub Pages)
│   ├── index.html                   — page d'accueil publique
│   └── assets/                      — brand + styles CSS
├── engine/                          — projet Python (uv)
│   ├── pyproject.toml               — deps + entry points
│   ├── src/chillbtc/                — package Python
│   │   ├── rules.py                 — R1 TSMOM, R2 Mayer, R3 Power Law
│   │   ├── optims.py                — O1 plateau, O2 walk-forward, O3 LOCO
│   │   ├── backtest.py              — runner carré latin 9 cellules
│   │   ├── cascade.py               — cascade 2 signaux (mode C retenu)
│   │   ├── cli.py                   — CLI unifié (entry point chillbtc)
│   │   └── monthly_signal.py        — signal live mensuel
│   ├── data/                        — cache OHLC daily/monthly/weekly Bitstamp
│   └── output/                      — artefacts backtest (CSV, JSON, PNG)
├── dist/chillbtc/                   — lanceurs cross-OS pour users non-dev
│   ├── linux/chill.sh               — lanceur Linux
│   ├── macos/chill.command          — lanceur macOS (double-clic)
│   ├── windows/chill.bat            — lanceur Windows (double-clic)
│   ├── LICENSE, VERSION
│   └── code/                        — stagé par CI depuis engine/ (non tracké)
└── .github/workflows/               — 3 smoke tests Linux/macOS/Windows
```

---

## 4. Flux de travail typiques

### Lancer le signal du mois (dev)

```bash
./chill                       # refresh Bitstamp + signal + récap + append journal
./chill --dry-run             # pareil sans append
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

---

## 5. CI — tests de fumée

3 workflows dans `.github/workflows/` :

- `test-chill-sh.yml` — smoke test Linux (ubuntu-latest)
- `test-chill-command.yml` — smoke test macOS (macos-latest)
- `test-chill-bat.yml` — smoke test Windows (windows-latest)

Chacun :

1. Check out le repo.
2. Stage `dist/chillbtc/code/` depuis `engine/` (pas de duplication git).
3. Lance le lanceur OS en scénario *first-time user* (PATH vidé, HOME neutre).
4. Vérifie que le journal est bootstrappé automatiquement.
5. Assert la présence des markers de sortie (« Signal BTC », « Récap
   des 10 », « Perf annualisée », « DD max depuis »).
6. Build un zip de distribution par OS et vérifie sa structure.

Déclencheurs :

- Push sur `dist/chillbtc/**`, `engine/**`, ou le workflow lui-même.
- `workflow_dispatch` manuel.

Voir les runs dans l'onglet Actions du repo GitHub.

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
3. Les 3 smoke tests CI doivent passer (Linux / macOS / Windows).
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
