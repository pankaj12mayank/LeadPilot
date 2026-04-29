from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.api.deps import get_current_user, require_app_roles
from backend.modules.csv_exporter.service import export_leads_csv
from backend.services import lead_orm_service
from database.orm.models import Lead, LeadPack, LeadPackPurchase

router = APIRouter(prefix="/exports", tags=["exports"], dependencies=[Depends(require_app_roles("admin", "buyer"))])


@router.get("/leads.csv")
def export_leads_csv_file(_user: dict = Depends(get_current_user)) -> FileResponse:
    """Download all leads as CSV (written under ``exports/``)."""
    path = export_leads_csv()
    return FileResponse(
        path,
        filename=os.path.basename(path),
        media_type="text/csv",
    )


PLAN_LIMITS: dict[str, int] = {
    "starter": 100,
    "growth": 500,
    "pro": 2000,
}

ROLE_LIMITS: dict[str, int] = {
    "buyer": 2000,
    "user": 10000,
    "admin": 100000,
}


class ExportRequest(BaseModel):
    format: str = Field(default="csv")
    ids: list[str] = Field(default_factory=list)
    search: str | None = None
    status: str | None = None
    tier: str | None = None
    platform: str | None = None
    plan_tier: str = Field(default="starter")


def _rows_for_export(user: dict[str, Any], body: ExportRequest) -> list[dict[str, Any]]:
    from database.orm.bootstrap import get_session_factory

    Session = get_session_factory()
    db = Session()
    try:
        rows = lead_orm_service.list_leads_for_export(
            db,
            ids=body.ids or None,
            search=body.search,
            status=body.status,
            tier=body.tier,
            platform=body.platform,
            viewer_user=user,
        )
        role = str(user.get("role") or "user").strip().lower()
        role_limit = ROLE_LIMITS.get(role, 1000)
        plan_limit = PLAN_LIMITS.get(str(body.plan_tier or "starter").strip().lower(), PLAN_LIMITS["starter"])
        max_rows = min(role_limit, plan_limit if role == "buyer" else role_limit)
        clipped = rows[:max_rows]
        return [lead_orm_service.lead_to_response_dict(x) for x in clipped]
    finally:
        db.close()


@router.post("/leads")
def export_filtered_leads(body: ExportRequest, user: dict = Depends(get_current_user)) -> FileResponse:
    rows = _rows_for_export(user, body)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = "xlsx" if str(body.format or "csv").strip().lower() == "xlsx" else "csv"
    out_dir = Path(os.getenv("EXPORTS_DIR") or os.path.join(os.getcwd(), "exports"))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"lead_export_{stamp}.{ext}"
    if ext == "xlsx":
        pd.DataFrame(rows).to_excel(path, index=False)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        with open(path, "w", encoding="utf-8", newline="") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            else:
                f.write("")
        media_type = "text/csv"
    return FileResponse(str(path), filename=path.name, media_type=media_type)


@router.get("/packs")
def list_lead_packs(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from database.orm.bootstrap import get_session_factory

    Session = get_session_factory()
    db = Session()
    try:
        rows = list(db.scalars(select(LeadPack).where(LeadPack.is_active == 1).order_by(LeadPack.created_at.desc())))
        out = []
        for row in rows:
            try:
                lead_ids = json.loads(row.lead_ids_json or "[]")
            except Exception:
                lead_ids = []
            out.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "description": row.description or "",
                    "price_usd": float(row.price_usd or 0),
                    "lead_count": len(lead_ids) if isinstance(lead_ids, list) else 0,
                    "created_at": row.created_at,
                }
            )
        return {"items": out, "role": str(user.get("role") or "buyer")}
    finally:
        db.close()


@router.get("/packs/{pack_id}/preview")
def preview_lead_pack(pack_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from database.orm.bootstrap import get_session_factory

    Session = get_session_factory()
    db = Session()
    try:
        pack = db.get(LeadPack, int(pack_id))
        if not pack or not int(pack.is_active or 0):
            raise HTTPException(status_code=404, detail="Lead pack not found")
        lead_ids = json.loads(pack.lead_ids_json or "[]")
        lead_rows = list(db.scalars(select(Lead).where(Lead.id.in_(lead_ids[:20])))) if isinstance(lead_ids, list) else []
        preview = [
            {
                "id": x.id,
                "full_name": x.full_name,
                "title": x.title,
                "company_name": x.company_name,
                "score": float(x.score or 0),
                "tier": x.tier,
            }
            for x in lead_rows
        ]
        return {
            "pack": {
                "id": pack.id,
                "name": pack.name,
                "description": pack.description or "",
                "price_usd": float(pack.price_usd or 0),
                "lead_count": len(lead_ids) if isinstance(lead_ids, list) else 0,
            },
            "preview": preview,
            "can_download": str(user.get("role") or "buyer").lower() == "admin",
        }
    finally:
        db.close()


@router.post("/packs/{pack_id}/purchase")
def purchase_lead_pack(pack_id: int, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from database.orm.bootstrap import get_session_factory

    role = str(user.get("role") or "buyer").strip().lower()
    if role not in {"buyer", "admin"}:
        raise HTTPException(status_code=403, detail="Only buyer/admin can purchase packs")
    Session = get_session_factory()
    db = Session()
    try:
        pack = db.get(LeadPack, int(pack_id))
        if not pack or not int(pack.is_active or 0):
            raise HTTPException(status_code=404, detail="Lead pack not found")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        row = LeadPackPurchase(
            pack_id=pack.id,
            buyer_user_id=str(user.get("id") or ""),
            amount_usd=float(pack.price_usd or 0),
            status="completed",
            purchased_at=now,
        )
        db.add(row)
        db.commit()
        return {"ok": True, "purchase_id": row.id, "pack_id": pack.id, "amount_usd": float(pack.price_usd or 0)}
    finally:
        db.close()


@router.get("/packs/{pack_id}/download")
def download_purchased_pack(pack_id: int, user: dict = Depends(get_current_user)) -> FileResponse:
    from database.orm.bootstrap import get_session_factory

    role = str(user.get("role") or "buyer").strip().lower()
    Session = get_session_factory()
    db = Session()
    try:
        pack = db.get(LeadPack, int(pack_id))
        if not pack or not int(pack.is_active or 0):
            raise HTTPException(status_code=404, detail="Lead pack not found")
        if role != "admin":
            purchase = db.scalar(
                select(LeadPackPurchase)
                .where(LeadPackPurchase.pack_id == pack.id, LeadPackPurchase.buyer_user_id == str(user.get("id") or ""))
                .limit(1)
            )
            if purchase is None:
                raise HTTPException(status_code=403, detail="Purchase required")
        lead_ids = json.loads(pack.lead_ids_json or "[]")
        lead_rows = list(db.scalars(select(Lead).where(Lead.id.in_(lead_ids)))) if isinstance(lead_ids, list) else []
        rows = [lead_orm_service.lead_to_response_dict(x) for x in lead_rows]
        out_dir = Path(os.getenv("EXPORTS_DIR") or os.path.join(os.getcwd(), "exports"))
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"lead_pack_{pack.id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            else:
                f.write("")
        return FileResponse(str(path), filename=path.name, media_type="text/csv")
    finally:
        db.close()
