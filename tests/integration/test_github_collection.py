from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kompiler.adapters.github_collection import GithubCollectionAdapter
from kompiler.cli.app import app
from kompiler.errors import AdapterError
from kompiler.github_collection import CollectionReader, _sha
from kompiler.protocol.canonical import canonical_bytes
from kompiler.registry import discover


def fixture_collection(root: Path, count: int = 1) -> Path:
    rows = []
    for k in range(count):
        slug = f"demo-{k:04}"
        base = root / "kristals" / slug
        (base / "ai").mkdir(parents=True)
        (base / "state").mkdir(parents=True)
        (base / ".kristal").mkdir(parents=True)
        state_ref = f"urn:kristal:state:{slug}"
        c = {"profile": "kristal.state-commitment/jcs-sha256-v1", "digest": "sha256:" + "0" * 64}
        state = {"schema_version":"9.0", "artifact_type":"kristal_state_snapshot", "state_ref":state_ref, "logical_commitment":c,"members":[],"references":[]}
        (base / "state/state-snapshot.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
        (base / "README.md").write_text(f"# Biology {slug}\n", encoding="utf-8")
        (base / "AI_START_HERE.md").write_text("# AI Entry\nRead ai/INDEX.json.\n", encoding="utf-8")
        (base / "AI_MANIFEST.json").write_text(json.dumps({"state_ref":state_ref,"state_logical_commitment":c}) + "\n", encoding="utf-8")
        def row(rel: str, role: str) -> dict:
            data=(base/rel).read_bytes()
            return {"path":rel,"role":role,"size":len(data),"sha256":_sha(data)}
        ai_idx = {"state_ref":state_ref,"state_logical_commitment":c,"files":[row("README.md","overview"),row("state/state-snapshot.json","state_snapshot")],"materialization_blobs":[]}
        (base / "ai/INDEX.json").write_text(json.dumps(ai_idx) + "\n", encoding="utf-8")
        specs=[("README.md","overview"),("AI_START_HERE.md","ai_entrypoint"),("AI_MANIFEST.json","ai_manifest"),("ai/INDEX.json","ai_index"),("state/state-snapshot.json","state_snapshot")]
        files=[row(rel,role) for rel,role in specs]
        files.sort(key=lambda x:x["path"].encode("utf-8"))
        projection={"format":"kristal.github-read-surface/1.0","slug":slug,"state_ref":state_ref,"state_logical_commitment":c,"entrypoint":"AI_START_HERE.md","files":files,"materialization_objects":[]}
        digest=_sha(canonical_bytes(projection))
        manifest={"format":"kristal.github-sync-manifest/1.0","read_surface_format":"kristal.github-read-surface/1.0","target_root":f"kristals/{slug}","slug":slug,"entrypoint":"AI_START_HERE.md","state_ref":state_ref,"state_logical_commitment":c,"surface_digest":digest,"files":files,"file_count":len(files),"total_bytes":sum(x["size"] for x in files),"materialization_object_count":0}
        (base / ".kristal/sync-manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        rows.append({"slug":slug,"title":f"Biology {slug}","path":f"kristals/{slug}","entrypoint":f"kristals/{slug}/AI_START_HERE.md","state_ref":state_ref,"state_logical_commitment":c,"surface_digest":digest,"file_count":len(files),"total_bytes":manifest["total_bytes"],"materialization_object_count":0})
    index={"format":"kristal.github-collection-index/1.0","kristals":rows}
    raw=json.dumps(index,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()
    index.update({"count":len(rows),"index_digest":_sha(raw)})
    (root/"kristals/index.json").write_text(json.dumps(index) + "\n",encoding="utf-8")
    return root


def test_local_collection_index_first_and_verified_read(tmp_path):
    root=fixture_collection(tmp_path, count=80)
    reader=CollectionReader(root)
    assert reader.catalog(query="Biology demo-007",limit=5)["count"]==10
    assert len(reader.catalog(limit=7)["entries"])==7
    assert reader._manifests=={}
    doc=reader.read("demo-0000","AI_START_HERE.md")
    assert "Read ai/INDEX" in doc["content"]
    assert doc["state_ref"] == "urn:kristal:state:demo-0000"
    assert reader.reading_map("demo-0000")["file_count"]==5
    assert len(reader._manifests)==1
    hits=discover([root]); assert hits[0]["adapter_type"]=="kristal-github-collection"


def test_reject_tampered_file_and_surface(tmp_path):
    root=fixture_collection(tmp_path)
    reader=CollectionReader(root)
    reader.manifest("demo-0000")
    path=root/"kristals/demo-0000/AI_START_HERE.md"
    path.write_text("# tampered\n")
    with pytest.raises(AdapterError,match="DIGEST_MISMATCH"):
        reader.read("demo-0000","AI_START_HERE.md")
    root=fixture_collection(tmp_path/"new")
    manifest=root/"kristals/demo-0000/.kristal/sync-manifest.json"
    m=json.loads(manifest.read_text());m["surface_digest"]="sha256:"+"a"*64
    manifest.write_text(json.dumps(m))
    with pytest.raises(AdapterError):
        CollectionReader(root).manifest("demo-0000")


def test_reject_traversal_and_undeclared(tmp_path):
    reader=CollectionReader(fixture_collection(tmp_path))
    for path in ("../../secrets.txt","/etc/passwd","ai/../state/state-snapshot.json",".\\secret"):
        with pytest.raises(AdapterError):
            reader.read("demo-0000",path)
    with pytest.raises(AdapterError,match="UNDECLARED_RESOURCE"):
        reader.read("demo-0000","unlisted.txt")


def test_cli_read_and_adapter(tmp_path):
    root=fixture_collection(tmp_path)
    cli=CliRunner().invoke(app,["github","read",str(root),"demo-0000"])
    assert cli.exit_code==0,cli.output
    assert "AI Entry" in cli.stdout
    adapter=GithubCollectionAdapter(root)
    assert {c.operation_id for c in adapter.capabilities()}=={"catalog","files","read","entrypoint"}
    assert all(not c.semantics.network for c in adapter.capabilities())


def test_remote_pins_commit_and_never_downloads_entire_collection(tmp_path, monkeypatch):
    root=fixture_collection(tmp_path, count=4)
    sha="a"*40
    calls=[]
    monkeypatch.setattr("kompiler.github_collection.shutil.which",lambda name:"/fake/gh")
    def mock_run(cmd,**kwargs):
        endpoint=cmd[-1];calls.append(endpoint)
        if "/commits/" in endpoint:
            doc={"sha":sha}
        elif "/contents/" in endpoint:
            from urllib.parse import unquote
            relative=unquote(endpoint.split("/contents/",1)[1].split("?ref=",1)[0])
            assert endpoint.endswith("?ref="+sha)
            data=(root/relative).read_bytes()
            doc={"type":"file","encoding":"base64","size":len(data),"content":base64.b64encode(data).decode()}
        else:
            raise AssertionError(endpoint)
        return subprocess.CompletedProcess(cmd,0,json.dumps(doc),"")
    monkeypatch.setattr("kompiler.github_collection.subprocess.run", mock_run)
    reader=CollectionReader("https://github.com/acme/kristal-public")
    assert reader.source_uri.endswith("/tree/"+sha)
    assert reader.catalog()["count"]==4
    assert len(calls)==2  # one commit resolution and one collection index
    assert reader.read("demo-0002","README.md")["content"].startswith("# Biology")
    assert len(calls) < 9
    assert all("?ref="+sha in c for c in calls if "/contents/" in c)


def test_remote_url_rejects_non_github_and_missing_ref(tmp_path):
    for url in ("http://github.com/a/b", "https://evil.com/a/b", "https://github.com/a", "https://foo@github.com/a/b", "https://github.com/a/b?x=1"):
        with pytest.raises(AdapterError): CollectionReader(url)


def test_remote_autodiscovery_denied_by_default(tmp_path, monkeypatch):
    from kompiler.config import AppConfig, StorageConfig
    from kompiler.runtime import KompilerRuntime
    from kompiler.errors import AdmissionError
    from kompiler.adapters.github_collection import GithubCollectionAdapter
    monkeypatch.setattr("kompiler.runtime.GithubCollectionAdapter",lambda src: (_ for _ in ()).throw(AssertionError("network invoked before policy check")))
    cfg=AppConfig(github_collections=["https://github.com/acme/kristal-public"],storage=StorageConfig(database=tmp_path/"test.db"))
    with pytest.raises(AdmissionError,match="NETWORK_DENIED"):
        monkeypatch.setattr("kompiler.runtime.load_config",lambda _:cfg)
        KompilerRuntime.create()


def test_framework_draft3_uses_verified_snapshot_pin_or_explicit_override(tmp_path, monkeypatch):
    from kompiler.errors import StandardError
    from kompiler.kristal_standard import KristalStandard, configure_standard_root
    base=tmp_path/"framework"
    (base/"contracts").mkdir(parents=True)
    for version in ("v7","v8","v9","v10"):
        (base/"schemas"/version).mkdir(parents=True)
    (base/"schemas/v6").mkdir(parents=True)
    (base/"schemas/v6/kristal-state.schema.json").write_text("{}")
    (base/"contracts/release.json").write_text(json.dumps({"version":"10.0.0-draft.3","semantic_baseline":{"schema_root":"schemas/v7"}}))
    contract=b'{"format":"example","version":"10.0.0-draft.3"}\n'
    (base/"contracts/contract-set.json").write_bytes(contract)
    monkeypatch.delenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256",raising=False)
    configure_standard_root(None)
    # A draft.3 source with a different contract set must be rejected against
    # the bundled exact snapshot pin, not trusted by version name alone.
    with pytest.raises(StandardError,match="MISMATCH"):
        KristalStandard.load(base)
    correct=hashlib.sha256(contract).hexdigest()
    monkeypatch.setenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256","0"*64)
    with pytest.raises(StandardError,match="MISMATCH"):
        KristalStandard.load(base)
    monkeypatch.setenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256",correct)
    loaded=KristalStandard.load(base)
    assert loaded.version=="10.0.0-draft.3"
    assert loaded.describe()["framework_commit"] is None
    assert loaded.describe()["contract_set_sha256"]==correct
    monkeypatch.delenv("KOMPILER_KRISTAL_CONTRACT_SET_SHA256",raising=False)


@pytest.mark.asyncio
async def test_verified_collection_records_compile_to_context_pack(tmp_path):
    from kompiler.config import AppConfig, StorageConfig
    from kompiler.registry import AdapterRegistry
    from kompiler.runtime import KompilerRuntime
    from kompiler.protocol.models import QueryPlan

    root=fixture_collection(tmp_path, count=20)
    adapter=GithubCollectionAdapter(root)
    reg=AdapterRegistry(); reg.register(adapter)
    rt=KompilerRuntime(AppConfig(storage=StorageConfig(database=root/'cache.db',cache=False)),reg,None)
    q=QueryPlan.model_validate({
        'request_id':'read-github-index-and-entrypoint', 'topic':'biology',
        'operations':[
            {'id':'find','target':adapter.target_id,'operation':'catalog','params':{'query':'demo-0001','limit':5}},
            {'id':'context','target':adapter.target_id,'operation':'entrypoint','params':{'slug':'demo-0001'}},
        ],
    })
    pack=await rt.run(q)
    assert pack.summary.record_count==2
    assert all(receipt.status=='success' for receipt in pack.execution.receipts)
    assert pack.protocol=='kompiler.context-pack'
    # Exercise the opt-in selector through the complete runtime and pack path,
    # not only as an isolated budgeting helper.
    lexical_q=q.model_copy(deep=True)
    lexical_q.request_id='read-github-lexical'
    lexical_q.budget.selection_mode='lexical'
    lexical_q.budget.max_items=1
    lexical_pack=await rt.run(lexical_q)
    assert lexical_pack.summary.record_count==1
    assert lexical_pack.summary.truncated
    assert lexical_pack.execution.query_hash != pack.execution.query_hash
