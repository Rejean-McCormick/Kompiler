<!-- kOA Doc Server · Docs IA · lot 01 · source datée, non-certifiante -->
# Documentation IA — Kompiler

**Périmètre :** Moteur local de requêtes et compilation de Context Packs à partir de vues de lecture autorisées et épinglées.

**Origine :** snapshot local documenté (20 novembre 2026, ou archive complémentaire). Les chemins et versions actifs sont à vérifier sur le poste avant toute modification.

**Autorité :** Kompiler possède son protocole de contexte, ses adaptateurs de lecture et ses exports. Les sources Kristal et autres collections conservent autorité sémantique, provenance et droits.

## Ordre de lecture conseillé à un agent

1. [`README.md`](../../README.md) — Commandes et statut.
2. [`docs/02-protocol/context-pack-contract.md`](../../docs/02-protocol/context-pack-contract.md) — Contrat des Context Packs.
3. [`docs/03-runtime/context-compiler.md`](../../docs/03-runtime/context-compiler.md) — Compilation, budgets et provenance.
4. [`docs/04-interfaces/cli.md`](../../docs/04-interfaces/cli.md) — CLI.
5. [`docs/05-security/determinism-provenance.md`](../../docs/05-security/determinism-provenance.md) — Règles de confiance et provenance.
6. [`pyproject.toml`](../../pyproject.toml) — Entrées/exigences du paquet.
7. [`src/kompiler/__main__.py`](../../src/kompiler/__main__.py) — Point d’entrée Python.
8. `tests` — Suite de tests — vérifier le contenu avant exécution.

## Documents produits par cet overlay

- [`AI_CONTEXT.md`](AI_CONTEXT.md) — limites, parcours et points de contrôle.
- `PROFIL_INGENIERIE.md` — produit **sur demande** à partir d'un scan RepoSurveyor du code local; ce fichier n'est pas fourni par le lot rédactionnel.
- `AGENTS.md` à la racine — consignes de dépôt existantes conservées ou nouvelles si elles n'existaient pas.

## Règles transversales

- Une capture documentaire n'établit ni conformité, ni maturité, ni disponibilité en production.
- Ne pas remplacer contrats, ADR, README ou preuves propriétaires par cette aide de navigation.
- Nouveau Framework v11 : lire le profil effectivement adopté; ne jamais imposer une migration par défaut.

## Procédure opérationnelle proposée (lot 04)

- [`OPERATIONS.md`](OPERATIONS.md) — parcours concret et points de contrôle à vérifier avant tout effet.
