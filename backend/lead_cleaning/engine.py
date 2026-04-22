"""
Lead cleaning pipeline: raw_leads.csv → cleaned_leads.csv → enriched_leads.csv + CleaningSummary.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd

import config as app_config
from backend.lead_cleaning.cleaners import clean_email, clean_phone, clean_url
from backend.lead_cleaning.dedupe import remove_duplicates
from backend.lead_cleaning.normalizers import normalize_company_name, normalize_job_title, normalize_name
from backend.lead_cleaning.summary import CleaningSummary
from backend.lead_cleaning.validators import validate_record, _is_row_empty
from backend.utils.logger import get_logger

logger = get_logger(__name__)

STANDARD_COLUMNS: List[str] = [
    "full_name",
    "title",
    "company_name",
    "company_website",
    "linkedin_url",
    "email",
    "phone",
    "company_size",
    "industry",
    "location",
    "source_platform",
    "notes",
]


def _lower_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k).strip().lower(): v for k, v in row.items() if k is not None}


def _coerce_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Map mixed CSV headers to standard keys."""
    x = _lower_keys(r)
    return {
        "full_name": str(x.get("full_name") or x.get("name") or "").strip(),
        "title": str(x.get("title") or x.get("job_title") or "").strip(),
        "company_name": str(x.get("company_name") or x.get("company") or "").strip(),
        "company_website": str(x.get("company_website") or x.get("website") or "").strip(),
        "linkedin_url": str(x.get("linkedin_url") or x.get("profile_url") or x.get("linkedin") or "").strip(),
        "email": str(x.get("email") or "").strip(),
        "phone": str(x.get("phone") or "").strip(),
        "company_size": str(x.get("company_size") or "").strip(),
        "industry": str(x.get("industry") or "").strip(),
        "location": str(x.get("location") or "").strip(),
        "source_platform": str(x.get("source_platform") or x.get("platform") or "").strip(),
        "notes": str(x.get("notes") or "").strip(),
    }


def _apply_cleaners_and_normalizers(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    out["full_name"] = normalize_name(out.get("full_name"))
    out["title"] = normalize_job_title(out.get("title"))
    out["company_name"] = normalize_company_name(out.get("company_name"))
    out["email"] = clean_email(out.get("email"))
    out["phone"] = clean_phone(out.get("phone"))
    out["linkedin_url"] = clean_url(out.get("linkedin_url"), "linkedin") if out.get("linkedin_url") else ""
    out["company_website"] = (
        clean_url(out.get("company_website"), "website") if out.get("company_website") else ""
    )
    return out


def _enrich_row(row: Dict[str, Any]) -> Dict[str, Any]:
    e = row.get("email") or ""
    domain = e.split("@", 1)[-1] if "@" in e else ""
    li = row.get("linkedin_url") or ""
    username = ""
    if "/in/" in li:
        try:
            username = li.split("/in/", 1)[1].strip("/").split("?", 1)[0]
        except IndexError:
            username = ""
    quality = 40
    if e:
        quality += 20
    if li:
        quality += 20
    if row.get("company_website"):
        quality += 10
    if row.get("phone"):
        quality += 10
    quality = min(100, quality)
    enriched = dict(row)
    enriched["email_domain"] = domain
    enriched["linkedin_username"] = username
    enriched["data_quality_score"] = quality
    return enriched


def run_cleaning_pipeline(
    input_csv_path: str,
    exports_dir: str | None = None,
) -> CleaningSummary:
    """
    Read ``input_csv_path``, write ``raw_leads.csv``, ``cleaned_leads.csv``, ``enriched_leads.csv``
    under ``exports_dir`` (default: ``config.EXPORTS_DIR``).
    """
    app_config.ensure_data_dirs()
    out_dir = exports_dir or app_config.EXPORTS_DIR
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.isfile(input_csv_path):
        raise FileNotFoundError(f"Input CSV not found: {input_csv_path}")

    raw_path = os.path.join(out_dir, "raw_leads.csv")
    cleaned_path = os.path.join(out_dir, "cleaned_leads.csv")
    enriched_path = os.path.join(out_dir, "enriched_leads.csv")

    df = pd.read_csv(input_csv_path, dtype=str, keep_default_na=False)
    raw_rows: List[Dict[str, Any]] = df.to_dict(orient="records")
    total_raw = len(raw_rows)

    pd.DataFrame(raw_rows).to_csv(raw_path, index=False)
    logger.info("Wrote %s rows to %s", total_raw, raw_path)

    coerced = [_coerce_row(r) for r in raw_rows]
    non_empty = [r for r in coerced if not _is_row_empty(r)]
    empty_removed = len(coerced) - len(non_empty)

    cleaned_intermediate = [_apply_cleaners_and_normalizers(r) for r in non_empty]
    deduped, dup_count = remove_duplicates(cleaned_intermediate)

    valid: List[Dict[str, Any]] = []
    invalid = 0
    for r in deduped:
        ok, _errs = validate_record(r)
        if ok:
            valid.append(r)
        else:
            invalid += 1

    if valid:
        cleaned_df = pd.DataFrame([{k: v.get(k, "") for k in STANDARD_COLUMNS} for v in valid])
    else:
        cleaned_df = pd.DataFrame(columns=STANDARD_COLUMNS)
    cleaned_df.to_csv(cleaned_path, index=False)

    enriched_rows = [_enrich_row(r) for r in valid]
    enriched_cols = STANDARD_COLUMNS + ["email_domain", "linkedin_username", "data_quality_score"]
    if enriched_rows:
        pd.DataFrame([{k: r.get(k, "") for k in enriched_cols} for r in enriched_rows]).to_csv(
            enriched_path, index=False
        )
    else:
        pd.DataFrame(columns=enriched_cols).to_csv(enriched_path, index=False)

    logger.info(
        "Cleaning done: raw=%s empty=%s dups=%s invalid=%s cleaned=%s",
        total_raw,
        empty_removed,
        dup_count,
        invalid,
        len(valid),
    )

    return CleaningSummary(
        total_raw_leads=total_raw,
        total_cleaned_leads=len(valid),
        total_enriched_leads=len(enriched_rows),
        empty_rows_removed=empty_removed,
        duplicates_removed=dup_count,
        invalid_records_removed=invalid,
    )


def run_cleaning_from_records(rows: List[Dict[str, Any]], exports_dir: str | None = None) -> CleaningSummary:
    """Same as pipeline but from in-memory rows (writes a temp raw CSV then runs)."""
    app_config.ensure_data_dirs()
    out_dir = exports_dir or app_config.EXPORTS_DIR
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, "_tmp_raw_input.csv")
    pd.DataFrame(rows).to_csv(tmp, index=False)
    try:
        return run_cleaning_pipeline(tmp, exports_dir=out_dir)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
