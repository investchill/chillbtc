# ChillBTC — installation Linux

> **Version distribution : 2026-04-22 (git `ae15fb7`)**. En cas de bug,
> communique cette ligne à l'auteur pour identifier la version exacte.

Stratégie d'investissement BTC **set-and-forget**. BTC posé. Un coup d'œil par mois.
L'outil te dit chaque 1ᵉʳ du mois : **100 % BTC, 50 % BTC + 50 % USDC,
ou 0 % BTC (100 % USDC)**. Tu appliques le dosage sur ta plateforme
d'échange, tu fermes le terminal, tu retournes à ta vie.

> © 2026 ChillBTC — Usage non-commercial uniquement. Licence CC BY-NC-SA 4.0
> (Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International).
> Redistribution autorisée avec attribution + même licence + usage non-commercial.
> Pas un conseil en investissement.

---

## Prérequis

**Aucun package système à installer.** Le launcher s'occupe de tout au premier
lancement via `uv`.

Il te faut juste :

- Linux x86_64 ou ARM64 avec une libc récente (glibc ≥ 2.31 — couvre Ubuntu
  20.04+, Debian 11+, Fedora 32+, Arch, openSUSE Leap 15.3+).
- `curl` ou `wget` installés (présents par défaut sur toutes les distros).
- Une connexion internet au premier lancement (30 s à 2 min selon ta bande
  passante) et chaque 1ᵉʳ du mois (quelques secondes pour récupérer le prix BTC).
- ~150 Mo d'espace disque libre.

---

## Installation et premier lancement

### 1. Place le dossier où tu veux

Home, `/opt/`, peu importe. Ne renomme pas les sous-dossiers `code/`, `linux/`
(ni `macos/`, `windows/` s'ils sont présents). Le launcher repose sur cette
structure pour trouver le code Python.

### 2. Rends `chill.sh` exécutable

Depuis un terminal dans le dossier `linux/` :

```bash
chmod +x chill.sh
```

Ou clic droit → Propriétés → cocher "Autoriser l'exécution" (selon ton
gestionnaire de fichiers).

### 3. Lance le script

Depuis le terminal :

```bash
./chill.sh
```

Ou double-clique dans le gestionnaire de fichiers si celui-ci est configuré
pour lancer les `.sh` exécutables (sur GNOME : Files → Préférences →
"Run executable text files when they are opened" → **Ask** ou **Run**).

### 4. Attends l'installation automatique (30 s à 2 min)

Le script télécharge et installe dans l'ordre :

1. **uv** (gestionnaire Python, ~5 Mo)
2. **Python 3.13+** dans un cache local (15-30 s)
3. **Les dépendances** (pandas, numpy, matplotlib, requests, ~80 Mo)

Tu vois les barres de progression, ne ferme pas la fenêtre. Les lancements
suivants seront instantanés (< 2 s).

---

## Utilisation mensuelle

Chaque 1ᵉʳ du mois (tolérance J+2) :

1. `./chill.sh` dans le dossier `linux/`.
2. Le CLI affiche : signal du mois → récap 10 derniers mois → récap annuel.
3. Compare le dosage cible (100 % / 50 % / 0 %) avec ta position actuelle
   sur Binance.
4. Si différent, ajuste avec des ordres à marché :
   - 100 % → tout en BTC
   - 50 % → moitié BTC, moitié USDC
   - 0 % → tout en USDC
5. Ferme le terminal.

**Le dosage change ~1 fois par an** en moyenne sur le backtest 2016-2026.
Les autres mois tu ne fais rien.

---

## Performance historique (backtest 2016 → 2026)

La stratégie a été calibrée sur les données publiques Bitstamp via un
**backtest walk-forward** (pas de data snooping) et gelée le **2026-05-01**.
Les chiffres ci-dessous sont les résultats du backtest sur l'historique
complet, avec 0,5 % de frais par switch (hypothèse pessimiste).

```
  année    perf strat    perf HODL      delta   DD max strat    DD max HODL
  ------------------------------------------------------------------------
  2016         +37.0%       +81.2%     -44.2%          -7.3%         -14.4%
  2017        +778.1%     +1339.4%    -561.3%          -8.6%         -10.1%
  2018          +0.0%       -73.4%     +73.4%          +0.0%         -64.2%
  2019         +37.4%       +94.1%     -56.7%         -33.4%         -33.4%
  2020        +269.3%      +304.5%     -35.2%         -31.2%         -31.2%
  2021         +55.3%       +59.4%      -4.1%          -0.5%         -40.4%
  2022          -9.0%       -64.2%     +55.2%          -9.8%         -63.7%
  2023        +102.8%      +155.7%     -52.8%         -14.9%         -14.9%
  2024        +121.0%      +121.0%      +0.0%         -17.3%         -17.3%
  2025          -5.0%        -6.3%      +1.3%         -23.4%         -24.4%
  2026         -11.3%       -22.0%     +10.7%          -7.4%         -14.8%
  ------------------------------------------------------------------------
  Perf annualisée 3 ans       : strat +41.3%   |   HODL +33.8%
  Perf annualisée 5 ans       : strat +28.0%   |   HODL +3.0%
  Perf annualisée depuis 2016 : strat +80.1%   |   HODL +63.8%
  DD max depuis 2016          : strat -40.3%   |   HODL -75.4%
```

**Le compromis fondamental** : la stratégie lague souvent en bull (delta
négatif) mais protège en bear (delta très positif en 2018 et 2022). Sur le
long terme, la protection bear compense largement le lag bull, tant en CAGR
qu'en drawdown.

⚠ **Past performance does not guarantee future results.**

---

## Disclaimer

**Ceci n'est pas un conseil en investissement.** Stratégie calibrée pour
**résident fiscal France + Binance + USDC comme cash**. Si ton contexte
diffère, les hypothèses de frais et fiscalité changent.

---

## FAQ rapide (Linux)

**Le site de données est down, le script échoue.**
Réessaie le lendemain. Cache local dans `../code/data/btc_monthly.csv`.

**Reset complet.**
`rm -rf ../code/.venv ../code/output/live_journal.csv` puis relance.

**Désinstaller uv.**
`rm ~/.local/bin/uv ~/.local/bin/uvx && rm -rf ~/.cache/uv/`

**Mon terminal ne trouve pas `uv` après l'install.**
Ajoute `export PATH="$HOME/.local/bin:$PATH"` à ton `~/.bashrc` ou
`~/.zshrc`, puis `source` le fichier. Le launcher `chill.sh` le fait déjà
dans son propre scope, mais la config persistante doit être faite par toi
si tu veux utiliser uv directement dans d'autres contextes.
