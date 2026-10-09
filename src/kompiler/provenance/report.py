from __future__ import annotations

from typing import Any

from kompiler.protocol.models import ContextPack


def reproducibility_report(pack: ContextPack) -> dict[str, Any]:
    receipts = pack.execution.receipts
    return {
        "context_pack_id": pack.context_pack_id,
        "semantic_hash": pack.semantic_hash,
        "artifact_hash": pack.artifact_hash,
        "query_hash": pack.execution.query_hash,
        "config_hash": pack.execution.config_hash,
        "cache_hits": pack.execution.cache_hits,
        "truncated": pack.summary.truncated,
        "operation_statuses": {r.operation_id: r.status for r in receipts},
        "source_states": sorted({s.source_state_id for s in pack.sources if s.source_state_id}),
        "reproducible_expected": all(r.status == "success" for r in receipts) and not pack.summary.truncated,
    }
