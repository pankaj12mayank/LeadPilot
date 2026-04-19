"""Append a single captured lead to CSV using pandas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

import config


CSV_COLUMNS: list[str] = [
    "captured_at",
    "name",
    "title",
    "company",
    "industry",
    "location",
    "website",
    "email",
    "source_platform",
    "profile_url",
    "score",
    "tier",
    "status",
]


def append_lead_row(lead: dict[str, Any], captured_at: str, csv_path: str | None = None) -> None:
    path = Path(csv_path or config.SAFE_CAPTURE_CSV_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    row = {k: lead.get(k, "") for k in CSV_COLUMNS if k != "captured_at"}
    row["captured_at"] = captured_at

    df = pd.DataFrame([row], columns=CSV_COLUMNS)
    write_header = not path.is_file() or path.stat().st_size == 0
    df.to_csv(path, mode="a", header=write_header, index=False)
