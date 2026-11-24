<!-- kOA Doc Server · Docs IA · lot 01 · source datée, non-certifiante -->
# Documentation IA — Kompiler

**Périmètre :** Moteur local de requêtes et compilation de Context Packs à partir de vues de lecture autorisées et épinglées.

**Origine :** snapshot local documenté (20 novembre 2026, ou archive complémentaire). Les chemins et versions actifs sont à vérifier sur le poste avant toute modification.

**Autorité :** Kompiler possède son protocole de contexte, ses adaptateurs de lecture et ses exports. Les sources Kristal et autres collections conservent autorité sémantique, provenance et droits.

## Méthode de travail IA

1. Partir de l’intention de lecture et du profil/adaptateur de la source.
2. Vérifier les autorisations, révisions épinglées et les budgets avant compilation.
3. Produire des artefacts portant provenance et limites de couverture; les résultats dérivés ne deviennent pas canon.
4. Ne pas assimiler un ZIP documentaire Doc Server au contrat Context Pack natif de Kompiler.

## Entrées et validations attestées par les sources

- `kompiler capabilities`
- `kompiler validate examples/queries/education.json`
- `kompiler self-test`

*Avant exécution, vérifier les préconditions locales et les effets possibles de la commande. Les commandes sont des points d’entrée documentés, pas des validations effectuées par cet overlay.*

## Frontières à ne jamais franchir

- Kompiler n’est ni l’éditeur du Kristal ni l’autorité de publication.
- Refuser l’exécution shell arbitraire ou un accès non autorisé à des sources.
- Le Framework v11 n’est activé que pour les profils/lecteurs explicitement compatibles.

## Incertitudes et limites explicites

- L’exemple CLI est indicatif; le projet utilise un dossier `src/` et peut nécessiter une installation en mode développement.

## Sources à relire

- [`README.md`](../../README.md) — Commandes et statut.
- [`docs/02-protocol/context-pack-contract.md`](../../docs/02-protocol/context-pack-contract.md) — Contrat des Context Packs.
- [`docs/03-runtime/context-compiler.md`](../../docs/03-runtime/context-compiler.md) — Compilation, budgets et provenance.
- [`docs/04-interfaces/cli.md`](../../docs/04-interfaces/cli.md) — CLI.
- [`docs/05-security/determinism-provenance.md`](../../docs/05-security/determinism-provenance.md) — Règles de confiance et provenance.
- [`pyproject.toml`](../../pyproject.toml) — Entrées/exigences du paquet.
- [`src/kompiler/__main__.py`](../../src/kompiler/__main__.py) — Point d’entrée Python.
- `tests` — Suite de tests — vérifier le contenu avant exécution.
