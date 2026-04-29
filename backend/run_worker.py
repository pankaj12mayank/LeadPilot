from __future__ import annotations

import argparse
import json
from typing import Any

from backend.services import task_worker_service
from database.orm.bootstrap import init_sa_tables


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LeadPilot distributed worker instance runner.")
    p.add_argument("--workers", type=int, default=0, help="Parallel workers on this machine (0 = use admin config).")
    p.add_argument("--max-tasks-per-worker", type=int, default=10, help="Tasks per worker each cycle.")
    p.add_argument("--poll-seconds", type=float, default=2.0, help="Sleep time when queue is idle.")
    p.add_argument("--max-cycles", type=int, default=0, help="0 means run forever.")
    return p


def main() -> dict[str, Any]:
    args = _parser().parse_args()
    init_sa_tables()
    out = task_worker_service.run_worker_instance_loop(
        worker_count=args.workers,
        max_tasks_per_worker=args.max_tasks_per_worker,
        poll_seconds=args.poll_seconds,
        max_cycles=args.max_cycles,
    )
    print(json.dumps(out, ensure_ascii=True, default=str))
    return out


if __name__ == "__main__":
    main()
