#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _venv_python() -> Path:
    if sys.platform == "win32":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def _kill_process_tree(pid: int) -> None:
    if sys.platform == "win32" and pid > 0:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _kill_process_tree(int(proc.pid or 0))


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"[run] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def ensure_venv() -> Path:
    py = _venv_python()
    if py.is_file():
        return py
    _run([sys.executable, "-m", "venv", str(ROOT / ".venv")], cwd=ROOT)
    if not py.is_file():
        raise RuntimeError("Failed to create virtual environment at .venv")
    return py


def ensure_env_files() -> None:
    env = ROOT / ".env"
    env_ex = ROOT / ".env.example"
    if not env.exists() and env_ex.exists():
        shutil.copyfile(env_ex, env)
        print("[ok] Created .env from .env.example")
    fenv = FRONTEND / ".env"
    fenv_ex = FRONTEND / ".env.example"
    if not fenv.exists() and fenv_ex.exists():
        shutil.copyfile(fenv_ex, fenv)
        print("[ok] Created frontend/.env from frontend/.env.example")


def install_dependencies(py: Path) -> None:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required. Install Node.js LTS and retry.")
    _run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(py), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
    _run([str(py), "-m", "playwright", "install", "--with-deps"], cwd=ROOT)
    if not (FRONTEND / "package.json").is_file():
        raise RuntimeError("frontend/package.json missing.")
    if (FRONTEND / "package-lock.json").is_file():
        _run([npm, "ci"], cwd=FRONTEND)
    else:
        _run([npm, "install"], cwd=FRONTEND)


def initialize_database(py: Path) -> None:
    _run([str(py), str(ROOT / "scripts" / "init_database.py")], cwd=ROOT)


def run_full_stack(py: Path) -> int:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required. Install Node.js LTS and retry.")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    api_cmd = [str(py), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"]
    web_cmd = [npm, "run", "dev"]

    print("=" * 60)
    print("[leadpilot] API: http://127.0.0.1:8000/docs")
    print("[leadpilot] Web: http://localhost:5173")
    print("[leadpilot] Press Ctrl+C to stop both services.")
    print("=" * 60)

    procs: list[subprocess.Popen] = []
    api = subprocess.Popen(api_cmd, cwd=str(ROOT), env=env)
    procs.append(api)
    time.sleep(1.5)
    if api.poll() is not None:
        return int(api.returncode or 1)
    web = subprocess.Popen(web_cmd, cwd=str(FRONTEND), env=env)
    procs.append(web)

    code = 0
    try:
        while True:
            if api.poll() is not None:
                print(f"[leadpilot] API exited ({api.returncode}). Stopping frontend...")
                code = int(api.returncode or 0)
                break
            if web.poll() is not None:
                print(f"[leadpilot] Frontend exited ({web.returncode}). Stopping API...")
                code = int(web.returncode or 0)
                break
            time.sleep(0.35)
    except KeyboardInterrupt:
        print("\n[leadpilot] Stopping...")
    finally:
        for p in reversed(procs):
            _terminate(p)
    return code


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LeadPilot one-command setup and run")
    p.add_argument("--setup-only", action="store_true", help="Install dependencies and initialize DB, then exit")
    p.add_argument("--run-only", action="store_true", help="Run API + frontend without setup steps")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.setup_only and args.run_only:
        print("Use only one of --setup-only or --run-only.", file=sys.stderr)
        return 2
    os.chdir(ROOT)
    py = ensure_venv()
    ensure_env_files()
    if not args.run_only:
        install_dependencies(py)
        initialize_database(py)
        print("[ok] Setup complete.")
    if args.setup_only:
        return 0
    return run_full_stack(py)


if __name__ == "__main__":
    raise SystemExit(main())
