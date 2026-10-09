# Built-in Adapter Catalog

The reference runtime includes trusted adapters for the Kristal shapes used during Kompiler design.

| Target | Adapter type | Main integration mode |
|---|---|---|
| `Kristall:<namespace_id>` | `kristall-v7` | v7 manifest + registries + Mesh + Surface compilation |
| `KristalState:<name>` | `kristal-v6-state` | generic validated read of any portable `kristal_state/6.0` |
| Math | `kristal-math` | existing JSON-emitting `tools/query.py` |
| HumanBody | `kristal-humanbody` | direct structured corpus/projection reads |
| ScolQc | `kristal-scolqc` | existing JSON-emitting `tools/query.py` |
| Catho | `kristal-catho` | existing `tools/query.py --json` |
| Power | `kristal-power` | direct ontology/graph/state reads |
| Recipes | `kristal-recipes` | existing JSON-emitting query CLI |
| HomeCare | `kristal-homecare` | demo projection query CLI |
| VehicleDiag | `kristal-vehiclediag` | graph query CLI plus direct ID listing |
| HospitalOps | `kristal-hospitalops` | direct glossary/state/source reads |

Adapters expose semantic operation IDs. Native CLI flags and physical file names are not part of the Kompiler protocol.

The `kristal-v6-state` adapter is the generic V7-Reader boundary: it validates an unchanged portable v6 state, preserves any declared `state_id`, and exposes read-only assertion/meta queries without rewriting source bytes.

The `kristall-v7` adapter is a meta-plane adapter rather than a source Kristal adapter. It validates the v7 deployment artifacts, exposes Surface-oriented operations, preserves KQ/KP/KA/KS identity spaces, and can coexist with the source Kristals referenced by the deployment.

Use `kompiler adapters discover <paths...>` to inspect known signatures without executing repository scripts. Use `kompiler adapters manifest <root>` to generate a trusted local manifest draft.

Direct application-owned `source-catalog/` reads are intentionally not built-in. Source catalogs belong behind the Médiathèque/Kristal authority boundaries rather than inside Kompiler.
