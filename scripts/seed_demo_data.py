#!/usr/bin/env python3
"""Seed a demo user and sample CRM leads (SQLAlchemy / API_META_DB_PATH)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from database.meta_db import init_meta_schema  # noqa: E402
from database.orm.bootstrap import get_session_factory, init_sa_tables  # noqa: E402
from backend.services import auth_service, lead_orm_service  # noqa: E402


DEMO_EMAIL = os.getenv("SEED_DEMO_EMAIL", "demo@leadpilot.local").strip().lower()
DEMO_PASSWORD = os.getenv("SEED_DEMO_PASSWORD", "demo-password-change-me")


def main() -> None:
    config.ensure_data_dirs()
    init_meta_schema()
    init_sa_tables()

    if auth_service.get_user_by_email(DEMO_EMAIL):
        print(f"Skip: user already exists ({DEMO_EMAIL}).")
    else:
        auth_service.create_user(DEMO_EMAIL, DEMO_PASSWORD)
        print(f"Created user: {DEMO_EMAIL}")

    Session = get_session_factory()
    db = Session()
    try:
        existing = lead_orm_service.count_leads_filtered(db)
        if existing >= 3:
            print(f"Skip: {existing} lead(s) already present.")
            return

        samples = [
            {
                "full_name": "Alex Rivera",
                "title": "Head of Growth",
                "company_name": "Northwind Labs",
                "email": "alex.rivera@example.com",
                "linkedin_url": "https://www.linkedin.com/in/example-alex",
                "source_platform": "linkedin",
                "industry": "Software",
                "location": "Austin, TX",
                "status": "new",
            },
            {
                "full_name": "Jamie Chen",
                "title": "VP Engineering",
                "company_name": "Contoso AI",
                "email": "jamie.chen@example.com",
                "linkedin_url": "https://www.linkedin.com/in/example-jamie",
                "source_platform": "apollo",
                "industry": "Software",
                "location": "San Francisco, CA",
                "status": "new",
            },
            {
                "full_name": "Sam Okonkwo",
                "title": "Founder",
                "company_name": "Fabrikam Data",
                "email": "sam@example.com",
                "linkedin_url": "",
                "source_platform": "upwork",
                "industry": "Consulting",
                "location": "Remote",
                "status": "contacted",
            },
        ]
        for row in samples:
            lead_orm_service.create_lead(db, row)
        db.commit()
        print(f"Inserted {len(samples)} demo lead(s).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
