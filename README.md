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

## 📊 Suivi en direct

Trois pages **mises à jour automatiquement** chaque 1ᵉʳ du mois à 06:00 UTC
par GitHub Actions. Aucune installation requise.

---

### [📊 Signal du mois en cours →](docs/signaux.md)

L'allocation BTC à appliquer ce mois-ci (100 / 50 / 0 %), avec la valeur
des 2 signaux R1 + R3 et le contexte du mois.

---

### [📈 Historique annuel →](docs/historique-annuel.md)

Performance année par année depuis 2015 — stratégie ChillBTC vs HODL en
parallèle.

---

### [📅 Historique mensuel →](docs/historique-mensuel.md)

Toutes les positions mois par mois depuis 2015-10, avec perf cumulée
stratégie vs HODL.

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

## 📊 Performance historique (backtest depuis 2015-10)

Mis à jour automatiquement chaque 1ᵉʳ du mois — **table complète année
par année et mois par mois sur les pages dédiées** :

- **[📈 Historique annuel →](docs/historique-annuel.md)** — perf annuelle
  stratégie vs HODL, 2015-10 → aujourd'hui.
- **[📅 Historique mensuel →](docs/historique-mensuel.md)** — toutes les
  positions et la perf cumulée mois par mois.

**Lecture rapide** (KPIs globaux, derniers chiffres consolidés) :

- **CAGR stratégie ≈ +90 %/an** vs **HODL ≈ +75 %/an** sur ~10 ans.
- **Drawdown max stratégie −40 %** vs **HODL −75 %** (c'est ça, le vrai gain).
- La strat **gagne largement en bear** (2018, 2022) et **sous-performe en
  bull** (2017, 2019, 2020, 2023) — c'est mécanique, pas un bug.

---

## 🛠 La méthode pas-à-pas, 100 % opérationnelle

Chaque 1ᵉʳ du mois (tolérance jusqu'au 3 si tu es pris) :

1. **Ouvre la page [Signal du mois en cours](docs/signaux.md)** (10 s)
   - Le dosage cible s'affiche : `🟢 100 % BTC`, `🟡 50 % BTC + 50 % USDC`,
     ou `🔴 0 % BTC (100 % USDC)`.
   - Les 6 derniers mois sont rappelés en bas de page pour le contexte.

2. **Compare avec ta position actuelle sur Binance** (10 s)
   - Ouvre l'app/site Binance → onglet "Portfolio" ou "Wallet overview".
   - Regarde la proportion BTC / USDC dans ton solde de trading.

3. **Si le dosage cible diffère de ta position** (2 min, ~1 fois par an
   en moyenne)
   - Passe l'ordre à marché sur la paire **BTC/USDC** :
     - Vers 100 % BTC : achète le complément en BTC.
     - Vers 50 % : ajuste pour être moitié-moitié (vendre BTC ou acheter
       BTC selon ton état actuel).
     - Vers 0 % : vends tout le BTC en USDC.
   - Un simple ordre à marché suffit (pas besoin de limit order, l'économie
     sur le spread est négligeable devant la volatilité de BTC au mois).

4. **Ferme l'onglet** (5 s)
   - Pas de news à lire, pas de Twitter à watcher, pas de dashboard à
     ouvrir à 23 h. Reviens dans 30 jours.

**Cas particuliers** :

- Le 1ᵉʳ du mois tombe un weekend ou férié → fais-le quand même, Binance
  est ouvert 24/7.
- Tu es en voyage sans connexion → fais-le à ton retour, tolérance J+2.
- La page n'est pas mise à jour le matin du 1ᵉʳ → vérifie en fin de journée
  (le bot tourne le 1ᵉʳ à 06:00 UTC, parfois retardé).

---

## 🤔 Pour aller plus loin

### Pour les développeurs (repo cloné)

📘 **Install détaillée, commandes, structure du repo, règles de contribution :
[`CONTRIBUTING.md`](CONTRIBUTING.md).**

Le moteur Python (`engine/`) recalcule l'historique cascade R1 + R3 et
régénère les 3 pages du `docs/`. Le workflow GitHub Actions
[`.github/workflows/monthly-update.yml`](.github/workflows/monthly-update.yml)
l'exécute le 1ᵉʳ du mois à 06:00 UTC.

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
