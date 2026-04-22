from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_current_user
from backend.services import analytics_engine, analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Legacy combined dashboard (unscoped + CRM rollups)."""
    return analytics_service.dashboard()


@router.get("/overview")
def analytics_overview(
    _user: dict = Depends(get_current_user),
    period: Optional[str] = Query(
        None,
        description="today | 7d | 30d | 90d | all (ignored when from+to are set)",
    ),
    date_from: Optional[str] = Query(None, alias="from", description="Custom range start (YYYY-MM-DD or ISO)"),
    date_to: Optional[str] = Query(None, alias="to", description="Custom range end (YYYY-MM-DD or ISO)"),
) -> Dict[str, Any]:
    """
    KPIs plus chart-ready payloads (bar, pie, line, funnel, heatmap) for the cohort
    defined by ``created_at`` in the selected window.
    """
    return analytics_engine.overview(period, date_from, date_to)


@router.get("/platforms")
def analytics_platforms(
    _user: dict = Depends(get_current_user),
    period: Optional[str] = Query(None, description="today | 7d | 30d | 90d | all"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
) -> Dict[str, Any]:
    return analytics_engine.platforms_chart(period, date_from, date_to)


@router.get("/status")
def analytics_status(
    _user: dict = Depends(get_current_user),
    period: Optional[str] = Query(None, description="today | 7d | 30d | 90d | all"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
) -> Dict[str, Any]:
    return analytics_engine.status_chart(period, date_from, date_to)


@router.get("/conversion")
def analytics_conversion(
    _user: dict = Depends(get_current_user),
    period: Optional[str] = Query(None, description="today | 7d | 30d | 90d | all"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
) -> Dict[str, Any]:
    return analytics_engine.conversion_view(period, date_from, date_to)


@router.get("/timeline")
def analytics_timeline(
    _user: dict = Depends(get_current_user),
    period: Optional[str] = Query(None, description="today | 7d | 30d | 90d | all"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
) -> Dict[str, Any]:
    return analytics_engine.timeline(period, date_from, date_to)


@router.get("/funnel")
def analytics_funnel(
    _user: dict = Depends(get_current_user),
    period: Optional[str] = Query(None, description="today | 7d | 30d | 90d | all"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
) -> Dict[str, Any]:
    return analytics_engine.funnel(period, date_from, date_to)
