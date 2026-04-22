from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.lead_cleaning import (
    clean_email,
    clean_phone,
    clean_url,
    normalize_company_name,
    normalize_job_title,
    normalize_name,
    remove_duplicates,
    validate_record,
)
from backend.services.platform_service import normalize_platform


def clean_and_validate(lead: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Normalize common CRM fields + ``validate_record`` (single-row API)."""
    row = dict(lead)
    if row.get("platform") or row.get("source_platform"):
        p = row.get("source_platform") or row.get("platform")
        row["source_platform"] = normalize_platform(str(p or ""))
    row["full_name"] = normalize_name(row.get("full_name") or row.get("name"))
    row["title"] = normalize_job_title(row.get("title") or row.get("job_title"))
    row["company_name"] = normalize_company_name(row.get("company_name") or row.get("company"))
    row["email"] = clean_email(row.get("email"))
    row["phone"] = clean_phone(row.get("phone"))
    row["linkedin_url"] = clean_url(row.get("linkedin_url") or row.get("profile_url"), "linkedin")
    row["company_website"] = clean_url(row.get("company_website") or row.get("website"), "website")
    ok, errors = validate_record(row)
    return ok, errors, row


def dedupe_leads(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    return remove_duplicates(rows)
