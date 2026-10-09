from pathlib import Path

from kompiler.adapters.common import KristalAdapterBase, opcap
from kompiler.adapters.base import AdapterContext, AdapterResult


class MissingSourceAdapter(KristalAdapterBase):
    adapter_id = "missing-source"
    adapter_version = "1"
    target_id = "Missing"

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.identity_paths = [self.root / "does-not-exist.json"]

    def capabilities(self):
        return [opcap("find", "find", {})]

    async def execute(self, operation: str, params: dict, context: AdapterContext):
        return AdapterResult()


def test_missing_identity_files_do_not_create_empty_hash(tmp_path: Path):
    adapter = MissingSourceAdapter(tmp_path)
    desc = adapter.source_descriptor()
    assert desc.state_id is None
    assert desc.integrity == "unknown"
    health = adapter.health()
    assert health["ok"] is False
    assert health["missing_identity_paths"] == ["does-not-exist.json"]
