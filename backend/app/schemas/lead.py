from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from database.orm.models import Lead as LeadORM
from backend.services.lead_statuses import assert_status_writable


class LeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(..., min_length=1, max_length=255)
    source_platform: str = Field(..., min_length=1, max_length=64)
    title: str = ""
    company_name: str = ""
    company_website: str = ""
    linkedin_url: str = ""
    email: str = ""
    phone: str = ""
    company_size: str = ""
    industry: str = ""
    location: str = ""
    notes: str = ""
    status: str = "new"
    personalized_message: str = ""
    followup_message: str = ""
    last_contacted_at: str = ""
    follow_up_reminder_at: str = ""

    @model_validator(mode="after")
    def require_contact_vector(self) -> "LeadCreate":
        if not (
            (self.linkedin_url or "").strip()
            or (self.company_website or "").strip()
            or (self.email or "").strip()
        ):
            raise ValueError("Provide at least one of: linkedin_url, company_website, or email")
        return self

    @field_validator("status")
    @classmethod
    def v_status(cls, v: str) -> str:
        return assert_status_writable(v or "new")


class LeadUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    source_platform: Optional[str] = None
    notes: Optional[str] = None
    score: Optional[float] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    personalized_message: Optional[str] = None
    followup_message: Optional[str] = None
    last_contacted_at: Optional[str] = None
    follow_up_reminder_at: Optional[str] = None

    @field_validator("status")
    @classmethod
    def v_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return assert_status_writable(v)


class StatusUpdate(BaseModel):
    status: str = Field(..., min_length=1)

    @field_validator("status")
    @classmethod
    def v_status(cls, v: str) -> str:
        return assert_status_writable(v)


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    title: str = ""
    company_name: str = ""
    company_website: str = ""
    linkedin_url: str = ""
    email: str = ""
    phone: str = ""
    company_size: str = ""
    industry: str = ""
    location: str = ""
    source_platform: str = ""
    notes: str = ""
    score: float = 0.0
    tier: str = ""
    status: str = ""
    personalized_message: str = ""
    followup_message: str = ""
    last_contacted_at: str = ""
    follow_up_reminder_at: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_orm_lead(cls, lead: LeadORM) -> "LeadResponse":
        return cls(
            id=lead.id,
            full_name=lead.full_name,
            title=lead.title or "",
            company_name=lead.company_name or "",
            company_website=lead.company_website or "",
            linkedin_url=lead.linkedin_url or "",
            email=lead.email or "",
            phone=lead.phone or "",
            company_size=lead.company_size or "",
            industry=lead.industry or "",
            location=lead.location or "",
            source_platform=lead.source_platform or "",
            notes=lead.notes or "",
            score=float(lead.score or 0),
            tier=lead.tier or "",
            status=lead.status or "",
            personalized_message=lead.personalized_message or "",
            followup_message=lead.followup_message or "",
            last_contacted_at=getattr(lead, "last_contacted_at", "") or "",
            follow_up_reminder_at=getattr(lead, "follow_up_reminder_at", "") or "",
            created_at=lead.created_at or "",
            updated_at=lead.updated_at or "",
        )


class PaginatedLeadsResponse(BaseModel):
    items: List[LeadResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 25
    pages: int = 0


class BulkDeleteRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    deleted: int


class LeadExportRequest(BaseModel):
    """When ``ids`` is set, export only those rows (must still exist). Otherwise export using filters."""

    ids: Optional[List[str]] = None
    search: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = None
    platform: Optional[str] = None


class BulkImportRequest(BaseModel):
    leads: List[LeadCreate] = Field(default_factory=list)


class BulkImportResponse(BaseModel):
    created: int
    errors: List[str] = Field(default_factory=list)
