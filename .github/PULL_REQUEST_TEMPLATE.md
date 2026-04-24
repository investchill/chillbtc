## Résumé

<!-- 1 à 3 phrases. Qu'est-ce que cette PR change, et pourquoi ? -->

## Checklist

- [ ] `uv run --group dev ruff check .` passe localement.
- [ ] `uv run --group dev pytest` passe localement (33+ tests verts).
- [ ] Si la PR touche à la doc utilisateur (README, methodologie,
      CONTRIBUTING), la prévisualisation GitHub rend correctement.
- [ ] Si la PR ajoute du code qui lit des prix ou calcule des signaux,
      au moins un test couvre le nouveau comportement.

## Impact sur la stratégie live

- [ ] Cette PR **ne modifie pas** les paramètres gelés (S2 n=11,
      S8 k_low=0.6 / k_high=2.5 / A=-16.917, convention
      `strict_r1_def`, dosage 100 / 50 / 0).
- [ ] Cette PR **ne modifie pas** le cron du workflow mensuel (1ᵉʳ du
      mois à 06:00 UTC).
- [ ] Cette PR **ne modifie pas** le contenu rendu de `docs/signaux.md`
      (à l'exception d'un header ou d'une légende explicite).

Si une case est décochée ci-dessus, ouvre une **issue `[meta]`** avant
la PR et décris pourquoi la revue annuelle ne suffit pas.

## Type de PR

- [ ] Bug fix (le code diffère de la doc et on rapproche le code).
- [ ] Amélioration doc, test, lisibilité, perf (signaux produits
      inchangés).
- [ ] Nouvelle règle / optim / visualisation (scope verrouillé, voir
      `CONTRIBUTING.md §6`).
- [ ] Trigger META (issue associée : #).
