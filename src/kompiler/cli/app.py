from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from kompiler.adapters import detect_builtin
from kompiler.github_collection import CollectionReader
from kompiler.config import load_config
from kompiler.errors import AdapterError, AdmissionError, CompilationError, PolicyError
from kompiler.protocol.io import dump_json, load_json, load_model
from kompiler.protocol.models import ContextPack, QueryPlan
from kompiler.kristall import materialize_v6_projection
from kompiler.local_catalog import local_entries, load_local_catalog
from kompiler.registry import discover
from kompiler.runtime import KompilerRuntime, error_artifact

app=typer.Typer(help="Compile structured Kristal knowledge into LLM-ready context packs.",no_args_is_help=True)
adapters_app=typer.Typer(help="Inspect and configure Kristal adapters.")
cache_app=typer.Typer(help="Inspect or clear the local operation cache.")
github_app=typer.Typer(help="Read an indexed GitHub Kristal collection; requires gh auth for remote URLs.")
app.add_typer(adapters_app,name="adapters"); app.add_typer(cache_app,name="cache"); app.add_typer(github_app,name="github")
console=Console(stderr=True)


def _exit_code(exc: Exception) -> int:
    if isinstance(exc, (ValidationError, AdmissionError, json.JSONDecodeError)):
        return 2
    if isinstance(exc, PolicyError):
        return 6
    if isinstance(exc, CompilationError):
        return 5
    if isinstance(exc, AdapterError):
        return 4 if exc.code in {"TIMEOUT", "RESOURCE_LIMIT_EXCEEDED"} else 3
    if isinstance(exc, KeyboardInterrupt):
        return 130
    return 3


def _runtime(config: str | None) -> KompilerRuntime:
    return KompilerRuntime.create(config)


def _emit(value: Any, output: Path | None=None, machine: bool=True) -> None:
    text=dump_json(value,output,pretty=True)
    if output is None: typer.echo(text)
    elif not machine: console.print(f"wrote {output}")


@app.command()
def capabilities(
    json_output: Annotated[bool,typer.Option("--json",help="Emit protocol JSON to stdout.")]=False,
    output: Annotated[Path|None,typer.Option("--output","-o")]=None,
    config: Annotated[str|None,typer.Option("--config")]=None,
):
    rt=_runtime(config); snap=rt.capabilities()
    if json_output or output: _emit(snap,output)
    else:
        table=Table(title=f"Kompiler capabilities — {snap.snapshot_id}")
        table.add_column("Target");table.add_column("Adapter");table.add_column("Source");table.add_column("Operations")
        for t in snap.targets: table.add_row(t.target_id,f"{t.adapter.id}@{t.adapter.version}",t.source.state_id or "unknown",", ".join(o.operation_id for o in t.operations))
        console.print(table)


@app.command("validate")
def validate_cmd(
    path: Path,
    config: Annotated[str|None,typer.Option("--config")]=None,
):
    try:
        query=load_model(path,QueryPlan)
        plan=_runtime(config).plan(query)
        typer.echo(json.dumps({"valid":True,"protocol":query.protocol,"version":query.version,"request_id":query.request_id,"query_hash":plan.query_hash,"stages":plan.stages},indent=2))
    except Exception as exc:
        art=error_artifact(exc)
        typer.echo(dump_json(art)); raise typer.Exit(_exit_code(exc))


@app.command()
def plan(path: Path, config: Annotated[str|None,typer.Option("--config")]=None):
    try:
        rt=_runtime(config); query=load_model(path,QueryPlan); p=rt.plan(query)
        payload={"request_id":query.request_id,"query_hash":p.query_hash,"stages":p.stages,"operations":{k:{"target":v.operation.target,"operation":v.operation.operation,"dependencies":sorted(v.dependencies),"stage":v.stage} for k,v in p.operations.items()}}
        typer.echo(json.dumps(payload,ensure_ascii=False,indent=2))
    except Exception as exc:
        typer.echo(dump_json(error_artifact(exc))); raise typer.Exit(_exit_code(exc))


@app.command()
def run(
    path: Path,
    output: Annotated[Path|None,typer.Option("--output","-o")]=None,
    json_output: Annotated[bool,typer.Option("--json")]=False,
    config: Annotated[str|None,typer.Option("--config")]=None,
):
    request_id=None
    try:
        query=load_model(path,QueryPlan); request_id=query.request_id
        pack=asyncio.run(_runtime(config).run(query))
        _emit(pack,output,machine=json_output)
    except Exception as exc:
        art=error_artifact(exc,request_id)
        _emit(art,output)
        raise typer.Exit(_exit_code(exc))


@app.command()
def inspect(
    path: Path,
    reproducibility: Annotated[bool,typer.Option("--reproducibility")]=False,
):
    data=load_json(path); pack=ContextPack.model_validate(data)
    if reproducibility:
        payload={"context_pack_id":pack.context_pack_id,"semantic_hash":pack.semantic_hash,"artifact_hash":pack.artifact_hash,"query_hash":pack.execution.query_hash,"config_hash":pack.execution.config_hash,"cache_hits":pack.execution.cache_hits,"truncated":pack.summary.truncated,"sources":[{"source_id":x.source_id,"state_id":x.source_state_id} for x in pack.sources],"deterministic_expected":all(r.status=="success" for r in pack.execution.receipts)}
        typer.echo(json.dumps(payload,ensure_ascii=False,indent=2)); return
    table=Table(title=pack.context_pack_id); table.add_column("Metric");table.add_column("Value")
    for k,v in pack.summary.model_dump().items(): table.add_row(k,json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else str(v))
    console.print(table)


@app.command("project-v6")
def project_v6(
    path: Path,
    output: Annotated[Path|None,typer.Option("--output","-o")]=None,
    surface_id: Annotated[str|None,typer.Option("--surface-id")]=None,
    recipe_id: Annotated[str,typer.Option("--recipe-id")]="recipe:kompiler-adhoc",
):
    """Materialize one v7 Surface as a v6-compatible kristal_state projection."""
    try:
        pack=load_model(path,ContextPack)
        artifact=materialize_v6_projection(pack,surface_id=surface_id,recipe_id=recipe_id)
        _emit(artifact,output)
    except Exception as exc:
        _emit(error_artifact(exc))
        raise typer.Exit(_exit_code(exc))


@adapters_app.command("list")
def adapters_list(config: Annotated[str|None,typer.Option("--config")]=None):
    rt=_runtime(config)
    typer.echo(json.dumps([{"target_id":a.target_id,"adapter_id":a.adapter_id,"version":a.adapter_version,"root":str(a.root)} for a in rt.registry.adapters()],ensure_ascii=False,indent=2))


@adapters_app.command("doctor")
def adapters_doctor(config: Annotated[str|None,typer.Option("--config")]=None):
    rt=_runtime(config); rows=[]; failed=False
    for a in rt.registry.adapters():
        h=a.health(); failed=failed or not h.get("ok",False); rows.append({"target_id":a.target_id,**h,"operations":[x.operation_id for x in a.capabilities()]})
    typer.echo(json.dumps(rows,ensure_ascii=False,indent=2));
    if failed: raise typer.Exit(3)


@adapters_app.command("discover")
def adapters_discover(paths: list[Path]):
    typer.echo(json.dumps(discover(paths),ensure_ascii=False,indent=2))


@adapters_app.command("bootstrap")
def adapters_bootstrap(
    paths: list[Path],
    output_dir: Annotated[Path,typer.Option("--output-dir")]=Path.home()/".config/kompiler/adapters",
    fragment: Annotated[Path|None,typer.Option("--config-fragment")]=None,
):
    """Detect supported Kristals and write trusted adapter manifests plus a config fragment."""
    hits=discover(paths)
    if not hits:
        console.print("No supported Kristals detected."); raise typer.Exit(3)
    output_dir=output_dir.expanduser(); output_dir.mkdir(parents=True,exist_ok=True)
    lines=[]; written=[]
    for item in hits:
        target=item["target_id"]; kind=item["adapter_type"]; root=item["root"]
        name=re.sub(r"[^a-z0-9._-]+", "-", target.lower()).strip("-")
        mpath=output_dir/f"{name}.toml"
        target_kind="kristall" if kind == "kristall-v7" else "kristal"
        text=f'id = "{kind}"\nversion = "1.0.0"\ntarget_id = "{target}"\nkind = "{target_kind}"\n\n[source]\nroot = "{Path(root).as_posix()}"\n\n[implementation]\ntype = "{kind}"\n'
        mpath.write_text(text,encoding="utf-8")
        lines += [f"[adapters.{name}]",f'manifest = "{mpath.as_posix()}"',""]
        written.append(str(mpath))
    frag=fragment or output_dir.parent/"adapters.generated.toml"
    frag.write_text("\n".join(lines),encoding="utf-8")
    typer.echo(json.dumps({"detected":len(hits),"manifests":written,"config_fragment":str(frag)},ensure_ascii=False,indent=2))


@adapters_app.command("manifest")
def adapters_manifest(
    root: Path,
    output: Annotated[Path|None,typer.Option("--output","-o")]=None,
):
    hit=detect_builtin(root)
    if not hit:
        console.print("No supported built-in Kristal signature detected."); raise typer.Exit(3)
    kind,kroot,target=hit
    target_kind="kristall" if kind == "kristall-v7" else "kristal"
    text=f'''id = "{kind}"\nversion = "1.0.0"\ntarget_id = "{target}"\nkind = "{target_kind}"\n\n[source]\nroot = "{kroot.as_posix()}"\n\n[implementation]\ntype = "{kind}"\n'''
    if output: output.parent.mkdir(parents=True,exist_ok=True); output.write_text(text,encoding="utf-8"); console.print(f"wrote {output}")
    else: typer.echo(text)


@cache_app.command("stats")
def cache_stats(config: Annotated[str|None,typer.Option("--config")]=None):
    rt=_runtime(config); typer.echo(json.dumps(rt.store.cache_stats() if rt.store else {"entries":0,"bytes":0},indent=2))


@cache_app.command("clear")
def cache_clear(config: Annotated[str|None,typer.Option("--config")]=None):
    rt=_runtime(config); n=rt.store.cache_clear() if rt.store else 0; typer.echo(json.dumps({"cleared":n},indent=2))


@app.command("locals")
def locals_cmd(
    catalog: Annotated[Path|None,typer.Option("--catalog",help="Kristal Manager kristal-manager.json path")]=None,
    discover_adapters: Annotated[bool,typer.Option("--discover-adapters",help="Also show which entries Kompiler can read directly")]=False,
):
    """Inspect Kristal Manager local inventory without taking management authority."""
    try:
        data=load_local_catalog(catalog)
        rows=local_entries(catalog)
        payload={"catalog":data.get("path"),"format":data.get("format"),"count":len(rows),"entries":rows}
        if discover_adapters:
            hits=discover([Path(r["path"]) for r in rows])
            payload["adapters"]=hits
        typer.echo(json.dumps(payload,ensure_ascii=False,indent=2))
    except Exception as exc:
        typer.echo(dump_json(error_artifact(exc))); raise typer.Exit(_exit_code(exc))


@github_app.command("catalog")
def github_catalog(
    source: str,
    query: Annotated[str, typer.Option("--query", "-q")] = "",
    limit: Annotated[int, typer.Option("--limit", min=1, max=200)] = 50,
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
):
    """Search collection index without downloading all Kristals."""
    try:
        reader = CollectionReader(source)
        _emit(reader.catalog(query=query, limit=limit, offset=offset))
    except Exception as exc:
        _emit(error_artifact(exc)); raise typer.Exit(_exit_code(exc))


@github_app.command("files")
def github_files(source: str, slug: str, limit: Annotated[int, typer.Option("--limit", min=1, max=500)] = 100):
    """Show verified file/digest map for a single hosted Kristal."""
    try:
        _emit(CollectionReader(source).reading_map(slug, limit=limit))
    except Exception as exc:
        _emit(error_artifact(exc)); raise typer.Exit(_exit_code(exc))


@github_app.command("read")
def github_read(source: str, slug: str, path: str = "AI_START_HERE.md"):
    """Fetch one declared file; always verify its exact bytes and digest."""
    try:
        _emit(CollectionReader(source).read(slug, path))
    except Exception as exc:
        _emit(error_artifact(exc)); raise typer.Exit(_exit_code(exc))


@app.command("self-test")
def self_test():
    """Run a deterministic end-to-end synthetic compilation."""
    import tempfile
    from kompiler.adapters.selftest import SelfTestAdapter
    from kompiler.config import AppConfig, StorageConfig
    from kompiler.registry import AdapterRegistry
    from kompiler.storage import SQLiteStore
    reg=AdapterRegistry(); reg.register(SelfTestAdapter())
    with tempfile.TemporaryDirectory() as td:
        cfg=AppConfig(storage=StorageConfig(database=Path(td)/"selftest.db",cache=True))
        rt=KompilerRuntime(cfg,reg,SQLiteStore(cfg.storage.database))
        q=QueryPlan.model_validate({"request_id":"self-test","topic":"kompiler","operations":[{"id":"facts","target":"SelfTest","operation":"facts","params":{"topic":"kompiler"}}]})
        pack=asyncio.run(rt.run(q))
        typer.echo(dump_json({"ok":pack.summary.record_count==2,"context_pack_id":pack.context_pack_id,"records":pack.summary.record_count,"conflicts":pack.summary.conflict_count,"gaps":pack.summary.gap_count}))


@app.command()
def serve(
    host: Annotated[str|None,typer.Option("--host")]=None,
    port: Annotated[int|None,typer.Option("--port")]=None,
    config: Annotated[str|None,typer.Option("--config")]=None,
):
    try: import uvicorn
    except ImportError as exc: raise typer.BadParameter("Install kompiler[api] to use the local API") from exc
    import os
    if config: os.environ["KOMPILER_CONFIG"]=config
    cfg=load_config(config)
    h=host or cfg.api.host; p=port or cfg.api.port
    if h not in {"127.0.0.1","localhost","::1"} and not cfg.api.bearer_token:
        raise typer.BadParameter("Non-loopback binding requires KOMPILER_API_TOKEN or api.bearer_token")
    uvicorn.run("kompiler.api.app:create_app",host=h,port=p,factory=True,reload=False)


if __name__=="__main__": app()
