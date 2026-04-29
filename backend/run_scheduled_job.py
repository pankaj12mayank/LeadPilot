from __future__ import annotations

import argparse
import json
from typing import Any

from backend.services import company_weekly_engine
from database.orm.bootstrap import get_session_factory, init_sa_tables


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LeadPilot cron scheduler entry point (STEP W11).")
    p.add_argument(
        "--job-type",
        required=True,
        choices=sorted(company_weekly_engine.SCHEDULED_JOB_TYPES),
        help="Scheduled job type to execute.",
    )
    p.add_argument("--keyword", default="software")
    p.add_argument("--location", default="")
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--delay-seconds", type=float, default=1.0)
    p.add_argument("--execute-now", action="store_true", help="Run immediately instead of enqueue-only mode.")
    return p


def main() -> dict[str, Any]:
    args = _parser().parse_args()
    init_sa_tables()
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        out = company_weekly_engine.run_scheduled_job(
            db,
            job_type=args.job_type,
            keyword=args.keyword,
            location=args.location,
            batch_size=args.batch_size,
            delay_seconds=args.delay_seconds,
            enqueue_only=not bool(args.execute_now),
        )
        print(json.dumps(out, ensure_ascii=True, default=str))
        return out
    finally:
        db.close()


if __name__ == "__main__":
    main()
