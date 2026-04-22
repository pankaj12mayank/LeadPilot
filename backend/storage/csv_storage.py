from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

import config
from backend.settings.lead_schema import LEAD_COLUMNS, normalize_lead_row, row_for_write, utc_now_iso
from backend.storage.base_storage import BaseStorage


class CsvStorage(BaseStorage):
    def __init__(self, path: Optional[str] = None):
        self.path = path or getattr(config, "CSV_FILE_PATH", "data/leads.csv")

    def init_storage(self) -> None:
        try:
            if not os.path.exists(self.path):
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                df = pd.DataFrame(columns=LEAD_COLUMNS)
                df.to_csv(self.path, index=False)
        except Exception:
            pass

    def _read_df(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            return pd.DataFrame(columns=LEAD_COLUMNS)
        try:
            df = pd.read_csv(self.path)
            for col in LEAD_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=LEAD_COLUMNS)

    def _write_df(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        for col in LEAD_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[LEAD_COLUMNS]
        tmp = self.path + ".tmp"
        df.to_csv(tmp, index=False)
        os.replace(tmp, self.path)

    def create_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        row = row_for_write(lead)
        now = utc_now_iso()
        if not row.get("created_at"):
            row["created_at"] = now
        row["updated_at"] = now
        self.init_storage()
        df = self._read_df()
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        self._write_df(df)
        return normalize_lead_row(row)

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        for r in self.list_leads():
            if str(r.get("lead_id")) == str(lead_id):
                return r
        return None

    def list_leads(self) -> List[Dict[str, Any]]:
        df = self._read_df()
        out: List[Dict[str, Any]] = []
        for rec in df.to_dict(orient="records"):
            out.append(normalize_lead_row(rec))
        return out

    def update_lead(self, lead_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        leads = self.list_leads()
        updated: Optional[Dict[str, Any]] = None
        for i, r in enumerate(leads):
            if str(r.get("lead_id")) == str(lead_id):
                merged = dict(r)
                for k, v in patch.items():
                    if k in LEAD_COLUMNS and k != "lead_id":
                        merged[k] = v
                merged["updated_at"] = utc_now_iso()
                leads[i] = normalize_lead_row(merged)
                updated = leads[i]
                break
        if updated is not None:
            self.sync_leads(leads)
        return updated

    def delete_lead(self, lead_id: str) -> bool:
        leads = self.list_leads()
        new_list = [r for r in leads if str(r.get("lead_id")) != str(lead_id)]
        if len(new_list) == len(leads):
            return False
        self.sync_leads(new_list)
        return True

    def update_status(self, lead_id: str, status: str) -> Optional[Dict[str, Any]]:
        return self.update_lead(lead_id, {"status": status})

    def sync_leads(self, leads: List[Dict[str, Any]]) -> None:
        normalized = [row_for_write(x) for x in leads]
        for r in normalized:
            if not r.get("created_at"):
                r["created_at"] = utc_now_iso()
            r["updated_at"] = utc_now_iso()
        df = pd.DataFrame(normalized, columns=LEAD_COLUMNS)
        self._write_df(df)
