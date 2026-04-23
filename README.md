# ChillBTC — BTC posé. Un coup d'œil par mois.

**ChillBTC** est une stratégie d'investissement Bitcoin **mécanique**,
**set-and-forget**, conçue pour limiter les baisses violentes en bear
market sans rater la hausse à long terme. L'outil te donne
**1 instruction simple par mois** : **100 %, 50 % ou 0 % de ton
allocation BTC**. Tu appliques le dosage sur Binance, tu fermes, tu
retournes à ta vie.

> © 2026 ChillBTC — Contact : chillbtc@zaclys.net
> Usage non-commercial uniquement ([CC BY-NC-SA 4.0](LICENSE)).
> Pas un conseil en investissement. Past performance does not guarantee future results.

---

## 🚀 Installation (3 min, zéro prérequis)

Choisis ton OS ci-dessous. Dans chaque cas, tu télécharges un dossier, tu
double-cliques un fichier, et au premier lancement le script installe
automatiquement tout ce qu'il faut (Python, librairies). Pas besoin d'avoir
quoi que ce soit d'installé au préalable.

### 🍎 macOS

1. **Télécharge** le dossier [`dist/chillbtc/macos/`](dist/chillbtc/macos/)
   (+ le dossier [`code/`](dist/chillbtc/code/) et le fichier
   [`LICENSE`](dist/chillbtc/LICENSE), à placer dans un parent commun).
   *Ou récupère le zip complet auprès de l'auteur.*
2. **Double-clique** `chill.command`. Au premier lancement, clic droit →
   **Ouvrir** pour passer Gatekeeper une seule fois.
3. **Attends** 30 s à 2 min (installation automatique de Python et des
   librairies). Le signal du mois s'affiche.

Détail étape par étape : [`dist/chillbtc/macos/README.md`](dist/chillbtc/macos/README.md).

### 🪟 Windows

1. **Télécharge** le dossier [`dist/chillbtc/windows/`](dist/chillbtc/windows/)
   (+ [`code/`](dist/chillbtc/code/) et [`LICENSE`](dist/chillbtc/LICENSE)).
2. **Double-clique** `chill.bat`. Au premier lancement, Windows SmartScreen
   demande confirmation → **Informations complémentaires** → **Exécuter
   quand même**.
3. **Attends** 30 s à 2 min. Le signal du mois s'affiche.

Détail : [`dist/chillbtc/windows/README.md`](dist/chillbtc/windows/README.md).

### 🐧 Linux

1. **Télécharge** le dossier [`dist/chillbtc/linux/`](dist/chillbtc/linux/)
   (+ [`code/`](dist/chillbtc/code/) et [`LICENSE`](dist/chillbtc/LICENSE)).
2. Dans un terminal : `chmod +x chill.sh && ./chill.sh`.
3. **Attends** 30 s à 2 min. Le signal du mois s'affiche.

Détail : [`dist/chillbtc/linux/README.md`](dist/chillbtc/linux/README.md).

---

## 🎯 Est-ce que cette méthode est pour toi ?

### ✅ Cette méthode est pour toi SI…

- Tu crois au **BTC long-terme** (plusieurs cycles de 4 ans).
- Tu veux **quelques minutes par mois**, pas quelques minutes par jour.
- Tu veux une **règle mécanique**, pas "je ressens que…" ou "mon pote a dit".
- Tu es **résident fiscal français** (la règle `CASH = USDC` annule la friction
  fiscale sur les switches mensuels — art. 150 VH bis CGI).
- Tu utilises **Binance** (adaptable à d'autres plateformes mais le backtest
  suppose Binance).
- Tu acceptes qu'un **drawdown jusqu'à −50 %** reste possible. Le backtest
  2016-2026 montre −40 % max mais le futur n'est pas garanti.
- Tu veux **limiter la casse en bear** (la perte de −75 % de 2022 serait passée
  à −9 %) quitte à **perdre un peu en bull** (la strat sous-performe HODL en
  bull market strong, c'est mécanique et normal).

### ❌ Cette méthode n'est PAS pour toi SI…

- Tu **trades activement** (day trading, swing trading intra-mois).
- Tu veux **battre le marché sur 3-6 mois** (la strat est conçue sur le cycle,
  pas sur le trimestre).
- Tu **ne tolères pas** un drawdown > −30 %.
- Tu veux un **stop-loss intra-mois** (la strat décide une seule fois par mois,
  point).
- Tu veux **timer les tops** ou **sauter sur les breakouts** (la strat est en
  retard sur les tournants, c'est la contrepartie de sa robustesse).
- Ton capital BTC est **inférieur à ~500 €** (les frais fixes de transaction
  dévorent le gain ; attends d'avoir un capital plus significatif).
- Tu comptes utiliser **autre chose qu'USDC** comme cash (USDT, BUSD, etc.) —
  la stratégie est calibrée pour USDC, émetteur régulé, avec un risque de
  dépegging documenté comme acceptable.

---

## 📖 Comment ça marche, en 1 minute

Chaque 1ᵉʳ du mois, l'outil lit **2 signaux** sur le prix BTC :

- **R1 — la tendance** (Time-Series Momentum, Moskowitz/Pedersen 2012) :
  BTC a-t-il monté sur les **11 derniers mois** ? → **BUY** (oui) ou **CASH** (non).
- **R3 — la valorisation** (Power Law, Santostasi) : BTC est-il **cher ou
  pas cher** par rapport à sa droite de puissance historique ? → **BUY**
  (pas cher) ou **CASH** (trop cher).

Les 2 signaux combinés → **1 dosage unique** (règle 100/50/0) :

```
R1 BUY  + R3 BUY   →  100 %  BTC                           (climat haussier)
R1 BUY  + R3 CASH  →   50 %  BTC  +  50 %  USDC            (BTC cher)
R1 CASH + R3 BUY   →   50 %  BTC  +  50 %  USDC            (tendance floue)
R1 CASH + R3 CASH  →    0 %  BTC  + 100 %  USDC            (bear confirmé)
```

C'est tout. Pas d'autre paramètre, pas de condition cachée, pas de filtre
discrétionnaire.

---

## 📊 Performance historique (backtest 10 ans, 2016 → 2026)

Arrêté au **22/04/2026** (dernière clôture mensuelle = 2026-03-31).

```
  année    perf strat    perf HODL      delta   DD max strat    DD max HODL
  ------------------------------------------------------------------------
  2016 *       +37.0%       +81.2%     -44.2%          -7.3%         -14.4%
  2017        +778.1%     +1339.4%    -561.3%          -8.6%         -10.1%
  2018          +0.0%       -73.4%     +73.4%          +0.0%         -64.2%
  2019         +37.4%       +94.1%     -56.7%         -33.4%         -33.4%
  2020        +269.3%      +304.5%     -35.2%         -31.2%         -31.2%
  2021         +55.3%       +59.4%      -4.1%          -0.5%         -40.4%
  2022          -9.0%       -64.2%     +55.2%          -9.8%         -63.7%
  2023        +102.8%      +155.7%     -52.8%         -14.9%         -14.9%
  2024        +121.0%      +121.0%      +0.0%         -17.3%         -17.3%
  2025          -5.0%        -6.3%      +1.3%         -23.4%         -24.4%
  2026 *       -11.3%       -22.0%     +10.7%          -7.4%         -14.8%
  ------------------------------------------------------------------------
  Perf annualisée 3 ans       : strat +41.3%   |   HODL +33.8%
  Perf annualisée 5 ans       : strat +28.0%   |   HODL +3.0%
  Perf annualisée depuis 2016 : strat +80.1%   |   HODL +63.8%
  DD max depuis 2016          : strat -40.3%   |   HODL -75.4%
```

> `*` **2016 et 2026 sont des années partielles**. 2016 = 8 mois (mai→déc,
> warm-up des règles), 2026 = 3 mois (janv→mars, année en cours). Pas
> directement comparables aux années pleines.

**Lecture rapide** :

- **CAGR strat +80 %/an vs HODL +64 %/an** sur 10 ans.
- **Drawdown max strat −40 %** vs HODL **−75 %** (c'est ça, le vrai gain).
- La strat **gagne largement en bear** (2018, 2022) et **sous-performe en
  bull** (2017, 2019, 2020, 2023) — c'est mécanique, pas un bug.

---

## 🛠 La méthode pas-à-pas, 100 % opérationnelle

Chaque 1ᵉʳ du mois (tolérance jusqu'au 3 si tu es pris) :

1. **Lancer l'outil** (30 s)
   - macOS : double-clique `chill.command` dans le dossier `macos/`.
   - Windows : double-clique `chill.bat` dans le dossier `windows/`.
   - Linux : `./chill.sh` dans le dossier `linux/`.
   - Au 1ᵉʳ lancement seulement, attendre 30 s à 2 min d'install auto.

2. **Lire le dosage cible** (10 s)
   - Le signal du mois s'affiche sous forme :
     `🟢 100 % BTC`, `🟡 50 % BTC + 50 % USDC`, ou `🔴 0 % BTC (100 % USDC)`.
   - Un récap 10 derniers mois + récap annuel s'affichent à la suite.

3. **Comparer avec ta position actuelle sur Binance** (10 s)
   - Ouvre l'app/site Binance → onglet "Portfolio" ou "Wallet overview".
   - Regarde la proportion BTC / USDC dans ton solde de trading.

4. **Si le dosage cible diffère de ta position** (2 min, ~1 fois par an
   en moyenne)
   - Passe l'ordre à marché sur la paire **BTC/USDC** :
     - Vers 100 % BTC : achète le complément en BTC.
     - Vers 50 % : ajuste pour être moitié-moitié (vendre BTC ou acheter
       BTC selon ton état actuel).
     - Vers 0 % : vends tout le BTC en USDC.
   - Un simple ordre à marché suffit (pas besoin de limit order, l'économie
     sur le spread est négligeable devant la volatilité de BTC au mois).

5. **Fermer la fenêtre** (10 s)
   - Le journal interne `live_journal.csv` est mis à jour automatiquement.
   - Pas de news à lire, pas de Twitter à watcher, pas de dashboard à
     ouvrir à 23 h. Reviens dans 30 jours.

**Cas particuliers** :

- Le 1ᵉʳ du mois tombe un weekend ou férié → fais-le quand même, Binance
  est ouvert 24/7.
- Tu es en voyage sans connexion → fais-le à ton retour, tolérance J+2.
- Le site `cryptodatadownload.com` est down → réessaie le lendemain.

---

## 🤔 Pour aller plus loin

### Pour les développeurs (repo cloné)

📘 **Install détaillée, commandes, structure du repo, règles de contribution : [`CONTRIBUTING.md`](CONTRIBUTING.md).**

Quick start depuis la racine du repo cloné :

```
./chill
```

Affiche à la suite, sans interaction :

1. **Signal du mois** — refresh daily Bitstamp, calcule R1 + R3, affiche la
   position cible, append la ligne au journal live.
2. **Récap des 10 derniers mois** — perf strat vs HODL mois par mois.
3. **Récap annuel** — perf année par année + perf annualisée 3/5/10 ans
   + DD max global.

Si le journal `engine/output/live_journal.csv` est absent au 1ᵉʳ lancement,
il est **bootstrappé automatiquement** depuis `engine/output/cascade_position.csv`.

---

## 🧭 Architecture conceptuelle

**N-versioning par produit cartésien** : trois familles de règles × trois
familles d'optimisation = **9 stratégies** calibrées indépendamment. La
stratégie retenue (Mode C cascade) combine R1 (défensif) et R3 (agressif)
pour sortir du marché via OR logique dès que l'un des deux signaux
dit CASH.

## 🛡 Garde-fous (résumé)

- Règles à **1 ou 2 paramètres maximum**. Pas de filtres ad hoc.
- **Plateau de stabilité exigé** : si seul le pic exact fonctionne = overfit.
- **Walk-forward + leave-one-cycle-out** comme filets OOS.
- **Décision figée à l'avance** : aucun bricolage entre revues annuelles.
- **Journal mensuel obligatoire** : sans journal, pas d'apprentissage.
