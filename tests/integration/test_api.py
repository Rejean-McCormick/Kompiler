from pathlib import Path

from fastapi.testclient import TestClient

from kompiler.api.app import create_app
from kompiler.config import AppConfig, StorageConfig
from kompiler.registry import AdapterRegistry
from kompiler.runtime import KompilerRuntime
from kompiler.storage import SQLiteStore
from tests.fixtures.mock_adapter import MockAdapter


def _runtime(tmp_path: Path) -> KompilerRuntime:
    reg = AdapterRegistry()
    reg.register(MockAdapter(tmp_path))
    cfg = AppConfig(storage=StorageConfig(database=tmp_path / "api.db", cache=True, retention="packs"))
    return KompilerRuntime(cfg, reg, SQLiteStore(cfg.storage.database))


def test_api_validate_run_and_retrieve_pack(tmp_path: Path):
    rt = _runtime(tmp_path)
    query = {
        "request_id": "api",
        "operations": [
            {"id": "a", "target": "Mock", "operation": "find", "params": {"topic": "air", "limit": 2}}
        ],
    }
    with TestClient(create_app(rt)) as client:
        validated = client.post("/v1/queries/validate", json=query)
        assert validated.status_code == 200
        assert validated.json()["valid"] is True

        response = client.post("/v1/runs", json=query)
        assert response.status_code == 200
        pack = response.json()
        run_id = pack["execution"]["run_id"]

        state = client.get(f"/v1/runs/{run_id}")
        assert state.status_code == 200
        assert state.json()["artifact_id"] == pack["artifact_hash"]

        fetched = client.get(f"/v1/runs/{run_id}/context-pack")
        assert fetched.status_code == 200
        assert fetched.json()["artifact_hash"] == pack["artifact_hash"]


def test_api_admission_error_is_422(tmp_path: Path):
    rt = _runtime(tmp_path)
    query = {
        "request_id": "bad",
        "operations": [{"id": "a", "target": "Mock", "operation": "does_not_exist", "params": {}}],
    }
    with TestClient(create_app(rt)) as client:
        response = client.post("/v1/runs", json=query)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNKNOWN_OPERATION"


def test_api_impossible_budget_is_413(tmp_path: Path):
    rt = _runtime(tmp_path)
    query = {
        "request_id": "too-small",
        "budget": {"max_items": 1, "max_bytes": 1, "target_tokens": 1},
        "operations": [{"id": "a", "target": "Mock", "operation": "echo_inputs", "params": {"values": []}}],
    }
    with TestClient(create_app(rt)) as client:
        response = client.post("/v1/runs", json=query)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "BUDGET_IMPOSSIBLE"
