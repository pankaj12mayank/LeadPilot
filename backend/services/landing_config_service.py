from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.ollama_messaging.ollama_service import OllamaGenerateService
from backend.services import external_llm_service, runtime_settings
from database.orm.bootstrap import get_session_factory, init_sa_tables
from database.orm.models import LandingConfigState


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_sections() -> list[dict[str, Any]]:
    return [
        {"id": "hero", "label": "Hero Section", "enabled": True, "order": 1, "heading": "Lead generation that actually compounds", "subheading": "Discover, qualify, and prioritize leads from multiple trusted sources.", "body": "LeadPilot helps teams find better-fit accounts and convert faster with AI-backed prioritization.", "image_url": "", "cta_primary_text": "Login", "cta_primary_link": "/login", "cta_secondary_text": "Get Leads", "cta_secondary_link": "/search-leads"},
        {"id": "problem", "label": "Problem Section", "enabled": True, "order": 2, "heading": "Why lead generation breaks", "subheading": "Most teams lose time on low-quality data.", "body": "Disconnected tools, stale lists, and no signal-based prioritization create wasted effort.", "items": ["Scattered sources", "Low quality leads", "No reliable scoring"]},
        {"id": "solution", "label": "Solution Section", "enabled": True, "order": 3, "heading": "One operational system", "subheading": "From data capture to conversion in one loop.", "body": "LeadPilot connects source ingestion, qualification, scoring, and execution with admin controls."},
        {"id": "features", "label": "Features Section", "enabled": True, "order": 4, "heading": "Core Features", "subheading": "", "body": "", "items": ["Multi-source leads", "AI qualification", "Config-driven scoring", "Export and buyer workflows"]},
        {"id": "how_it_works", "label": "How It Works", "enabled": True, "order": 5, "heading": "How it works", "items": ["Pick mode", "Fetch accounts", "Qualify with AI", "Prioritize", "Convert"]},
        {"id": "data_sources", "label": "Data Sources Section", "enabled": True, "order": 6, "heading": "Data Sources", "items": ["LinkedIn", "Google Maps", "IndiaMart", "Justdial", "eWorldTrade", "Global Sources", "ThomasNet", "Yelp", "Faire"]},
        {"id": "ai_intelligence", "label": "AI Intelligence Section", "enabled": True, "order": 7, "heading": "AI Intelligence", "body": "Generate summaries, problem statements, opportunity insights, and actionable scores."},
        {"id": "use_cases", "label": "Use Cases", "enabled": True, "order": 8, "heading": "Built for teams that sell", "items": ["Agencies", "Freelancers", "Sales teams"]},
        {"id": "testimonials", "label": "Testimonials", "enabled": True, "order": 9, "heading": "Loved by operators", "items": ["Lead quality improved in 2 weeks.", "Our outbound focus finally became predictable."]},
        {"id": "pricing", "label": "Pricing Section", "enabled": True, "order": 10, "heading": "Pricing", "items": ["Free", "Starter", "Pro", "Agency"]},
        {"id": "faq", "label": "FAQ Section", "enabled": True, "order": 11, "heading": "FAQ", "items": ["Can I control sources per plan?", "Does AI fallback safely?", "Can I export filtered leads?"]},
        {"id": "cta", "label": "CTA Section", "enabled": True, "order": 12, "heading": "Ready to run a better pipeline?", "body": "Start with your current team and scale cleanly.", "cta_primary_text": "Start now", "cta_primary_link": "/login"},
        {"id": "footer", "label": "Footer", "enabled": True, "order": 13, "heading": "LeadPilot", "body": "Lead operations platform"},
    ]


def default_landing_config() -> dict[str, Any]:
    return {
        "sections": _default_sections(),
        "seo": {
            "title": "LeadPilot | AI Lead Growth System",
            "description": "LeadPilot helps you discover, qualify, and convert better leads with AI and multi-source data.",
            "keywords": ["lead generation", "AI lead scoring", "b2b leads", "sales pipeline"],
            "og_title": "LeadPilot",
            "og_description": "AI-assisted lead operations.",
            "og_image": "",
            "structured_data_type": "SoftwareApplication",
        },
        "geo": {
            "enabled": True,
            "location_label": "",
            "keyword_focus": "AI lead generation",
        },
        "theme": {
            "default_theme": "system",
            "brand_colors": {"primary": "#d97706", "accent": "#059669", "background_light": "#f8fafc", "background_dark": "#0b1120"},
            "font_family": "Inter, system-ui, sans-serif",
        },
        "analytics": {
            "enabled": True,
            "track_page_views": True,
            "track_cta_clicks": True,
            "track_conversions": True,
        },
    }


def get_landing_config() -> dict[str, Any]:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        row = db.query(LandingConfigState).order_by(LandingConfigState.id.desc()).first()
        if row is None:
            cfg = default_landing_config()
            row = LandingConfigState(config_json=json.dumps(cfg, ensure_ascii=True), version=1, updated_at=_now())
            db.add(row)
            db.commit()
            return cfg
        parsed = json.loads(str(row.config_json or "{}"))
        return parsed if isinstance(parsed, dict) else default_landing_config()
    except Exception:
        return default_landing_config()
    finally:
        db.close()


def save_landing_config(cfg: dict[str, Any]) -> dict[str, Any]:
    init_sa_tables()
    Session = get_session_factory()
    db = Session()
    try:
        row = db.query(LandingConfigState).order_by(LandingConfigState.id.desc()).first()
        payload = json.dumps(cfg, ensure_ascii=True)
        if row is None:
            row = LandingConfigState(config_json=payload, version=1, updated_at=_now())
            db.add(row)
        else:
            row.config_json = payload
            row.version = int(row.version or 1) + 1
            row.updated_at = _now()
        db.commit()
        return cfg
    finally:
        db.close()


def generate_ai_content(*, location: str = "", keyword_focus: str = "") -> dict[str, Any]:
    provider = runtime_settings.get_ai_provider()
    location = str(location or "").strip()
    keyword_focus = str(keyword_focus or "").strip() or "AI lead generation"
    prompt = (
        "Return strict JSON with keys: hero_heading, hero_subheading, cta_text, problem_points, feature_points.\n"
        "Tone: human, premium, clear, conversion-focused.\n"
        f"location={location}\n"
        f"keyword_focus={keyword_focus}\n"
    )
    system = "You write high-converting SaaS landing page copy."
    raw: str | None = None
    if provider == "ollama" and runtime_settings.get_use_ollama():
        try:
            raw = OllamaGenerateService(timeout_seconds=12.0, max_retries=1).generate_text(runtime_settings.get_model_name(), prompt, system=system)
        except Exception:
            raw = None
    elif provider == "external_api" and runtime_settings.get_external_api_key():
        raw = external_llm_service.chat_completion_json(system=system, user=prompt)
    if raw:
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    loc_phrase = f" in {location}" if location else ""
    return {
        "hero_heading": f"Find high-intent B2B leads{loc_phrase} without guesswork",
        "hero_subheading": "LeadPilot combines trusted sources, AI qualification, and practical scoring so your team spends time on the right accounts.",
        "cta_text": "Start generating leads",
        "problem_points": ["Prospect lists are outdated or noisy", "Teams waste time on unqualified accounts", "No consistent way to prioritize outreach"],
        "feature_points": ["Multi-source data ingestion", "AI qualification and opportunity insights", "Config-driven scoring and queue execution"],
    }
