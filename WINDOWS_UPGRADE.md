# Mise à niveau Windows — Kompiler 0.8.0-alpha.1

1. Sauvegarder vos fichiers de configuration, bases de données et adaptateurs externes. Extraire le ZIP dans un nouveau dossier, sans écraser une ancienne installation en cours d'exécution.
2. Installer Python **3.12+**, puis ouvrir PowerShell dans le dossier `Kompiler-0.8.0-alpha.1`.
3. Exécuter `py -m pip install -e ".[api]"` (ou `py -m pip install -e .` pour la CLI uniquement).
4. Configurer `[kristal_standard].root = "C:/mycode/Kristal/Kristal-Framework"` dans votre TOML, ou la variable d'environnement `KOMPILER_KRISTAL_STANDARD_ROOT`.
5. Pour le snapshot Framework draft.3 fourni le 8 octobre, aucun hash manuel n'est nécessaire. Pour une autre révision draft.3, configurer le SHA-256 exact de `contracts/contract-set.json` dans `[kristal_standard].contract_set_sha256`.
6. Tester `py -m kompiler self-test`, puis `py -m kompiler capabilities` après configuration.
7. Lancer le panneau Windows avec `pyw Kompiler.pyw` ou le script lui-même, selon l'association Python de Windows.

Le mode de sélection par défaut ne change pas. Pour opter explicitement pour une sélection lexicale, utiliser dans votre requête JSON :

```json
"topic": "solar energy",
"budget": {"max_items": 25, "selection_mode": "lexical"}
```

Il s'agit d'un fragment à insérer dans une requête `kompiler.query` complète. Aucun compte GitHub ni accès réseau n'est requis pour travailler sur les collections locales. Pour les collections distantes, `gh auth login` et un accès réseau explicitement autorisé sont nécessaires.

Kompiler ne sauvegarde pas, ne synchronise pas et n'active pas les Kristals. Ces actions appartiennent aux autres outils du système.
