from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from kompiler.adapters.base import AdapterResult
from kompiler.errors import AdapterError


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def state_id_for_paths(paths: list[Path], *, base: Path | None = None) -> str:
    h = hashlib.sha256()
    base = base.resolve() if base is not None else None
    unique = {p.resolve(): p for p in paths}
    for p in sorted(unique, key=lambda x: str(x)):
        if not p.exists() or not p.is_file():
            continue
        rp = p.resolve()
        try:
            label = str(rp.relative_to(base)) if base is not None else str(rp)
        except ValueError:
            label = str(rp)
        h.update(label.encode("utf-8"))
        h.update(b"\0")
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return f"sha256:{h.hexdigest()}"


async def _terminate_process(proc: asyncio.subprocess.Process) -> None:
    """Terminate a subprocess tree best-effort on all supported platforms."""
    if proc.returncode is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass
    try:
        await proc.wait()
    except Exception:
        pass


class _OutputLimitExceeded(Exception):
    pass


async def _read_bounded(stream: asyncio.StreamReader | None, limit: int) -> bytes:
    if stream is None:
        return b""
    data = bytearray()
    while True:
        chunk = await stream.read(64 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > limit:
            raise _OutputLimitExceeded
    return bytes(data)


def json_documents(text: str) -> list[Any]:
    text = text.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        dec = json.JSONDecoder()
        out: list[Any] = []
        pos = 0
        while pos < len(text):
            while pos < len(text) and text[pos].isspace():
                pos += 1
            if pos >= len(text):
                break
            value, pos = dec.raw_decode(text, pos)
            out.extend(value if isinstance(value, list) else [value])
        return out


async def run_python_json(
    root: Path,
    script: Path,
    args: list[str],
    *,
    timeout_ms: int,
    max_bytes: int = 8_000_000,
) -> AdapterResult:
    script = script.resolve()
    root = root.resolve()
    if root not in script.parents:
        raise AdapterError("PATH_OUTSIDE_ALLOWED_ROOT", "adapter script escaped configured root")
    keep = ["PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR"]
    safe_env = {k: os.environ[k] for k in keep if k in os.environ}
    safe_env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    creationflags = 0
    kwargs: dict[str, Any] = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True
    elif os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creationflags
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script),
        *args,
        cwd=str(root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=safe_env,
        **kwargs,
    )
    stdout_task = asyncio.create_task(_read_bounded(proc.stdout, max_bytes))
    stderr_task = asyncio.create_task(_read_bounded(proc.stderr, max_bytes))
    wait_task = asyncio.create_task(proc.wait())
    tasks = [stdout_task, stderr_task, wait_task]
    try:
        stdout, stderr, _ = await asyncio.wait_for(
            asyncio.gather(*tasks), timeout=timeout_ms / 1000
        )
    except TimeoutError:
        for task in tasks:
            task.cancel()
        await _terminate_process(proc)
        raise AdapterError("TIMEOUT", f"adapter exceeded {timeout_ms} ms", retryable=True)
    except _OutputLimitExceeded:
        for task in tasks:
            task.cancel()
        await _terminate_process(proc)
        raise AdapterError("RESOURCE_LIMIT_EXCEEDED", "adapter output exceeded byte limit")
    except asyncio.CancelledError:
        for task in tasks:
            task.cancel()
        await _terminate_process(proc)
        raise
    if proc.returncode != 0:
        raise AdapterError(
            "ADAPTER_FAILURE",
            f"native adapter exited with status {proc.returncode}",
            {"stderr": stderr.decode("utf-8", "replace")[-4000:]},
        )
    try:
        items = json_documents(stdout.decode("utf-8"))
    except Exception as exc:
        raise AdapterError("ADAPTER_OUTPUT_INVALID", f"native adapter did not emit valid JSON: {exc}") from exc
    return AdapterResult(items=items, raw_item_count=len(items), metadata={"native_stderr": stderr.decode("utf-8", "replace")})
