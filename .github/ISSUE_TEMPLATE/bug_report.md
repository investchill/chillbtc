---
name: Bug
about: Un comportement qui diffère de ce que la documentation annonce.
title: "[bug] "
labels: ["bug"]
---

## Comportement attendu

Qu'est-ce que la doc (README, CONTRIBUTING, methodologie) indique que le
code doit faire ?

## Comportement observé

Qu'est-ce que tu as vu à la place ? Collez la sortie exacte si pertinent
(stacktrace, valeur de signal, dosage produit).

## Étapes de reproduction

1. `git clone https://github.com/investchill/chillbtc.git`
2. `cd chillbtc/engine && uv sync --group dev`
3. `uv run <commande>`
4. …

## Environnement

- OS :
- Python :
- Commit (`git rev-parse HEAD`) :
- Branche :

## Contexte supplémentaire

Tout ce qui aiderait à diagnostiquer (modif locale, version de `uv`,
dataset particulier, etc.).
