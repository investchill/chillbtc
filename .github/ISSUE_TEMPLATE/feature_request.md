---
name: Proposition d'amélioration
about: Nouvelle règle, optimisation, visualisation, etc. Scope verrouillé — lis d'abord.
title: "[feat] "
labels: ["enhancement"]
---

## Scope architectural

La stratégie ChillBTC est **verrouillée par conception** pour limiter
l'overfit (cf. [`CONTRIBUTING.md §6`](../CONTRIBUTING.md)) :

- **3 règles** (TSMOM tendance, Mayer, Power Law valorisation), pas plus.
- **3 familles d'optimisation** (plateau, walk-forward, leave-one-cycle-out).
- **1 ou 2 paramètres max** par règle.
- **Cadence mensuelle** sans décision intra-mois.

Avant de proposer, confirme que tu respectes ces contraintes. Si ta
proposition les dépasse, explique pourquoi dans « Pourquoi ».

## Ce que ça fait

En une phrase.

## Pourquoi

Quel problème concret ça résout. Si ça ajoute une règle, montre sur
quelles années historiques elle aurait aidé (sans choisir les dates
après coup).

## Comment

Esquisse d'implémentation. Si c'est une règle, donne la formule, les
1-2 paramètres, et leur plage raisonnable.

## Anti-overfit

- [ ] La règle dépend d'au plus 2 paramètres.
- [ ] Le gain dépend d'un **plateau de stabilité**, pas d'un pic isolé
      dans le grid search.
- [ ] Le backtest inclut les frais (conservateur 0,5 % par switch).
- [ ] La proposition ne touche pas aux paramètres figés S2 / S8 / cascade
      `strict_r1_def` / dosage 100-50-0 en dehors d'une fenêtre de revue
      annuelle (1ᵉʳ janvier).
