"""
Run the Selenium + leadpilot pipeline (``python -m backend.leadpilot``) as a child process
so the FastAPI app is not affected by preflight ``sys.exit`` in ``backend.leadpilot.main``.
Used by the web UI to start the same flow without a second terminal.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Repository root: backend/services/this_file.py -> parents[2] == project root
_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class LeadpilotJobView:
    available: bool
    state: str  # idle | running | completed | failed
    message: str
    log_tail: list[str]
    pid: int | None
    returncode: int | None
    started_at: float | None
    finished_at: float | None
    command: str | None


_lock = threading.Lock()
_proc: subprocess.Popen[str] | None = None
_log_lines: deque[str] = deque(maxlen=200)
_state: str = "idle"
_message: str = ""
_returncode: int | None = None
_started: float | None = None
_finished: float | None = None
_last_cmd: str | None = None
_drain_thread: threading.Thread | None = None


def is_available() -> bool:
    p = _REPO_ROOT / "backend" / "leadpilot" / "__init__.py"
    sc = _REPO_ROOT / "backend" / "leadpilot" / "main.py"
    return p.is_file() and sc.is_file()


def get_status() -> LeadpilotJobView:
    with _lock:
        _sync_state_from_proc_nolock()
        return LeadpilotJobView(
            available=is_available(),
            state=_state,
            message=_message,
            log_tail=list(_log_lines),
            pid=(_proc.pid if _proc and _proc.poll() is None else None),
            returncode=_returncode,
            started_at=_started,
            finished_at=_finished,
            command=_last_cmd,
        )


def _append_log(line: str) -> None:
    line = line.rstrip("\r\n")
    if not line and not _log_lines:
        return
    if line or _log_lines:  # allow empty line between blocks
        _log_lines.append(line)


def _sync_state_from_proc_nolock() -> None:
    global _state, _message, _returncode, _finished, _proc
    if _proc is None:
        return
    code = _proc.poll()
    if code is None:
        _state = "running"
        return
    if _returncode is None:
        _returncode = int(code)
    if _state == "running":
        _state = "completed" if _returncode == 0 else "failed"
        if _returncode == 0:
            _message = "Pipeline finished successfully."
        else:
            _message = f"Process exited with code {_returncode}."
    _finished = _finished or time.time()
    _proc = None


def _drain_stream(stream: Any) -> None:
    if stream is None:
        return
    try:
        for line in stream:
            with _lock:
                _append_log(line if isinstance(line, str) else str(line))
    except Exception as e:  # noqa: BLE001
        with _lock:
            _append_log(f"[stream error] {e!s}")


def _wait_proc(p: subprocess.Popen[str], out_t: threading.Thread, err_t: threading.Thread) -> None:
    global _state, _message, _returncode, _finished, _proc
    try:
        p.wait(timeout=None)
    except Exception:  # noqa: BLE001
        pass
    out_t.join(timeout=2.0)
    err_t.join(timeout=2.0)
    with _lock:
        code = p.poll()
        if code is not None and _returncode is None:
            _returncode = int(code)
        if _state == "running" and p.poll() is not None:
            _returncode = int(p.returncode or 0)
            _state = "completed" if _returncode == 0 else "failed"
            if _returncode == 0:
                _message = "Pipeline finished successfully."
            else:
                _message = f"Process exited with code {_returncode}."
        _finished = time.time()
        _proc = None


def start_leadpilot_subprocess(
    *,
    argv: list[str],
    extra_env: dict[str, str] | None = None,
) -> str | None:
    """
    Spawn ``sys.executable`` with *argv* (e.g. ``["-m", "leadpilot", ...]``).
    Returns an error string, or None on success.
    """
    global _proc, _state, _message, _returncode, _started, _finished, _last_cmd, _drain_thread, _log_lines
    if not is_available():
        return "Selenium leadpilot package is not present (expected backend/leadpilot)."

    with _lock:
        if _proc is not None and _proc.poll() is None:
            return "A leadpilot run is already in progress."
        _log_lines = deque(maxlen=200)
        _returncode = None
        _finished = None
        _message = "Starting pipeline…"
        _state = "running"
        _started = time.time()
        _last_cmd = f"{sys.executable} " + " ".join(argv)
        _append_log(_last_cmd)

    env = os.environ.copy()
    if extra_env:
        env.update({k: v for k, v in extra_env.items() if v is not None and v != ""})
    # Ensure imports resolve like the CLI
    pyp = str(_REPO_ROOT)
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = pyp + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = pyp

    try:
        p = subprocess.Popen(
            [sys.executable, *argv],
            cwd=str(_REPO_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
        )
    except OSError as e:  # noqa: PERF203
        with _lock:
            _state = "failed"
            _message = f"Failed to start process: {e}"
            _returncode = -1
            _finished = time.time()
        return str(e)

    with _lock:
        _proc = p

    out_t = threading.Thread(
        target=_drain_stream,
        args=(p.stdout,),
        name="leadpilot-stdout",
        daemon=True,
    )
    err_t = threading.Thread(
        target=_drain_stream,
        args=(p.stderr,),
        name="leadpilot-stderr",
        daemon=True,
    )
    out_t.start()
    err_t.start()
    _drain_thread = threading.Thread(
        target=_wait_proc,
        args=(p, out_t, err_t),
        name="leadpilot-wait",
        daemon=True,
    )
    _drain_thread.start()
    return None


def stop_leadpilot() -> str | None:
    """Best-effort terminate. Returns error message if not running, else None."""
    global _proc, _state, _message, _returncode, _finished
    with _lock:
        p = _proc
        if p is None or p.poll() is not None:
            return "No run in progress."
        _message = "Stopping…"
    try:
        p.terminate()
    except OSError as e:  # noqa: PERF203
        return str(e)
    t0 = time.time()
    while p.poll() is None and (time.time() - t0) < 8.0:
        time.sleep(0.2)
    if p.poll() is None:
        try:
            p.kill()
        except OSError:
            pass
    with _lock:
        if _returncode is None and p.poll() is not None:
            _returncode = int(p.returncode or 0)
        if _state == "running":
            _state = "failed"
            _message = "Stopped by user."
        _returncode = _returncode if _returncode is not None else -15
        _finished = time.time()
        _proc = None
    return None
