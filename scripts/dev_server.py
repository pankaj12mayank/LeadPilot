"""
Run FastAPI + Vite in one terminal. Use this when separate CMD windows fail or close.

Repo root:
  .venv\\Scripts\\python.exe scripts\\dev_server.py

Ctrl+C stops both (best-effort on Windows).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def _venv_python() -> Path | None:
    if sys.platform == "win32":
        p = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        p = ROOT / ".venv" / "bin" / "python"
    return p if p.is_file() else None


def _kill_process_tree(pid: int) -> None:
    if sys.platform == "win32" and pid > 0:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )


def _terminate(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    p.terminate()
    try:
        p.wait(timeout=6)
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            if p.pid:
                _kill_process_tree(p.pid)


def main() -> int:
    py = _venv_python()
    if not py:
        print("[dev] ERROR: no .venv — run from repo root:  python -m venv .venv", file=sys.stderr)
        print("[dev] Then install:  .venv\\Scripts\\pip install -r requirements.txt", file=sys.stderr)
        return 1

    if not (FRONTEND / "package.json").is_file():
        print("[dev] ERROR: frontend/package.json missing.", file=sys.stderr)
        return 1

    npm = shutil.which("npm")
    if not npm:
        print("[dev] ERROR: npm not on PATH (install Node.js LTS).", file=sys.stderr)
        return 1

    os.chdir(ROOT)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    api_cmd = [
        str(py),
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    print("=" * 60)
    print(f"[dev] Repo:  {ROOT}")
    print("[dev] API:   http://127.0.0.1:8000/docs   (JSON under /api)")
    print("[dev] Web:   http://localhost:5173/")
    print("[dev] LinkedIn (Selenium) full pipeline: open a 2nd terminal, repo root:")
    print("[dev]         python leadpilot_single.py --help   (or: python -m backend.leadpilot)")
    print("[dev]         LNN_BASE_URL=http://127.0.0.1:8000/api  to push leads into this API")
    print("[dev] Press Ctrl+C here to stop BOTH (API + Vite).")
    print("=" * 60)

    procs: list[subprocess.Popen] = []

    api = subprocess.Popen(api_cmd, cwd=str(ROOT), env=env)
    procs.append(api)

    time.sleep(1.5)
    if api.poll() is not None:
        print(f"[dev] ERROR: API exited immediately (code {api.returncode}).", file=sys.stderr)
        print("[dev] Try: .venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000", file=sys.stderr)
        return api.returncode or 1

    shell = sys.platform == "win32"
    web_cmd: str | list[str] = f'"{npm}" run dev' if shell else [npm, "run", "dev"]
    web = subprocess.Popen(web_cmd, cwd=str(FRONTEND), env=env, shell=shell)
    procs.append(web)

    exit_code = 0
    try:
        while True:
            if api.poll() is not None:
                print(f"\n[dev] API exited ({api.returncode}). Stopping Vite…")
                exit_code = api.returncode or 0
                break
            if web.poll() is not None:
                print(f"\n[dev] Vite exited ({web.returncode}). Stopping API…")
                exit_code = web.returncode or 0
                break
            time.sleep(0.35)
    except KeyboardInterrupt:
        print("\n[dev] Ctrl+C — stopping…")
        exit_code = 0
    finally:
        print("[dev] Cleaning up processes…")
        for p in reversed(procs):
            _terminate(p)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
