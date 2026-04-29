from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from backend.leadpilot.linkedin_session_cache import session_info_dict
from backend.services import analytics_service, company_service, lead_orm_service, runtime_settings, settings_service
from database.orm.bootstrap import get_session_factory, init_sa_tables
from database.orm.models import Company, CompanyEnrichment


def _db():
    Session = get_session_factory()
    return Session()


def _company_rows(*, keyword: str, source: str, min_score: float) -> list[dict]:
    db = _db()
    try:
        stmt = (
            select(Company, CompanyEnrichment)
            .join(CompanyEnrichment, CompanyEnrichment.company_id == Company.id, isouter=True)
            .order_by(CompanyEnrichment.score.desc().nullslast(), Company.last_updated.desc())
            .limit(500)
        )
        out: list[dict] = []
        for c, e in db.execute(stmt).all():
            if keyword:
                kw = keyword.lower()
                if kw not in (c.company_name or "").lower() and kw not in (c.domain or "").lower():
                    continue
            if source and source != "all" and (c.source or "").lower() != source:
                continue
            score = float(getattr(e, "score", 0) or 0)
            if score < min_score:
                continue
            out.append(
                {
                    "company_id": c.id,
                    "company": c.company_name or "",
                    "website": c.website or "",
                    "source": c.source or "",
                    "signals": {
                        "hiring": bool(getattr(e, "signal_hiring", 0)),
                        "scaling": bool(getattr(e, "signal_scaling", 0)),
                        "content_gap": bool(getattr(e, "signal_content_gap", 0)),
                        "ads_gap": bool(getattr(e, "signal_ads_gap", 0)),
                    },
                    "score": score,
                    "priority": str(getattr(e, "priority", "") or ""),
                }
            )
        return out
    finally:
        db.close()


def _lead_rows(search: str, limit: int = 100):
    db = _db()
    try:
        leads = lead_orm_service.list_leads_filtered(
            db,
            search=(search or None),
            sort="created_at_desc",
            offset=0,
            limit=limit,
        )
        out = []
        for x in leads:
            out.append(
                {
                    "name": x.full_name or "",
                    "role": x.title or "",
                    "company": x.company_name or "",
                    "score": float(x.score or 0),
                    "signals": {
                        "hiring": bool(getattr(x, "signal_hiring", 0)),
                        "scaling": bool(getattr(x, "signal_scaling", 0)),
                        "content_gap": bool(getattr(x, "signal_content_gap", 0)),
                        "ads_gap": bool(getattr(x, "signal_ads_gap", 0)),
                    },
                    "message": (x.personalized_message or x.solution_text or ""),
                }
            )
        return out
    finally:
        db.close()


def _admin_stats() -> dict:
    db = _db()
    try:
        total_companies = int(db.scalar(select(func.count(Company.id))) or 0)
    finally:
        db.close()
    dash = analytics_service.dashboard(use_cache=True)
    return {
        "total_companies": total_companies,
        "total_leads": int(dash.get("total_leads") or 0),
        "hot_leads": int(dash.get("hot_leads") or 0),
    }


def _render_dashboard():
    stats = _admin_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Companies", stats["total_companies"])
    c2.metric("Total Leads", stats["total_leads"])
    c3.metric("Hot Leads", stats["hot_leads"])


def _render_mode_selector():
    st.subheader("Mode Selector")
    mode = st.radio("Choose Mode", ["LinkedIn", "Explorer"], horizontal=True)
    if mode == "LinkedIn":
        sess = session_info_dict()
        st.info("LinkedIn Mode uses your existing manual LinkedIn capture flow.")
        st.write(
            {
                "within_policy": sess.get("within_policy"),
                "policy_days": sess.get("policy_days"),
                "last_verified_at": sess.get("last_verified_at"),
                "message": sess.get("message"),
            }
        )
    else:
        st.success("Explorer Mode enabled. Use filters on Explorer page below.")


def _render_explorer():
    st.subheader("Explorer")
    c1, c2, c3 = st.columns([2, 1, 1])
    keyword = c1.text_input("Keyword", value="")
    source = c2.selectbox("Source", ["all", "manual", "yc", "job_board", "local", "crunchbase", "builtwith"], index=0)
    min_score = c3.slider("Min Score", 0, 100, 0)
    rows = _company_rows(keyword=keyword.strip(), source=source, min_score=float(min_score))
    table = []
    for r in rows:
        table.append(
            {
                "company": r["company"],
                "website": r["website"],
                "source": r["source"],
                "signals": ", ".join([k for k, v in r["signals"].items() if v]) or "none",
                "score": round(float(r["score"]), 2),
                "priority": r["priority"],
            }
        )
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def _render_leads():
    st.subheader("Lead View")
    q = st.text_input("Search leads", value="")
    rows = _lead_rows(q.strip(), limit=150)
    table = []
    for r in rows:
        table.append(
            {
                "name": r["name"],
                "role": r["role"],
                "company": r["company"],
                "score": round(float(r["score"]), 2),
                "signals": ", ".join([k for k, v in r["signals"].items() if v]) or "none",
                "message": (r["message"] or "")[:200],
            }
        )
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def _render_admin():
    st.subheader("Admin Panel")
    stats = _admin_stats()
    st.write({"total_companies": stats["total_companies"], "total_leads": stats["total_leads"], "hot_leads": stats["hot_leads"]})

    cfg = runtime_settings.get_admin_config()
    sw = cfg.get("scoring_weights") or {}
    tf = cfg.get("targeting") or {}
    src_cfg = cfg.get("sources") or {}
    with st.form("admin_controls_form"):
        st.markdown("#### Scoring Config")
        c1, c2, c3, c4, c5 = st.columns(5)
        role = c1.number_input("role_relevance", min_value=1, max_value=100, value=int(sw.get("role_weight") or 40))
        size = c2.number_input("company_size", min_value=1, max_value=100, value=int(sw.get("company_size_weight") or 20))
        sig = c3.number_input("signals", min_value=1, max_value=100, value=int(sw.get("signal_weight") or 35))
        data = c4.number_input("data_completeness", min_value=1, max_value=100, value=int(sw.get("data_weight") or 25))
        base = c5.number_input("base_factor_mix", min_value=1, max_value=100, value=int(sw.get("base_factor_mix") or 10))

        st.markdown("#### Targeting Filters")
        min_company_score = st.slider("min_company_score", 0, 100, int(tf.get("min_company_score") or 70))
        allowed_sources = st.multiselect(
            "allowed_sources",
            options=["manual", "yc", "job_board", "local", "crunchbase", "builtwith"],
            default=list(src_cfg.get("allowed_sources") or runtime_settings.get_enabled_ingestion_sources()),
        )
        pref_locations = st.text_input("preferred_locations (comma-separated)", value=",".join(tf.get("preferred_locations") or []))
        pref_keywords = st.text_input("preferred_keywords (comma-separated)", value=",".join(tf.get("preferred_keywords") or []))

        ok = st.form_submit_button("Save Admin Config")
        if ok:
            settings_service.patch_settings(
                {
                    "admin_config": {
                        "scoring_weights": {
                            "role_weight": int(role),
                            "company_size_weight": int(size),
                            "signal_weight": int(sig),
                            "data_weight": int(data),
                            "base_factor_mix": int(base),
                        },
                        "targeting": {
                            "min_company_score": int(min_company_score),
                            "preferred_locations": [x.strip() for x in pref_locations.split(",") if x.strip()],
                            "preferred_keywords": [x.strip() for x in pref_keywords.split(",") if x.strip()],
                        },
                        "sources": {
                            **src_cfg,
                            "allowed_sources": list(allowed_sources),
                        },
                    }
                }
            )
            st.success("Admin config saved.")


def main():
    st.set_page_config(page_title="LeadPilot Client UI", layout="wide")
    st.title("LeadPilot - Basic Client UI")
    init_sa_tables()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "Mode Selector", "Explorer", "Lead View", "Admin Panel"])
    with tab1:
        _render_dashboard()
    with tab2:
        _render_mode_selector()
    with tab3:
        _render_explorer()
    with tab4:
        _render_leads()
    with tab5:
        _render_admin()


if __name__ == "__main__":
    main()
