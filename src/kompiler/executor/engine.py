from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from kompiler.adapters.base import AdapterContext, AdapterResult
from kompiler.config import AppConfig
from kompiler.errors import AdapterError, KompilerException
from kompiler.normalization import NormalizedBatch, normalize_result
from kompiler.planner import ExecutionPlan, select
from kompiler.protocol.canonical import canonical_bytes, prefixed_hash
from kompiler.protocol.models import ExecutionSummary, OperationReceipt
from kompiler.registry import AdapterRegistry
from kompiler.storage import SQLiteStore


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _result_to_dict(result: AdapterResult) -> dict[str, Any]:
    return asdict(result)


def _result_from_dict(value: dict[str, Any]) -> AdapterResult:
    return AdapterResult(**value)


def _bound_result(result: AdapterResult, *, max_items: int, max_bytes: int) -> AdapterResult:
    """Apply deterministic operation output limits to every adapter implementation."""
    raw_count = result.raw_item_count or len(result.items)
    kept: list[Any] = []
    size = 2
    truncated = bool(result.truncated)
    for item in result.items:
        if len(kept) >= max_items:
            truncated = True
            break
        payload = canonical_bytes(item)
        # Account for a comma in the JSON array. This is deliberately conservative.
        if size + len(payload) + (1 if kept else 0) > max_bytes:
            truncated = True
            break
        kept.append(item)
        size += len(payload) + (1 if len(kept) > 1 else 0)
    if len(kept) < len(result.items):
        truncated = True
    result.items = kept
    result.raw_item_count = raw_count
    result.truncated = truncated
    return result


class RunExecutor:
    def __init__(self, registry: AdapterRegistry, config: AppConfig, store: SQLiteStore | None = None) -> None:
        self.registry = registry
        self.config = config
        self.store = store
        self._cancelled: set[str] = set()

    def cancel(self, run_id: str) -> None:
        self._cancelled.add(run_id)

    async def execute(
        self,
        plan: ExecutionPlan,
        run_id: str | None = None,
    ) -> tuple[dict[str, NormalizedBatch], dict[str, Any], ExecutionSummary]:
        run_id = run_id or f"run:{uuid.uuid4()}"
        started = _utc()
        if self.store:
            self.store.run_start(run_id, plan.query.request_id, started.isoformat(), plan.query_hash)
        receipts: dict[str, OperationReceipt] = {
            op.id: OperationReceipt(operation_id=op.id, status="pending") for op in plan.query.operations
        }
        batches: dict[str, NormalizedBatch] = {}
        raw_envelopes: dict[str, Any] = {}
        semaphore = asyncio.Semaphore(
            min(plan.query.execution.max_parallelism, self.config.limits.max_parallelism)
        )

        async def run_node(op_id: str) -> None:
            pop = plan.operations[op_id]
            op = pop.operation
            receipt = receipts[op_id]
            if run_id in self._cancelled:
                receipt.status = "cancelled"
                return

            # Required bindings are true dependencies; optional bindings may be empty after
            # an upstream failure. This distinction makes `continue` useful without silently
            # violating a required data dependency.
            failed_required = [
                b.from_operation
                for b in op.inputs
                if b.required and receipts[b.from_operation].status != "success"
            ]
            if failed_required:
                receipt.status = "skipped"
                receipt.error_code = "INVALID_DEPENDENCY"
                receipt.error_message = f"required upstream failed: {', '.join(sorted(set(failed_required)))}"
                return

            t0 = time.perf_counter()
            receipt.started_at = _utc()
            receipt.status = "running"
            try:
                params = dict(op.params)
                upstream: dict[str, Any] = {}
                for binding in op.inputs:
                    env = raw_envelopes.get(binding.from_operation)
                    values = select(env, binding.selector) if env is not None else []
                    if len(values) > self.config.limits.max_join_items:
                        raise AdapterError(
                            "RESOURCE_LIMIT_EXCEEDED",
                            f"binding {binding.from_operation} -> {op.id} selected {len(values)} items; "
                            f"limit is {self.config.limits.max_join_items}",
                            {"selected": len(values), "limit": self.config.limits.max_join_items},
                            operation_id=op.id,
                        )
                    upstream[binding.from_operation] = values
                    if binding.inject_as:
                        params[binding.inject_as] = values

                adapter = self.registry.get(op.target)
                source = adapter.source_descriptor()
                receipt.adapter_id = adapter.adapter_id
                receipt.adapter_version = adapter.adapter_version
                receipt.source_state_id = source.state_id
                receipt.source_snapshot_id = source.snapshot_id
                receipt.source_contract_family = source.contract_family
                receipt.kristall_id = source.kristall_id

                requested_items = op.budget.max_items if op.budget and op.budget.max_items else self.config.limits.max_items
                requested_bytes = op.budget.max_bytes if op.budget and op.budget.max_bytes else self.config.limits.max_bytes
                max_items = min(
                    self.config.limits.max_items,
                    requested_items,
                    pop.capability.limits.max_items or self.config.limits.max_items,
                )
                max_bytes = min(
                    self.config.limits.max_bytes,
                    requested_bytes,
                    pop.capability.limits.max_bytes or self.config.limits.max_bytes,
                )
                timeout_ms = min(
                    op.timeout_ms or plan.query.execution.default_timeout_ms,
                    pop.capability.limits.timeout_ms or self.config.limits.default_timeout_ms,
                    self.config.limits.default_timeout_ms,
                )
                ctx = AdapterContext(
                    operation_id=op_id,
                    reader_policy=plan.query.context.reader_policy,
                    timeout_ms=timeout_ms,
                    max_items=max_items,
                    max_bytes=max_bytes,
                    max_stdout_bytes=self.config.limits.max_stdout_bytes,
                    upstream=upstream,
                    surface=op.surface,
                )
                cache_key = prefixed_hash(
                    "opcache",
                    {
                        "protocol_major": "1",
                        "capability_snapshot_id": plan.capability_snapshot_id,
                        "target": op.target,
                        "operation": op.operation,
                        "params": params,
                        "surface": op.surface.model_dump(mode="json", exclude_none=True) if op.surface else None,
                        "upstream_hash": prefixed_hash("up", upstream),
                        "reader_policy": plan.query.context.reader_policy,
                        "locale": plan.query.context.locale,
                        "source": source.model_dump(mode="json", exclude_none=True),
                        "adapter": {"id": adapter.adapter_id, "version": adapter.adapter_version},
                        "limits": {
                            "max_items": max_items,
                            "max_bytes": max_bytes,
                            "timeout_ms": timeout_ms,
                        },
                        "config_hash": self.config.semantic_hash,
                    },
                )
                cache_safe = bool(source.state_id)
                cached = (
                    self.store.cache_get(cache_key)
                    if self.store and self.config.storage.cache and plan.query.execution.use_cache and cache_safe
                    else None
                )
                if cached is not None:
                    result = _result_from_dict(cached)
                    receipt.cache_hit = True
                else:
                    async with semaphore:
                        result = await asyncio.wait_for(
                            adapter.execute(op.operation, params, ctx), timeout=timeout_ms / 1000
                        )
                    result = _bound_result(result, max_items=max_items, max_bytes=max_bytes)
                    if self.store and self.config.storage.cache and plan.query.execution.use_cache and cache_safe:
                        self.store.cache_put(cache_key, _result_to_dict(result))
                # Older cache rows or third-party adapters are bounded again defensively.
                result = _bound_result(result, max_items=max_items, max_bytes=max_bytes)
                batch = normalize_result(op.target, op_id, result, source)
                batches[op_id] = batch
                raw_envelopes[op_id] = {
                    "items": result.items,
                    "records": [r.model_dump(mode="json", exclude_none=True) for r in batch.records],
                    "referents": [r.model_dump(mode="json", exclude_none=True) for r in batch.referents],
                    "relations": [r.model_dump(mode="json", exclude_none=True) for r in batch.relations],
                    "metadata": result.metadata,
                }
                receipt.status = "success"
                receipt.raw_item_count = result.raw_item_count
                receipt.normalized_item_count = len(batch.records)
                receipt.truncated = result.truncated
            except asyncio.TimeoutError:
                receipt.status = "failed"
                receipt.error_code = "TIMEOUT"
                receipt.error_message = f"operation exceeded configured timeout"
            except asyncio.CancelledError:
                receipt.status = "cancelled"
                receipt.error_code = "CANCELLED"
                receipt.error_message = "operation cancelled"
                raise
            except KompilerException as exc:
                receipt.status = "failed"
                receipt.error_code = exc.code
                receipt.error_message = exc.message
            except Exception as exc:
                receipt.status = "failed"
                receipt.error_code = "ADAPTER_FAILURE"
                receipt.error_message = str(exc)
            finally:
                receipt.completed_at = _utc()
                receipt.duration_ms = int((time.perf_counter() - t0) * 1000)

        try:
            for stage_index, stage in enumerate(plan.stages):
                await asyncio.gather(*(run_node(op_id) for op_id in stage))
                abort = any(
                    receipts[x].status == "failed"
                    and (plan.operations[x].operation.on_error or plan.query.execution.on_operation_error)
                    == "abort_run"
                    for x in stage
                )
                if abort:
                    for later in plan.stages[stage_index + 1 :]:
                        for op_id in later:
                            if receipts[op_id].status == "pending":
                                receipts[op_id].status = "skipped"
                                receipts[op_id].error_code = "RUN_ABORTED"
                                receipts[op_id].error_message = "run aborted by upstream failure"
                    break
        finally:
            self._cancelled.discard(run_id)

        completed = _utc()
        ordered = [receipts[op.id] for op in plan.query.operations]
        summary = ExecutionSummary(
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            duration_ms=int((completed - started).total_seconds() * 1000),
            receipts=ordered,
            config_hash=self.config.semantic_hash,
            query_hash=plan.query_hash,
            cache_hits=sum(1 for r in ordered if r.cache_hit),
        )
        return batches, raw_envelopes, summary
