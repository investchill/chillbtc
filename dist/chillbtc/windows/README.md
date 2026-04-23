# ChillBTC — installation Windows

> **Version distribution : 2026-04-22 (git `ae15fb7`)**. En cas de bug,
> communique cette ligne à l'auteur pour identifier la version exacte.

Stratégie d'investissement BTC **set-and-forget**. BTC posé. Un coup d'œil par mois.
L'outil te dit chaque 1ᵉʳ du mois : **100 % BTC, 50 % BTC + 50 % USDC,
ou 0 % BTC (100 % USDC)**. Tu appliques le dosage sur ta plateforme
d'échange, tu fermes la fenêtre, tu retournes à ta vie.

> © 2026 ChillBTC — Usage non-commercial uniquement. Licence CC BY-NC-SA 4.0
> (Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International).
> Redistribution autorisée avec attribution + même licence + usage non-commercial.
> Pas un conseil en investissement.

---

## Prérequis

**Aucun.** Tu n'as pas besoin d'avoir Python, `uv`, ou quoi que ce soit
d'installé au préalable. Le launcher s'occupe de tout au premier lancement.

Il te faut juste :
- Windows 10 (64-bit) ou plus récent.
- Une connexion internet **au premier lancement** (30 s à 2 min selon ta
  bande passante) et **chaque 1ᵉʳ du mois** pour récupérer le prix BTC du
  mois qui vient de s'écouler (quelques secondes).
- ~150 Mo d'espace disque libre (Python + dépendances installés en local,
  dans le dossier `..\code\.venv\`).

---

## Installation et premier lancement

### Étape 1 — Télécharger le dossier

Tu as reçu le dossier `chillbtc\`. Place-le où tu veux (Bureau,
Documents, peu importe). Ne renomme pas les sous-dossiers `code\`,
`macos\`, `windows\`.

### Étape 2 — Lancer `chill.bat`

Ouvre le dossier `windows\` dans l'Explorateur Windows. Tu y vois :

- `README.md` (ce fichier)
- `chill.bat` ← **le launcher**

**Double-clique sur `chill.bat`.**

### Étape 3 — Passer SmartScreen (première fois uniquement)

Windows va probablement afficher un écran bleu :

> *Windows a protégé votre ordinateur. Windows Defender SmartScreen a
> empêché le démarrage d'une application non reconnue.*

C'est normal : le fichier vient d'une source hors Microsoft Store. Pour
l'autoriser :

1. Clique sur **Informations complémentaires**.
2. Clique sur le bouton **Exécuter quand même** qui apparaît.
3. Une fenêtre Invite de commandes s'ouvre avec le script qui démarre.

Tu n'auras à passer ce SmartScreen **qu'une seule fois**. Les lancements
suivants, un double-clic suffit.

### Étape 4 — Attendre l'installation automatique

Au premier lancement, le script installe automatiquement :

1. **uv** (un gestionnaire Python moderne, ~5 Mo) — quelques secondes.
   Windows te demandera peut-être l'autorisation d'exécuter un script
   PowerShell : accepte.
2. **Un Python moderne** (3.13+) dans un cache local géré par uv —
   15-30 secondes.
3. **Les dépendances Python** (pandas, numpy, matplotlib, requests,
   ~80 Mo de wheels) — 15 secondes à 2 minutes selon ta connexion.

**Durée totale : de 30 secondes (fibre) à ~2 minutes (4G en intérieur) la
toute première fois.** Tu vois les barres de progression dans la fenêtre.
Ne ferme pas la fenêtre.

Les lancements suivants seront **instantanés** (< 2 secondes).

---

## Utilisation mensuelle

Chaque 1ᵉʳ du mois (tolérance J+2 si tu es pris) :

1. Double-clique sur `chill.bat`.
2. Le CLI affiche à la suite, sans que tu aies à choisir quoi que ce soit :
   - **Le signal du mois** : 100 % BTC, 50 % BTC + 50 % USDC, ou 0 %
     BTC (100 % USDC).
   - **Le récap des 10 derniers mois** : perf de la stratégie vs HODL
     (buy-and-hold simple) mois par mois.
   - **Le récap annuel depuis 2016** : perf année par année, perf
     annualisée (3 ans, 5 ans, depuis le début), et drawdown maximal
     global.
3. Compare la position cible affichée avec ta position actuelle sur Binance
   (ou autre plateforme).
4. **Si la position change**, ajuste ton allocation sur la plateforme avec
   des ordres à marché :
   - 100 % → tout en BTC.
   - 50 % → moitié BTC, moitié USDC (au mieux-
     disant).
   - 0 % → tout en USDC.
5. Appuie sur une touche pour fermer la fenêtre. Reviens dans un mois.

**En moyenne, le signal change 1 fois par an** sur le backtest 2016-2026.
Les autres mois, tu n'as qu'à confirmer que rien n'a bougé.

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

**Comment lire ce tableau** :

- **perf strat** / **perf HODL** : performance de la stratégie vs un simple
  buy-and-hold BTC, année par année.
- **delta** = perf strat − perf HODL. Négatif = la stratégie a sous-performé
  HODL cette année (normal en bull market fort, la stratégie entre plus
  tard en position). Positif = la stratégie a surperformé HODL (typiquement
  les années bear, où elle a su sortir).
- **DD max** = drawdown intra-année maximal (la plus grosse baisse pic-à-
  creux pendant l'année).
- **Perf annualisée** = taux de croissance composé équivalent (CAGR).
  Sur 10 ans, la stratégie bat HODL de 80 % vs 64 %.
- **DD max depuis 2016** : plus grosse chute pic-à-creux sur toute
  l'histoire. La stratégie a plafonné à −40 %, contre −75 % pour HODL.

**Le compromis fondamental** : la stratégie lague souvent en bull market (le
delta est négatif), mais protège en bear (delta très positif en 2018 et
2022). Sur le long terme, la protection bear compense largement le lag
bull, tant en CAGR qu'en drawdown.

⚠ **Past performance does not guarantee future results.** Le backtest
suppose que les cycles BTC historiques (halving + bull/bear marqués)
continuent. Si BTC entre dans un régime "actif macro lisse" sans crash
violent, l'avantage de la stratégie vs HODL se réduira mécaniquement.

---

## Disclaimer

**Ceci n'est pas un conseil en investissement.** L'outil produit un signal
mécanique à partir d'une stratégie calibrée sur l'historique public BTC.
Les décisions d'allocation sont à ta charge. L'auteur décline toute
responsabilité pour les pertes éventuelles.

**Hypothèses de la stratégie** :
- **Résidence fiscale : France.** Cash = USDC
  pour éviter la friction fiscale sur les switches mensuels (fait
  générateur = cession en monnaie ayant cours légal, art. 150 VH bis CGI).
  Si tu es résident fiscal ailleurs, adapte ou consulte ton comptable.
- **Plateforme : Binance.** Les frais sont estimés à 0,5 % par switch
  (hypothèse conservatrice, réel ~0,15-0,20 % avec USDC).
- **Horizon : plusieurs cycles BTC (4+ ans).** La stratégie n'a pas de sens
  sur moins d'un cycle complet. Ne l'utilise pas pour "timer" à court terme.
- **Capital : uniquement ce que tu peux te permettre de voir chuter de
  −50 %.** Même avec la protection bear, un drawdown de cet ordre n'est
  pas exclu (voir DD max 2019 et 2022 dans le tableau).

---

## FAQ

**Q : Le site `cryptodatadownload.com` est down, le script échoue.**

R : Réessaie dans quelques heures ou le lendemain. Si ça persiste, ouvre
`engine\data\btc_monthly.csv` (cache local) — le dernier prix y est stocké.
Tu peux déplacer le signal d'un ou deux jours sans impact.

**Q : Je veux tester sur un autre PC ou transférer l'outil.**

R : Copie simplement le dossier complet `chillbtc\` (qui inclut `code\`,
`macos\`, `windows\`) sur la nouvelle machine. Double-clique à nouveau sur
`chill.bat`. La première install sera refaite (30 s à 2 min).

**Q : Je veux repartir à zéro (reset).**

R : Supprime le dossier `code\.venv\` (recréé au prochain lancement) et le
fichier `code\output\live_journal.csv` (re-bootstrappé au prochain lancement
depuis `code\output\cascade_position.csv`).

**Q : Comment désinstaller complètement ?**

R : Supprime le dossier `chillbtc\`. Pour aller plus loin, supprime
aussi le binaire uv (`%USERPROFILE%\.local\bin\uv.exe`) et le cache uv
(`%LOCALAPPDATA%\uv\cache\`) si tu ne t'en sers pas pour d'autres projets.

**Q : Windows bloque l'exécution du script PowerShell au premier lancement.**

R : Le launcher utilise `-ExecutionPolicy ByPass` pour contourner la
restriction par défaut, mais si ton administrateur système a durci les
règles, demande-lui de te laisser exécuter `irm https://astral.sh/uv/install.ps1 | iex`
en PowerShell, ou installe uv manuellement depuis https://docs.astral.sh/uv/.

**Q : Pourquoi le dossier `code\` n'est pas dans `windows\` ?**

R : `code\` contient le moteur Python partagé entre macOS et Windows. Le
séparer évite la duplication. Le launcher `chill.bat` sait aller le chercher
automatiquement.
