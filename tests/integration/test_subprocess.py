import asyncio
import os
from pathlib import Path

import pytest

from kompiler.adapters.utils import run_python_json
from kompiler.errors import AdapterError


def _script(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "query.py"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_subprocess_output_is_bounded(tmp_path: Path):
    script = _script(tmp_path, "import json\nprint(json.dumps(['x'*10000]))\n")
    with pytest.raises(AdapterError) as exc:
        await run_python_json(tmp_path, script, [], timeout_ms=3000, max_bytes=128)
    assert exc.value.code == "RESOURCE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_subprocess_arguments_are_not_shell_interpreted(tmp_path: Path):
    marker = tmp_path / "should-not-exist"
    script = _script(tmp_path, "import json,sys\nprint(json.dumps(sys.argv[1:]))\n")
    payload = f"; touch {marker}"
    result = await run_python_json(tmp_path, script, [payload], timeout_ms=3000, max_bytes=4096)
    assert result.items == [payload]
    assert not marker.exists()


@pytest.mark.asyncio
async def test_malformed_native_json_is_rejected(tmp_path: Path):
    script = _script(tmp_path, "print('not-json')\n")
    with pytest.raises(AdapterError) as exc:
        await run_python_json(tmp_path, script, [], timeout_ms=3000, max_bytes=4096)
    assert exc.value.code == "ADAPTER_OUTPUT_INVALID"


@pytest.mark.skipif(os.name != "posix", reason="process-group orphan check is POSIX-specific")
@pytest.mark.asyncio
async def test_cancelled_subprocess_is_killed(tmp_path: Path):
    pid_file = tmp_path / "pid.txt"
    script = _script(
        tmp_path,
        "import json,os,time\n"
        f"open({str(pid_file)!r},'w').write(str(os.getpid()))\n"
        "time.sleep(60)\n"
        "print(json.dumps({'ok': True}))\n",
    )
    task = asyncio.create_task(
        run_python_json(tmp_path, script, [], timeout_ms=120000, max_bytes=4096)
    )
    for _ in range(100):
        if pid_file.exists():
            break
        await asyncio.sleep(0.02)
    assert pid_file.exists()
    pid = int(pid_file.read_text())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.05)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
