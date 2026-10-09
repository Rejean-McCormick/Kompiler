from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class SQLiteStore:
    """Small serialized SQLite store safe for a shared local API runtime."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._closed = False
        self.con = sqlite3.connect(self.path, check_same_thread=False)
        with self._lock:
            self.con.execute("PRAGMA journal_mode=WAL")
            self.con.execute("PRAGMA foreign_keys=ON")
            self.con.execute("PRAGMA busy_timeout=5000")
        self._init()

    def _init(self) -> None:
        with self._lock:
            self.con.executescript(
                """
                CREATE TABLE IF NOT EXISTS cache (
                  cache_key TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  value_json TEXT NOT NULL,
                  byte_size INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                  run_id TEXT PRIMARY KEY,
                  request_id TEXT,
                  status TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  completed_at TEXT,
                  query_hash TEXT,
                  context_pack_id TEXT,
                  artifact_id TEXT,
                  metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                  artifact_id TEXT PRIMARY KEY,
                  kind TEXT NOT NULL,
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  body_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runs_request_id ON runs(request_id);
                CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
                CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind);
                """
            )
            cols = {row[1] for row in self.con.execute("PRAGMA table_info(runs)")}
            if "artifact_id" not in cols:
                self.con.execute("ALTER TABLE runs ADD COLUMN artifact_id TEXT")
            self.con.commit()

    def cache_get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.con.execute("SELECT value_json FROM cache WHERE cache_key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key: str, value: dict[str, Any]) -> None:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self.con.execute(
                "INSERT OR REPLACE INTO cache(cache_key,value_json,byte_size) VALUES(?,?,?)",
                (key, text, len(text.encode("utf-8"))),
            )
            self.con.commit()

    def cache_stats(self) -> dict[str, int]:
        with self._lock:
            row = self.con.execute("SELECT COUNT(*), COALESCE(SUM(byte_size),0) FROM cache").fetchone()
        return {"entries": int(row[0]), "bytes": int(row[1])}

    def cache_clear(self) -> int:
        with self._lock:
            n = self.con.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            self.con.execute("DELETE FROM cache")
            self.con.commit()
        return int(n)

    def run_start(self, run_id: str, request_id: str, started_at: str, query_hash: str) -> None:
        with self._lock:
            self.con.execute(
                "INSERT OR REPLACE INTO runs(run_id,request_id,status,started_at,query_hash) VALUES(?,?,?,?,?)",
                (run_id, request_id, "running", started_at, query_hash),
            )
            self.con.commit()

    def run_finish(
        self,
        run_id: str,
        status: str,
        completed_at: str,
        context_pack_id: str | None,
        artifact_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        with self._lock:
            self.con.execute(
                "UPDATE runs SET status=?,completed_at=?,context_pack_id=?,artifact_id=?,metadata_json=? WHERE run_id=?",
                (
                    status,
                    completed_at,
                    context_pack_id,
                    artifact_id,
                    json.dumps(metadata, ensure_ascii=False),
                    run_id,
                ),
            )
            self.con.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.con.execute(
                "SELECT run_id,request_id,status,started_at,completed_at,query_hash,context_pack_id,artifact_id,metadata_json "
                "FROM runs WHERE run_id=?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        keys = [
            "run_id",
            "request_id",
            "status",
            "started_at",
            "completed_at",
            "query_hash",
            "context_pack_id",
            "artifact_id",
            "metadata",
        ]
        vals = list(row)
        vals[-1] = json.loads(vals[-1])
        return dict(zip(keys, vals, strict=True))

    def put_artifact(self, artifact_id: str, kind: str, body: dict[str, Any]) -> None:
        with self._lock:
            self.con.execute(
                "INSERT OR REPLACE INTO artifacts(artifact_id,kind,body_json) VALUES(?,?,?)",
                (artifact_id, kind, json.dumps(body, ensure_ascii=False)),
            )
            self.con.commit()

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.con.execute(
                "SELECT body_json FROM artifacts WHERE artifact_id=?", (artifact_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self.con.close()
                self._closed = True
