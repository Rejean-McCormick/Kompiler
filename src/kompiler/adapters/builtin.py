from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .base import Adapter
from .catho import CathoAdapter
from .homecare import HomeCareAdapter
from .hospitalops import HospitalOpsAdapter
from .humanbody import HumanBodyAdapter
from .manifest import AdapterManifest
from .kristall import KristallAdapter
from .kristal_v6 import KristalV6StateAdapter, find_v6_state, target_id_for_state
from .kristal_v9 import KristalV9StateAdapter, find_v9_state, target_id_for_v9
from .github_collection import GithubCollectionAdapter
from .kristal_v10 import KristalV10PublicationAdapter, find_v10_publication, target_id_for_v10
from .kristal_v11 import KristalV11ReadViewAdapter
from kompiler.kristall import find_kristall_manifest
from .math import MathAdapter
from .power import PowerAdapter
from .recipes import RecipesAdapter
from .scolqc import ScolQcAdapter
from .vehicle import VehicleDiagAdapter


def _root_from_manifest(m: AdapterManifest) -> Path:
    return m.root


BUILTIN_FACTORIES: dict[str, Callable[[AdapterManifest], Adapter]] = {
    "kristal-math": lambda m: MathAdapter(_root_from_manifest(m)),
    "kristal-humanbody": lambda m: HumanBodyAdapter(_root_from_manifest(m)),
    "kristal-scolqc": lambda m: ScolQcAdapter(_root_from_manifest(m)),
    "kristal-catho": lambda m: CathoAdapter(_root_from_manifest(m)),
    "kristal-power": lambda m: PowerAdapter(_root_from_manifest(m)),
    "kristal-recipes": lambda m: RecipesAdapter(_root_from_manifest(m)),
    "kristal-homecare": lambda m: HomeCareAdapter(_root_from_manifest(m)),
    "kristal-vehiclediag": lambda m: VehicleDiagAdapter(_root_from_manifest(m)),
    "kristal-hospitalops": lambda m: HospitalOpsAdapter(_root_from_manifest(m)),
    "kristall-v7": lambda m: KristallAdapter(_root_from_manifest(m), target_id=m.target_id),
    "kristal-v6-state": lambda m: KristalV6StateAdapter(_root_from_manifest(m), target_id=m.target_id),
    "kristal-v9-state": lambda m: KristalV9StateAdapter(_root_from_manifest(m), target_id=m.target_id),
    "kristal-github-collection": lambda m: GithubCollectionAdapter(_root_from_manifest(m), target_id=m.target_id),
    "kristal-v10-publication": lambda m: KristalV10PublicationAdapter(_root_from_manifest(m), target_id=m.target_id),
    "kristal-v11-read-view": lambda m: KristalV11ReadViewAdapter(m),
}


def _candidate_roots(root: Path) -> list[Path]:
    root = root.resolve()
    out = [root]
    for pattern in ["knowledge-base", "power-knowledge-base", "Kristal-*/knowledge-base", "*/knowledge-base"]:
        out.extend(p.resolve() for p in root.glob(pattern) if p.is_dir())
    return list(dict.fromkeys(out))


def detect_builtin(root: Path) -> tuple[str, Path, str] | None:
    root = root.expanduser().resolve()
    if (root / "kristals" / "index.json").is_file():
        return "kristal-github-collection", root, f"GitHubCollection:{root.name}"
    v10 = find_v10_publication(root)
    if v10 is not None:
        return "kristal-v10-publication", v10, target_id_for_v10(v10)
    v9 = find_v9_state(root)
    if v9 is not None:
        # Preserve the Local Kristal workspace root when discovery starts there.
        # This lets the adapter retain the semantic surface (build-v9 vs AI mirror
        # vs release) instead of collapsing every local state into an explicit file.
        adapter_root = root if root.is_dir() and (root / "kristal.workspace.json").is_file() else v9
        return "kristal-v9-state", adapter_root, target_id_for_v9(v9)
    manifest = find_kristall_manifest(root)
    if manifest is not None:
        try:
            value = json.loads(manifest.read_text(encoding="utf-8"))
            namespace_id = str(value.get("namespace_id") or manifest.parent.name)
        except Exception:
            namespace_id = manifest.parent.name
        return "kristall-v7", manifest.parent, f"Kristall:{namespace_id}"
    for c in _candidate_roots(root):
        if (c / "corpus/math.structured-epistemic-state.json").exists(): return "kristal-math", c, "Math"
        if (c / "corpus/humanbody.structured-epistemic-state.json").exists(): return "kristal-humanbody", c, "HumanBody"
        if (c / "sources/progression_semantics.json").exists() and (c / "tools/query.py").exists(): return "kristal-scolqc", c, "ScolQc"
        if (c / "canonical-corpus/corpus-chretien.semantic.json").exists(): return "kristal-catho", c, "Catho"
        if (c / "corpus/power-topology.structured-epistemic-state.json").exists(): return "kristal-power", c, "Power"
        if (c / "corpus/classification-index.json").exists() and (c / "corpus/search-documents.json").exists(): return "kristal-recipes", c, "Recipes"
        if (c / "examples/demo-home/projections/current-state.json").exists(): return "kristal-homecare", c, "HomeCare"
        if (c / "corpus/graph.json").exists() and (c / "tools/query.py").exists(): return "kristal-vehiclediag", c, "VehicleDiag"
    # Repository-root integrations that are not knowledge-base nested.
    if (root / "knowledge-base/clinical-commons.structured-epistemic-state.json").exists(): return "kristal-hospitalops", root, "HospitalOps"
    state_path = find_v6_state(root)
    if state_path is not None:
        return "kristal-v6-state", state_path, target_id_for_state(state_path)
    return None


def instantiate_detected(adapter_type: str, root: Path) -> Adapter:
    cls = {
        "kristal-math": MathAdapter,
        "kristal-humanbody": HumanBodyAdapter,
        "kristal-scolqc": ScolQcAdapter,
        "kristal-catho": CathoAdapter,
        "kristal-power": PowerAdapter,
        "kristal-recipes": RecipesAdapter,
        "kristal-homecare": HomeCareAdapter,
        "kristal-vehiclediag": VehicleDiagAdapter,
        "kristal-hospitalops": HospitalOpsAdapter,
        "kristall-v7": KristallAdapter,
        "kristal-v6-state": KristalV6StateAdapter,
        "kristal-v9-state": KristalV9StateAdapter,
        "kristal-v10-publication": KristalV10PublicationAdapter,
        "kristal-github-collection": GithubCollectionAdapter,
    }[adapter_type]
    return cls(root)
