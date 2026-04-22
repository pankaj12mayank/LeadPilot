"""Fill AI subject + message for leads that are missing personalized_message."""

from __future__ import annotations

from sqlalchemy import select

from database.orm.bootstrap import get_session_factory
from database.orm.models import Lead
from backend.services import lead_orm_service, message_service
from backend.settings.lead_schema import utc_now_iso
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def generate_for_all_pending() -> int:
    Session = get_session_factory()
    db = Session()
    changed = 0
    try:
        for lead in db.scalars(select(Lead)):
            if str(lead.personalized_message or "").strip():
                continue
            ai = lead_orm_service.lead_to_ai_dict(lead)
            subject = message_service.build_subject(ai)
            msg_lead = {**ai, "subject": subject}
            lead.personalized_message = message_service.build_outreach_message(msg_lead)
            lead.status = "ready"
            lead.updated_at = utc_now_iso()
            changed += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    logger.info("bulk_message_service: generated messages for %s lead(s)", changed)
    return changed
