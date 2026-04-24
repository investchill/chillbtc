# ChillBTC — le BTC posé. Un coup d'œil par mois.

[![Tests](https://github.com/investchill/chillbtc/actions/workflows/test.yml/badge.svg)](https://github.com/investchill/chillbtc/actions/workflows/test.yml)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![Strategy frozen](https://img.shields.io/badge/strategy-frozen%20until%202027--01-informational.svg)](CHANGELOG.md)

**ChillBTC** est une stratégie d'investissement Bitcoin **à règles
fixes**, que tu **appliques une fois par mois puis oublies**. Elle est
conçue pour limiter les grosses baisses en marché baissier sans rater
la hausse sur le long terme. L'outil te donne **1 instruction simple
par mois** : **100 %, 50 % ou 0 % de ton allocation BTC**. Tu appliques
le dosage sur Binance, tu fermes, tu retournes à ta vie.

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
des 2 signaux (tendance + valorisation) et le contexte du mois.

---

### [📈 Historique annuel →](docs/historique-annuel.md)

Performance année par année depuis 2015 — stratégie ChillBTC vs **HODL**
(acheter et garder, stratégie passive de référence) en parallèle.

---

### [📅 Historique mensuel →](docs/historique-mensuel.md)

Toutes les positions mois par mois depuis 2015-10, avec perf cumulée
stratégie vs HODL.

---

## 🎯 Est-ce que cette méthode est pour toi ?

### ✅ Cette méthode est pour toi SI…

- Tu crois au **BTC long-terme** (plusieurs cycles de 4 ans).
- Tu veux **quelques minutes par mois**, pas quelques minutes par jour.
- Tu veux une **règle fixe**, pas "je ressens que…" ou "mon pote a dit".
- Tu es **résident fiscal français** (la règle `CASH = USDC` annule la friction
  fiscale sur les switches mensuels — art. 150 VH bis CGI).
- Tu utilises **Binance** (adaptable à d'autres plateformes mais la
  simulation historique suppose Binance).
- Tu acceptes qu'une **baisse temporaire jusqu'à −50 %** de ton portefeuille
  reste possible. La simulation 2016-2026 montre −40 % max (baisse temporaire
  sur papier), mais le futur n'est pas garanti.
- Tu veux **limiter la casse en marché baissier** (la perte de −75 % de
  2022 serait passée à −9 %) quitte à **perdre un peu en marché haussier**
  (ChillBTC sous-performe HODL quand la hausse est forte, c'est normal
  par construction).

### ❌ Cette méthode n'est PAS pour toi SI…

- Tu **trades activement** (day trading, swing trading intra-mois).
- Tu veux **battre le marché sur 3-6 mois** (ChillBTC est conçu sur le cycle,
  pas sur le trimestre).
- Tu **ne tolères pas** une baisse temporaire de ton portefeuille supérieure à −30 %.
- Tu veux un **stop-loss intra-mois** (ChillBTC décide une seule fois par mois,
  point).
- Tu veux **timer les sommets** ou **sauter sur les cassures** (ChillBTC est en
  retard sur les tournants, c'est la contrepartie de sa robustesse).
- Ton capital BTC est **inférieur à ~500 €** (les frais fixes de transaction
  dévorent le gain ; attends d'avoir un capital plus significatif).
- Tu comptes utiliser **autre chose qu'USDC** comme cash (USDT, BUSD, etc.) —
  la stratégie est calibrée pour USDC, émetteur régulé, avec un risque de
  dépegging documenté comme acceptable.

---

## 📖 Comment ça marche, en 1 minute

Chaque 1ᵉʳ du mois, l'outil lit **2 signaux** sur le prix BTC :

- **Tendance** (Time-Series Momentum, Moskowitz/Pedersen 2012) :
  BTC a-t-il monté sur les **11 derniers mois** ? → **ACHAT** (oui) ou **CASH** (non).
- **Valorisation** (Power Law, Santostasi) : BTC est-il **cher ou
  pas cher** par rapport à sa droite de puissance historique ? → **ACHAT**
  (pas cher) ou **CASH** (trop cher).

Les 2 signaux combinés → **1 dosage unique** (règle 100/50/0) :

```
Tendance ACHAT + Valorisation ACHAT  →  100 %  BTC                   (climat haussier)
Tendance ACHAT + Valorisation CASH   →    0 %  BTC  + 100 %  USDC    (valorisation CASH prime)
Tendance CASH  + Valorisation ACHAT  →   50 %  BTC  +  50 %  USDC    (signaux opposés)
Tendance CASH  + Valorisation CASH   →    0 %  BTC  + 100 %  USDC    (baisse confirmée)
```

C'est tout. Pas d'autre paramètre, pas de condition cachée, pas de filtre
discrétionnaire.

📖 **Pour aller plus loin sur la méthodologie** (formules exactes, fondements
académiques avec DOI, illustrations historiques annotées sur 10 ans) : voir
**[docs/methodologie.md](docs/methodologie.md)**.

---

## 📊 Performance historique (simulation depuis 2015-10)

Mis à jour automatiquement chaque 1ᵉʳ du mois — **table complète année
par année et mois par mois sur les pages dédiées** :

- **[📈 Historique annuel →](docs/historique-annuel.md)** — perf annuelle
  stratégie vs HODL, 2015-10 → aujourd'hui.
- **[📅 Historique mensuel →](docs/historique-mensuel.md)** — toutes les
  positions et la perf cumulée mois par mois.

**Lecture rapide** (chiffres globaux sur ~10 ans) :

- **Performance annualisée ChillBTC ≈ +90 %/an** vs **HODL ≈ +75 %/an**.
- **Pire baisse temporaire ChillBTC −40 %** (sur papier, perte
  non-réalisée) vs **HODL −75 %** — c'est ça, le vrai gain.
- ChillBTC **gagne largement en marché baissier** (2018, 2022) et
  **sous-performe en marché haussier** (2017, 2019, 2020, 2023) — c'est
  normal par construction, pas un bug.

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

Le moteur Python (`engine/`) recalcule l'historique cascade (tendance + valorisation) et
régénère les 3 pages du `docs/`. Le workflow GitHub Actions
[`.github/workflows/monthly-update.yml`](.github/workflows/monthly-update.yml)
l'exécute le 1ᵉʳ du mois à 06:00 UTC.

---

## 🧭 Comment la méthode a été construite

Trois règles candidates (tendance, Mayer, valorisation) croisées avec
trois façons indépendantes de les calibrer, soit **neuf combinaisons
testées** séparément. Celle retenue combine **la tendance** (qui sort
tôt en cas de retournement) et **la valorisation** (qui sort quand le
prix est trop cher) : la position est réduite ou coupée dès que l'un
des deux signaux passe CASH.

📖 Détails complets (formules, références académiques avec DOI,
illustrations historiques) dans
**[docs/methodologie.md](docs/methodologie.md)**.

## 🛡 Garde-fous anti-sur-optimisation

- Chaque règle n'a au plus **1 ou 2 boutons à tourner**. Aucune
  exception.
- Un paramètre n'est retenu que s'il fait partie d'une **plage large
  qui marche**, jamais un pic isolé du grid search.
- Deux protocoles de validation indépendants, qui cachent une partie de
  l'historique à la calibration pour vérifier que le résultat n'est pas
  dû à la chance.
- **Décision figée à l'avance** : aucun ajustement entre deux revues
  annuelles.
- **Journal mensuel obligatoire** : sans trace, pas d'apprentissage
  possible.
