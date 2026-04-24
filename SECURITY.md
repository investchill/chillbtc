# Security

## Quoi rapporter

- Une vulnérabilité dans le code Python (injection, désérialisation, etc.).
- Un problème sur le workflow GitHub Actions qui pourrait être exploité
  (permissions excessives, secret exposé, tampering d'artefacts).
- Un dépegging ou une faille stablecoin qui invalide la règle
  `CASH = USDC` telle qu'elle est documentée.
- Un bug qui, s'il se propage au live, pourrait causer un mauvais signal
  (ex. faute arithmétique dans `rules.py` ou `cascade.py`).

Ce ne sont pas des vulnérabilités :

- La stratégie ChillBTC **n'est pas un conseil en investissement** et
  peut sous-performer le marché. Les performances passées ne préjugent
  pas des performances futures.
- La sensibilité du résultat à un choix de paramètre ou de fenêtre n'est
  pas un bug, c'est un caveat documenté dans
  [`docs/methodologie.md`](docs/methodologie.md).

## Comment rapporter

**Privé** : envoyez un mail à `chillbtc@zaclys.net`. Merci de ne pas
ouvrir d'issue publique avant la correction.

Réponse attendue sous **7 jours**. Corrections sous **30 jours** quand
c'est techniquement tenable, plus tôt si l'exploitation est triviale.

## Périmètre

Le dépôt couvert est `github.com/investchill/chillbtc`. Les forks ne
sont pas dans le périmètre.
