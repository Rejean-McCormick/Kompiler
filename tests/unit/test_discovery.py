from kompiler.registry import discover


def test_recursive_discovery_is_bounded_but_finds_nested_kristal(tmp_path):
    root = tmp_path / "wrapper" / "release" / "Kristal-Recipes" / "knowledge-base"
    (root / "corpus").mkdir(parents=True)
    (root / "corpus" / "classification-index.json").write_text("{}")
    (root / "corpus" / "search-documents.json").write_text("{}")
    hits = discover([tmp_path])
    assert any(x["target_id"] == "Recipes" for x in hits)


def test_discovery_prefers_v9_state_snapshot(tmp_path):
    root=tmp_path/'Kristal-X'/'.kristal'/'v9';root.mkdir(parents=True)
    (root/'state-snapshot.json').write_text('{"schema_version":"9.0","artifact_type":"kristal_state_snapshot","state_ref":"urn:test","logical_commitment":{"profile":"kristal.state-commitment/jcs-sha256-v1","digest":"sha256:0000000000000000000000000000000000000000000000000000000000000000"},"members":[],"references":[]}',encoding='utf-8')
    hits=discover([tmp_path])
    assert any(x['adapter_type']=='kristal-v9-state' for x in hits)


def _minimal_v9_state(ref: str, digest_char: str = "0") -> str:
    import json
    return json.dumps({
        "schema_version": "9.0",
        "artifact_type": "kristal_state_snapshot",
        "state_ref": ref,
        "logical_commitment": {
            "profile": "kristal.state-commitment/jcs-sha256-v1",
            "digest": "sha256:" + digest_char * 64,
        },
        "members": [],
        "references": [],
    })


def test_discovery_reads_local_kit_32_build_v9(tmp_path):
    workspace = tmp_path / "Mon-Kristal"
    state = workspace / "build" / "v9" / "state-snapshot.json"
    state.parent.mkdir(parents=True)
    (workspace / "kristal.workspace.json").write_text(
        '{"format":"kristal.local-workspace/3.2.0","slug":"mon-kristal"}',
        encoding="utf-8",
    )
    state.write_text(_minimal_v9_state("urn:kristal:state:mon-kristal"), encoding="utf-8")
    hits = discover([workspace])
    assert hits == [{
        "adapter_type": "kristal-v9-state",
        "root": str(workspace.resolve()),
        "target_id": "KristalV9:urn:kristal:state:mon-kristal",
    }]


def test_discovery_reads_local_kit_32_portable_state_when_build_absent(tmp_path):
    workspace = tmp_path / "Mon-Kristal"
    state = workspace / "state" / "state-snapshot.json"
    state.parent.mkdir(parents=True)
    (workspace / "kristal.workspace.json").write_text(
        '{"format":"kristal.local-workspace/3.2.0","slug":"mon-kristal"}',
        encoding="utf-8",
    )
    state.write_text(_minimal_v9_state("urn:kristal:state:mon-kristal"), encoding="utf-8")
    hits = discover([workspace])
    assert any(x["root"] == str(workspace.resolve()) for x in hits)


def test_local_kit_build_v9_wins_over_ai_mirror(tmp_path):
    from kompiler.adapters.kristal_v9 import find_v9_state_candidates

    workspace = tmp_path / "Mon-Kristal"
    (workspace / "kristal.workspace.json").parent.mkdir(parents=True)
    (workspace / "kristal.workspace.json").write_text(
        '{"format":"kristal.local-workspace/3.2.0"}', encoding="utf-8"
    )
    build = workspace / "build" / "v9" / "state-snapshot.json"
    mirror = workspace / "state" / "state-snapshot.json"
    build.parent.mkdir(parents=True)
    mirror.parent.mkdir(parents=True)
    build.write_text(_minimal_v9_state("urn:kristal:state:current", "1"), encoding="utf-8")
    mirror.write_text(_minimal_v9_state("urn:kristal:state:mirror", "2"), encoding="utf-8")
    candidates = find_v9_state_candidates(workspace)
    assert [c.surface for c in candidates[:2]] == ["build-v9", "portable-ai-state"]
    assert candidates[0].path == build.resolve()


def test_multiple_historical_releases_are_not_silently_treated_as_latest(tmp_path):
    from kompiler.adapters.kristal_v9 import find_v9_state

    workspace = tmp_path / "Mon-Kristal"
    workspace.mkdir()
    (workspace / "kristal.workspace.json").write_text(
        '{"format":"kristal.local-workspace/3.2.0"}', encoding="utf-8"
    )
    for i in ("a", "b"):
        state = workspace / "release" / "v9" / "states" / i / i / "state-snapshot.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(_minimal_v9_state(f"urn:kristal:state:{i}", i), encoding="utf-8")
    assert find_v9_state(workspace) is None


def test_exact_release_directory_is_readable_even_when_workspace_has_history(tmp_path):
    from kompiler.adapters.kristal_v9 import find_v9_state

    workspace = tmp_path / "Mon-Kristal"
    workspace.mkdir()
    (workspace / "kristal.workspace.json").write_text(
        '{"format":"kristal.local-workspace/3.2.0"}', encoding="utf-8"
    )
    release = workspace / "release" / "v9" / "states" / "a" / "b"
    release.mkdir(parents=True)
    state = release / "state-snapshot.json"
    state.write_text(_minimal_v9_state("urn:kristal:state:released", "3"), encoding="utf-8")
    assert find_v9_state(release) == state.resolve()
