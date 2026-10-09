from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from kompiler.protocol.models import ContextPack, QueryPlan
from kompiler.kristall import materialize_v6_projection
from kompiler.errors import AdmissionError, CompilationError, PolicyError
from kompiler.runtime import KompilerRuntime, error_artifact


class RunManager:
    def __init__(self, runtime: KompilerRuntime) -> None:
        self.runtime=runtime
        self.tasks: dict[str,asyncio.Task]= {}
        self.results: dict[str,dict[str,Any]]={}

    async def _execute(self,run_id:str,query:QueryPlan)->None:
        self.results[run_id]={"run_id":run_id,"status":"running","request_id":query.request_id}
        try:
            pack=await self.runtime.run(query,run_id=run_id)
            self.results[run_id]={"run_id":run_id,"status":"completed","request_id":query.request_id,"context_pack_id":pack.context_pack_id,"context_pack":pack.model_dump(by_alias=True,mode="json",exclude_none=True)}
        except asyncio.CancelledError:
            self.runtime.executor.cancel(run_id)
            self.results[run_id]={"run_id":run_id,"status":"cancelled","request_id":query.request_id}
        except Exception as exc:
            self.results[run_id]={"run_id":run_id,"status":"failed","request_id":query.request_id,"error":error_artifact(exc,query.request_id).model_dump(mode="json",exclude_none=True)}

    def start(self,query:QueryPlan)->str:
        run_id=f"run:{uuid.uuid4()}"
        task=asyncio.create_task(self._execute(run_id,query))
        self.tasks[run_id]=task
        task.add_done_callback(lambda _task,rid=run_id:self.tasks.pop(rid,None))
        return run_id

    def cancel(self,run_id:str)->bool:
        task=self.tasks.get(run_id)
        if not task: return False
        self.runtime.executor.cancel(run_id); task.cancel(); return True


def create_app(runtime: KompilerRuntime | None = None) -> FastAPI:
    runtime=runtime or KompilerRuntime.create()
    manager=RunManager(runtime)
    app=FastAPI(title="Kompiler Local API",version="1.1",docs_url="/docs",redoc_url=None)
    app.add_event_handler("shutdown", runtime.close)
    if runtime.config.api.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=runtime.config.api.cors_origins, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Authorization","Content-Type"])

    async def auth(authorization: str | None = Header(default=None)) -> None:
        token=runtime.config.api.bearer_token
        if not token: return
        if authorization != f"Bearer {token}": raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="invalid local API token")

    @app.get("/health")
    async def health(_:None=Depends(auth)):
        return {"ok":True,"targets":runtime.registry.targets}

    @app.get("/v1/capabilities")
    async def capabilities(_:None=Depends(auth)):
        return runtime.capabilities().model_dump(by_alias=True,mode="json",exclude_none=True)

    @app.post("/v1/queries/validate")
    async def validate_query(body:dict[str,Any],_:None=Depends(auth)):
        try:
            query=QueryPlan.model_validate(body); plan=runtime.plan(query)
            return {"valid":True,"request_id":query.request_id,"query_hash":plan.query_hash,"stages":plan.stages}
        except Exception as exc:
            return JSONResponse(status_code=422,content=error_artifact(exc,body.get("request_id") if isinstance(body,dict) else None).model_dump(mode="json",exclude_none=True))

    @app.post("/v1/runs")
    async def start_run(body:dict[str,Any],async_mode:bool=Query(default=False),_:None=Depends(auth)):
        try: query=QueryPlan.model_validate(body)
        except Exception as exc: return JSONResponse(status_code=422,content=error_artifact(exc,body.get("request_id") if isinstance(body,dict) else None).model_dump(mode="json",exclude_none=True))
        if not async_mode:
            try:
                pack=await runtime.run(query)
                return pack.model_dump(by_alias=True,mode="json",exclude_none=True)
            except Exception as exc:
                code=(
                    422 if isinstance(exc,AdmissionError)
                    else 403 if isinstance(exc,PolicyError)
                    else 413 if isinstance(exc,CompilationError) and exc.code == "BUDGET_IMPOSSIBLE"
                    else 500 if isinstance(exc,CompilationError)
                    else 500
                )
                return JSONResponse(status_code=code,content=error_artifact(exc,query.request_id).model_dump(mode="json",exclude_none=True))
        run_id=manager.start(query); return {"run_id":run_id,"status":"accepted"}

    @app.get("/v1/runs/{run_id}")
    async def run_state(run_id:str,_:None=Depends(auth)):
        state=manager.results.get(run_id) or (runtime.store.get_run(run_id) if runtime.store else None)
        if not state: raise HTTPException(status_code=404,detail="run not found")
        clean=dict(state); clean.pop("context_pack",None); return clean

    @app.get("/v1/runs/{run_id}/context-pack")
    async def run_pack(run_id:str,_:None=Depends(auth)):
        state=manager.results.get(run_id)
        if state and state.get("context_pack"): return state["context_pack"]
        stored=runtime.store.get_run(run_id) if runtime.store else None
        if stored and stored.get("artifact_id"):
            art=runtime.store.get_artifact(stored["artifact_id"]); 
            if art: return art
        raise HTTPException(status_code=404,detail="context pack not available")

    @app.post("/v1/runs/{run_id}/cancel")
    async def cancel_run(run_id:str,_:None=Depends(auth)):
        if not manager.cancel(run_id): raise HTTPException(status_code=404,detail="active run not found")
        return {"run_id":run_id,"status":"cancellation_requested"}

    @app.post("/v1/projections/v6")
    async def project_v6(body:dict[str,Any],_:None=Depends(auth)):
        try:
            pack=ContextPack.model_validate(body.get("context_pack"))
            artifact=materialize_v6_projection(
                pack,
                surface_id=body.get("surface_id"),
                recipe_id=body.get("recipe_id") or "recipe:kompiler-adhoc",
            )
            return artifact
        except Exception as exc:
            return JSONResponse(
                status_code=422,
                content=error_artifact(exc).model_dump(mode="json",exclude_none=True),
            )

    @app.get("/v1/cache/stats")
    async def cache_stats(_:None=Depends(auth)):
        return runtime.store.cache_stats() if runtime.store else {"entries":0,"bytes":0}

    return app
