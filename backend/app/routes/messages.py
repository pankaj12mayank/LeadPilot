from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_app_roles
from backend.app.schemas.message import MessageResponse
from backend.services import email_service, history_service, lead_orm_service, message_service, status_history_service
from backend.settings.lead_schema import utc_now_iso
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"], dependencies=[Depends(require_app_roles("admin", "user"))])


def _subject_for_lead(lead) -> str:
    ai = lead_orm_service.lead_to_ai_dict(lead)
    return message_service.build_subject(ai)


@router.post("/generate/{lead_id}", response_model=MessageResponse)
def generate_message(
    lead_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MessageResponse:
    row = lead_orm_service.get_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    ai = lead_orm_service.lead_to_ai_dict(row)
    subject = message_service.build_subject(ai)
    msg_lead = {**ai, "subject": subject}
    text = message_service.build_outreach_message(msg_lead)
    row.personalized_message = text
    row.updated_at = utc_now_iso()
    # Draft only: do not change pipeline status (e.g. avoid implying "sent" before SMTP is configured).
    db.commit()
    try:
        history_service.record_event(
            lead_id,
            "message.generated",
            {"length": len(text or ""), "draft_only": True},
            user["id"],
        )
    except Exception:
        logger.exception("message.generate: meta history write failed (lead already saved)")
    final = lead_orm_service.get_lead(db, lead_id) or row
    return MessageResponse(
        lead_id=lead_id,
        message=str(final.personalized_message or ""),
        email=str(final.email or ""),
        subject=subject,
        status=str(final.status or ""),
    )


@router.post("/send/{lead_id}", response_model=MessageResponse)
def send_message(
    lead_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MessageResponse:
    row = lead_orm_service.get_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    body = str(row.personalized_message or "")
    to_addr = str(row.email or "").strip()
    if not to_addr:
        raise HTTPException(status_code=400, detail="Lead has no email; cannot send")
    subj = _subject_for_lead(row)
    # Release ORM transaction before email_history (same SQLite file as leads).
    db.commit()
    ok = email_service.send_email(
        to_addr, subj, body, lead_id=lead_id, record_history=True
    )
    row = lead_orm_service.get_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    prev = str(row.status or "")
    final_row = row
    if ok and prev not in ("message_sent", "contacted"):
        row.status = "message_sent"
        row.last_contacted_at = utc_now_iso()
        row.updated_at = utc_now_iso()
    db.commit()
    try:
        history_service.record_event(
            lead_id,
            "message.send_requested",
            {"to": to_addr, "success": ok},
            user["id"],
        )
        if ok and prev not in ("message_sent", "contacted"):
            status_history_service.record_change(lead_id, prev or "new", "message_sent")
    except Exception:
        logger.exception("message.send: meta history write failed (lead row already committed)")
    if ok and prev not in ("message_sent", "contacted"):
        final_row = lead_orm_service.get_lead(db, lead_id) or row
    return MessageResponse(
        lead_id=lead_id,
        message=body,
        email=to_addr,
        subject=subj,
        status=str(final_row.status or ""),
    )


@router.get("/{lead_id}", response_model=MessageResponse)
def get_message(
    lead_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> MessageResponse:
    row = lead_orm_service.get_lead(db, lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return MessageResponse(
        lead_id=lead_id,
        message=str(row.personalized_message or ""),
        email=str(row.email or ""),
        subject=_subject_for_lead(row),
        status=str(row.status or ""),
    )
