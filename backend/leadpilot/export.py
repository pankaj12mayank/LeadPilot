"""Excel (primary) + optional JSON export for LeadPilot."""

from __future__ import annotations

import json
from typing import Any

from .utils import get_logger

log = get_logger("leadpilot.export")


def _flatten(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Name": row.get("Name", ""),
        "Company": row.get("Company", ""),
        "Role": row.get("Role", ""),
        "Profile Link": row.get("Profile Link", "") or row.get("linkedin_url", ""),
        "Agency Type (SEO / Ads / Creative)": row.get("Agency Type", "")
        or row.get("agency_type", ""),
        "Team Size (estimate)": row.get("Team Size", "")
        or row.get("team_size", ""),
        "Problem Seen": row.get("problems_refined") or row.get("Problem Seen", ""),
        "Last Active": row.get("Last Active", "N/A"),
        "Connection Sent (Date)": row.get("Connection Sent (Date)", "")
        or row.get("connection_sent", ""),
        "Replied (Y/N)": row.get("Replied (Y/N)", "") or row.get("replied_yn", "N"),
        "Status": row.get("Status", "") or row.get("status", "new"),
        "Solution": row.get("Solution", "") or row.get("solution_text", ""),
        "Work Email": row.get("work_email", ""),
        "Company Domain": row.get("company_domain", ""),
        "Industry": row.get("industry", ""),
        "Employee Count (validated)": row.get("employee_count", ""),
        "Revenue": row.get("revenue", ""),
        "Lead Score": row.get("lead_score", ""),
        "Priority": row.get("priority", ""),
        "Enrichment Status": row.get("enrichment_status", ""),
        "Enrichment Source": row.get("enrichment_source", ""),
        "Scoring Notes": row.get("scoring_reasoning", ""),
    }


def export_leadpilot(
    rows: list[dict[str, Any]],
    xlsx_path: str,
    json_path: str | None = None,
) -> None:
    if not rows:
        log.warning("No rows to export")
        return
    try:
        import pandas as pd
    except ImportError as e:
        raise RuntimeError("pip install pandas openpyxl") from e
    flat = [_flatten(r) for r in rows]
    df = pd.DataFrame(flat)
    try:
        df.to_excel(xlsx_path, index=False, engine="openpyxl")
    except OSError as e:
        log.error("Failed to write %s: %s", xlsx_path, e)
        raise
    log.info("Wrote %s", xlsx_path)
    if json_path:
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(flat, f, ensure_ascii=False, indent=2)
            log.info("Wrote %s", json_path)
        except OSError as e:
            log.error("Failed to write JSON %s: %s", json_path, e)
            raise
