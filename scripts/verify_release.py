#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF_PATH = ROOT / "logs" / "release-proof.md"


@dataclass
class CheckResult:
    name: str
    command: list[str]
    exit_code: int
    elapsed_s: float
    stdout_tail: str


def run_check(name: str, command: list[str], cwd: Path) -> CheckResult:
    start = time.time()
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    elapsed = time.time() - start
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    tail = "\n".join((out + ("\n" + err if err else "")).splitlines()[-12:]).strip()
    return CheckResult(
        name=name,
        command=command,
        exit_code=int(proc.returncode),
        elapsed_s=elapsed,
        stdout_tail=tail,
    )


def build_checks(mode: str) -> list[tuple[str, list[str], Path]]:
    py = [sys.executable, "-m", "pytest"]
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required for frontend verification checks.")
    checks: list[tuple[str, list[str], Path]] = [
        (
            "Backend auth + isolation",
            py + ["tests/test_auth.py", "-q"],
            ROOT,
        ),
        (
            "Backend debug validation",
            py + ["tests/test_debug_validation.py", "-q"],
            ROOT,
        ),
        (
            "Backend ingestion reliability",
            py + ["tests/test_company_ingestion_service.py", "-q"],
            ROOT,
        ),
        (
            "Explorer regression guard",
            py + ["tests/test_companies_api.py::test_companies_explorer_search_supports_filters_and_enriched_columns", "-q"],
            ROOT,
        ),
        (
            "Frontend search/mode smoke",
            [npm, "run", "test", "--", "SearchLeadsPage"],
            ROOT / "frontend",
        ),
    ]
    if mode == "full":
        checks.insert(
            3,
            (
                "Backend broader companies API",
                py + ["tests/test_companies_api.py", "-q"],
                ROOT,
            ),
        )
    return checks


def write_proof(results: list[CheckResult], mode: str) -> None:
    PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_ok = all(r.exit_code == 0 for r in results)
    lines: list[str] = []
    lines.append("# Release Proof")
    lines.append("")
    lines.append(f"- Mode: `{mode}`")
    lines.append(f"- Status: `{'PASS' if all_ok else 'FAIL'}`")
    lines.append("")
    lines.append("| Check | Exit | Seconds |")
    lines.append("|---|---:|---:|")
    for r in results:
        lines.append(f"| {r.name} | {r.exit_code} | {r.elapsed_s:.2f} |")
    lines.append("")
    for r in results:
        lines.append(f"## {r.name}")
        lines.append("")
        lines.append(f"- Command: `{' '.join(r.command)}`")
        lines.append(f"- Exit: `{r.exit_code}`")
        lines.append("")
        if r.stdout_tail:
            lines.append("```text")
            lines.append(r.stdout_tail)
            lines.append("```")
            lines.append("")
    lines.append(f"Final decision: **{'READY' if all_ok else 'NOT READY'}**")
    PROOF_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run release verification checks and write proof report.")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick")
    parser.add_argument("--quick", action="store_true", help="Alias for --mode quick")
    parser.add_argument("--full", action="store_true", help="Alias for --mode full")
    args = parser.parse_args()

    mode = "full" if args.full else "quick"
    if args.mode:
        mode = args.mode
    if args.quick:
        mode = "quick"

    checks = build_checks(mode)
    results: list[CheckResult] = []
    print(f"[verify_release] running {len(checks)} checks ({mode})...")
    for name, cmd, cwd in checks:
        print(f"[verify_release] {name}")
        res = run_check(name, cmd, cwd)
        results.append(res)
        print(f"  -> exit={res.exit_code} time={res.elapsed_s:.2f}s")

    write_proof(results, mode)
    print(f"[verify_release] proof written: {PROOF_PATH}")
    ok = all(r.exit_code == 0 for r in results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
