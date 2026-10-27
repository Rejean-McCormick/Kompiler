from __future__ import annotations

from pathlib import Path
import asyncio
from typing import Any

from kompiler.adapters.base import Adapter, AdapterContext, AdapterResult
from kompiler.adapters.common import opcap
from kompiler.github_collection import CollectionReader
from kompiler.protocol.models import OperationCapability, SourceDescriptor
from kompiler.errors import AdapterError


class GithubCollectionAdapter(Adapter):
    """Optional reader for a local/hosted collection, not a hosting manager."""

    adapter_id = "kristal-github-collection"
    adapter_version = "1.0.0"
    kind = "kristal-collection"

    def __init__(self, source: str | Path, target_id: str | None = None):
        self.reader = CollectionReader(source)
        self.root = self.reader.root or Path(".")
        name = (self.reader.remote or self.root.name).replace("/", ":")
        self.target_id = target_id or f"GitHubCollection:{name}"

    def source_descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            contract_family="kristal.github-collection-index/1.0",
            snapshot_id=self.reader.index["index_digest"],
            root_hint=self.reader.source_uri,
            integrity="derived-index-and-content-sha256",
        )

    def health(self) -> dict[str, Any]:
        return {"ok": True, "adapter_id": self.adapter_id, "target_id": self.target_id, "source": self.reader.source_uri, "collection_count": len(self.reader.entries), "index_digest": self.reader.index["index_digest"], "source_revision": self.reader.revision, "network": self.reader.is_network}

    def capabilities(self) -> list[OperationCapability]:
        net = self.reader.is_network
        return [
            opcap("catalog", "Search the small derived collection index without traversing all Kristals.", {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 200}, "offset": {"type": "integer", "minimum": 0}}, max_items=200, network=net, record_kinds=["kristal_collection_entry"]),
            opcap("files", "Read the verified file/digest map for one hosted Kristal.", {"slug": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 500}}, ["slug"], max_items=500, network=net, record_kinds=["kristal_read_surface_file"]),
            opcap("read", "Read one explicitly declared UTF-8 resource with SHA-256 verification.", {"slug": {"type": "string"}, "path": {"type": "string"}}, ["slug", "path"], max_items=1, max_bytes=1_048_576, network=net, record_kinds=["kristal_verified_content"]),
            opcap("entrypoint", "Read the verified AI_START_HERE.md for one hosted Kristal.", {"slug": {"type": "string"}}, ["slug"], max_items=1, max_bytes=1_048_576, network=net, record_kinds=["kristal_verified_content"]),
        ]

    async def execute(self, operation: str, params: dict[str, Any], context: AdapterContext) -> AdapterResult:
        slug = str(params.get("slug") or "")
        if operation == "catalog":
            result = await asyncio.to_thread(self.reader.catalog, query=str(params.get("query") or ""), limit=int(params.get("limit") or 100), offset=int(params.get("offset") or 0))
            return AdapterResult(items=result["entries"], metadata={k: v for k, v in result.items() if k != "entries"})
        if operation == "files":
            result = await asyncio.to_thread(self.reader.reading_map, slug, limit=int(params.get("limit") or 100))
            return AdapterResult(items=result["files"], metadata={k: v for k, v in result.items() if k != "files"})
        if operation in {"read", "entrypoint"}:
            rel = "AI_START_HERE.md" if operation == "entrypoint" else str(params.get("path") or "")
            return AdapterResult(items=[await asyncio.to_thread(self.reader.read, slug, rel)])
        raise AdapterError("UNKNOWN_OPERATION", f"Unsupported GitHub collection operation: {operation}")
