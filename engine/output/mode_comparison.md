## §13 — Comparaison des 3 modes candidats d'exploitation

Règle de sélection : contrainte **DD ≤ -50 %** (cible bon père de famille).
Tie-break CAGR. Fenêtre backtest : 2016-05-31 → 2026-03-31 (119 mois), frais 0,5 % par switch.

### Candidats retenus

- **Mode A** : sélection de la cellule `S8` (max CAGR sous DD ≤ -50 %).
- **Mode B** : ensemble vote K=4 parmi 9.
- **Mode C** : cascade R1 (S2, R1×O2 DD, n=11) + R3 (S8, R3×O2 CAGR walk-forward), convention `strict_r1_def` (edge case R1 BUY & R3 CASH → 0 %).

### KPIs comparés

```
mode       label                      CAGR    Max DD   Sharpe   switch/an
HODL       HODL                     63.82%   -75.41%    1.011       0.000
Mode A     S8 (cellule)             97.92%   -42.13%    1.383       0.403
Mode B     ensemble_K4              96.15%   -42.13%    1.317       0.706
Mode C     cascade R1+R3 (100/50/0)   80.11%   -40.32%    1.303       1.008
```

### Matrice de dominance stricte (A vs B = A >= B sur les 3 KPI, > sur ≥ 1)

```
           Mode A       Mode B       Mode C      
Mode A     —            DOMINE       NON-DOMINÉ
Mode B     NON-DOMINÉ   —            NON-DOMINÉ
Mode C     NON-DOMINÉ   NON-DOMINÉ   —
```

### Diagnostic

- Tous les modes battent HODL sur DD (-75.4 %) et sur CAGR.
- Mode C cascade a le **meilleur DD** (-40.32 % vs -42.13 % pour A et B), aligné avec le but "sortir en bear pour limiter le DD".
- Mode A (S8 seul) a le **meilleur CAGR** (97.9 %), mais c'est une cellule R3 isolée — **biais in-sample non complètement lavé** (refit de A sur la full history, WFE=0.585 en Phase C). La perf "honnête" hors biais serait plus basse.
- Mode B ensemble K=4 **dilue le biais R3** (9 cellules votent) mais ne domine A sur aucun KPI. Il sert surtout de filet de robustesse conceptuelle.
- Mode C cascade a le **Sharpe le plus bas** des 3 modes actifs (1.30), mais **aucun des 3 modes ne domine strictement les 2 autres** : A gagne CAGR/Sharpe mais perd DD, C gagne DD mais perd CAGR/Sharpe.

### Implication pour la sélection finale

La clause de dégradation (« une seule cellule domine les 8 autres sur les 3 critères → bascule Mode A ») **ne se déclenche pas** sur la fenêtre actuelle : A domine partiellement mais pas strictement. Le choix entre A, B, C est donc un arbitrage de préférences :

- **Priorité DD** (cohérent avec le profil déclaré) → Mode C cascade.
- **Priorité CAGR brut** → Mode A (S8 seul), avec acceptation du biais in-sample.
- **Priorité robustesse conceptuelle** (9 règles votent) → Mode B K=4.
