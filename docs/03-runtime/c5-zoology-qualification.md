# C5 — Kompiler 0.8.0-alpha.1 / Zoology / Framework draft.3.1

**Statut : tests de lecture et compatibilité locale, pas une publication qualifiée.**

## Écart corrigé

La version réelle du Framework est `10.0.0-draft.3.1`, distincte du `draft.3` précédemment supporté. L'algorithme de sécurité Kompiler existant attend un contrat pris par version et une empreinte SHA-256 exacte. Le snapshot `draft.3.1` documenté a pour empreinte du fichier `contracts/contract-set.json` :

`fd8add31bb0a20159fd2e6c6c3175863a8195c9840e0b9f6a8cc388e57176c92`

`src/kompiler/kristal-standard.lock.json` ajoute cette version et **son empreinte spécifique**. Les pins `draft.2` et `draft.3` sont conservés. Tout autre ensemble de contrats portant le même numéro de version reste bloqué par défaut, à moins d'un pin opérateur explicite vérifié. Aucun commit de Framework n'est inventé.

`kristal-v10.integration.json` annonce le Kompiler observé `0.8.0-alpha.1` et cible `draft.3.1` ; les profils v6, v9 et GitHub v10 conservent leurs responsabilités respectives.

## Démonstration reproductible

Depuis le dépôt Kompiler avec `pytest` et les dépendances de développement :

```powershell
$env:C5_FRAMEWORK_ROOT='C:\mycode\Kristal\Kristal-Framework'
$env:KOMPILER_KRISTAL_STANDARD_ROOT=$env:C5_FRAMEWORK_ROOT
$env:C5_ZOOLOGY_ROOT='C:\mycode\Kristal\locals\Kristal-Zoology'
python -m pytest tests/integration/test_c5_framework_pin.py tests/integration/test_c5_zoology_local.py -v
```

Pour `test_c5_zoology_read_surface.py`, générer d'abord la couche IA **sur une copie temporaire du dossier Zoology**, puis affecter `C5_ZOOLOGY_ROOT` à cette copie :

```powershell
python tools/kristal.py build-v9 .
python tools/kristal.py build-ai .
python tools/kristal.py check-ai .
```

La fixture hébergée est créée dans le répertoire temporaire du test et réutilise les octets véritables du Kristal. Elle **n'est ni signée par Manager ni publiée**, et ne remplace aucun reçu de C1/C2/C3. Le test contrôle l'index, le manifeste, les chemins, les SHA, le refus d'une ressource non déclarée, la corruption d'un fichier et la création de Context Pack en lecture seule.

## Chaîne C5 validée sur la copie 2026-10-08

- Framework `10.0.0-draft.3.1` chargé avec le pin exact et refus des hashes divergents.
- Zoology : `sha256:2503493eed8b2515107f9c32eed48286845f5468838ad3ae7b4a8f66a65f2ac8` (engagement de state v9).
- API Kompiler locale `kompiler.capabilities/1.1` ; pont `doctor` et `run` vers `kompiler.context-pack/1.1` réels.
- Context Pack : `recordCount=1`, provenance source Zoology et engagement v9 présents.
- Suite pytest Kompiler avec snapshots et variables d'environnement : réussite (voir rapport C5 livré séparément).

## Non qualifié

- La publication v10 immuable réelle de Zoology ; `kristal-public` n'expose pas encore l'index v10.
- Le pipeline C1→C2→C3→C4, l'autorisation de diffusion, un commit GitHub vérifié et la qualification métier indépendante.
- Le rendu Konstellation historique, qui nécessite son runtime UI propre.
- L'Integration Pack est un pont vers **Konstellation historique**, pas vers Konstellation Light : ne pas assimiler les deux.

**Aucun changement dans l'identité sémantique ni l'autorité des sources.**
