from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kompiler.adapters import instantiate_detected
from kompiler.adapters.github_collection import GithubCollectionAdapter
from kompiler.compiler import compile_context_pack
from kompiler.config import AppConfig, load_config
from kompiler.errors import KompilerException, AdmissionError
from kompiler.executor import RunExecutor
from kompiler.kristal_standard import configure_standard_root
from kompiler.local_catalog import discovery_paths
from kompiler.planner import build_plan
from kompiler.protocol.canonical import prefixed_hash
from pydantic import ValidationError
from json import JSONDecodeError
from kompiler.protocol.models import ContextPack, ErrorArtifact, ErrorBody, QueryBudget, QueryPlan
from kompiler.registry import AdapterRegistry, discover
from kompiler.storage import SQLiteStore


class KompilerRuntime:
    def __init__(self, config: AppConfig, registry: AdapterRegistry, store: SQLiteStore | None) -> None:
        self.config=config; self.registry=registry; self.store=store; self.executor=RunExecutor(registry,config,store)

    @classmethod
    def create(cls, config_path: str | Path | None = None) -> "KompilerRuntime":
        config=load_config(config_path)
        configure_standard_root(config.standard.root, config.standard.contract_set_sha256)
        registry=AdapterRegistry.from_manifests(config.adapter_manifests)
        # Opt-in v11 sources are not public read surfaces. Never expose them on a
        # non-loopback API, even if another configuration enables remote access.
        if any(a.adapter_id == "kristal-v11-read-view" for a in registry.adapters()):
            if config.api.enabled and config.api.host not in {"127.0.0.1", "::1", "localhost"}:
                raise AdmissionError("V11_LOCAL_ONLY", "v11 local reader cannot be served on a non-loopback API")
        # Optional convenience roots: explicit env opt-in; detection does not execute source scripts.
        roots=os.getenv("KOMPILER_KRISTAL_ROOTS","")
        discover_roots=[Path(x) for x in roots.split(os.pathsep) if x]
        if config.manager.auto_discover:
            discover_roots.extend(discovery_paths(config.manager.catalog))
        if discover_roots:
            for item in discover(discover_roots):
                if item["target_id"] not in registry.targets:
                    registry.register(instantiate_detected(item["adapter_type"],Path(item["root"])))
        if config.github_collections:
            for source in dict.fromkeys(config.github_collections):
                if str(source).startswith("https://") and config.network_default != "allow":
                    raise AdmissionError("NETWORK_DENIED", "Enable runtime.network_default='allow' before auto-registering remote GitHub collections")
                adapter = GithubCollectionAdapter(source)
                if adapter.target_id not in registry.targets:
                    registry.register(adapter)
        store=SQLiteStore(config.storage.database)
        return cls(config,registry,store)

    def capabilities(self):
        return self.registry.snapshot()

    def close(self) -> None:
        if self.store:
            self.store.close()

    def plan(self, query: QueryPlan):
        return build_plan(query,self.registry,config=self.config)

    async def run(self, query: QueryPlan, run_id: str | None = None) -> ContextPack:
        actual_run_id=run_id or f"run:{uuid.uuid4()}"
        try:
            plan=self.plan(query)
            batches,raw,execution=await self.executor.execute(plan,run_id=actual_run_id)
            snapshot=self.registry.snapshot()
            provenance={
                "capability_snapshot_id":snapshot.snapshot_id,
                "targets":{t.target_id:{"adapter":t.adapter.model_dump(mode="json"),"source":t.source.model_dump(mode="json",exclude_none=True)} for t in snapshot.targets},
                "query_hash":plan.query_hash,
                "config_hash":self.config.semantic_hash,
            }
            budget=QueryBudget(
                max_items=min(query.budget.max_items or self.config.limits.max_items,self.config.limits.max_items),
                max_bytes=min(query.budget.max_bytes or self.config.limits.max_bytes,self.config.limits.max_bytes),
                target_tokens=min(query.budget.target_tokens or self.config.limits.max_target_tokens,self.config.limits.max_target_tokens),
                selection_mode=query.budget.selection_mode,
            )
            pack=compile_context_pack(query,batches,execution,provenance=provenance,operation_outputs=raw,effective_budget=budget)
            if self.store:
                retention=self.config.storage.retention
                artifact_id=None
                metadata={"summary":pack.summary.model_dump(mode="json"),"semantic_hash":pack.semantic_hash,"artifact_hash":pack.artifact_hash}
                if retention in {"packs","full"} and pack.artifact_hash:
                    artifact_id=pack.artifact_hash
                    self.store.put_artifact(artifact_id,"context-pack",pack.model_dump(by_alias=True,mode="json",exclude_none=True))
                if retention == "full":
                    raw_id=prefixed_hash("raw",{"request_id":query.request_id,"execution":execution.run_id,"outputs":raw})
                    self.store.put_artifact(raw_id,"operation-outputs",raw)
                    metadata["raw_artifact_id"]=raw_id
                if retention == "none":
                    metadata={}
                self.store.run_finish(execution.run_id,pack.status,pack.generated_at.isoformat(),pack.context_pack_id,artifact_id,metadata)
            return pack
        except asyncio.CancelledError:
            if self.store and self.store.get_run(actual_run_id):
                self.store.run_finish(actual_run_id,"cancelled",datetime.now(timezone.utc).isoformat(),None,None,{} if self.config.storage.retention=="none" else {"cancelled":True})
            raise
        except Exception as exc:
            if self.store and self.store.get_run(actual_run_id):
                metadata={} if self.config.storage.retention=="none" else {"error":error_artifact(exc,query.request_id).model_dump(mode="json",exclude_none=True)}
                self.store.run_finish(actual_run_id,"failed",datetime.now(timezone.utc).isoformat(),None,None,metadata)
            raise


def error_artifact(exc: Exception, request_id: str | None = None) -> ErrorArtifact:
    if isinstance(exc,KompilerException):
        body=ErrorBody(code=exc.code,message=exc.message,operation_id=exc.operation_id,retryable=exc.retryable,details=exc.details)
    elif isinstance(exc, ValidationError):
        body=ErrorBody(code="SCHEMA_VIOLATION",message="Protocol artifact failed model validation",retryable=False,details={"errors":[{"path":".".join(str(x) for x in e["loc"]),"message":e["msg"],"type":e["type"]} for e in exc.errors()]})
    elif isinstance(exc, JSONDecodeError):
        body=ErrorBody(code="INVALID_JSON",message=str(exc),retryable=False)
    else:
        body=ErrorBody(code="COMPILATION_FAILURE",message=str(exc),retryable=False)
    return ErrorArtifact(request_id=request_id,error=body)
