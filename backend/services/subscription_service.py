from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_

from database.orm.bootstrap import get_session_factory
from database.orm.models import (
    Plan, Subscription, Transaction, UserUsage, User,
    PaymentGatewayConfig, EmailConfig, EmailTemplate,
)
import config
from backend.utils.logger import get_logger

logger = get_logger(__name__)


_DEFAULT_PLANS = [
    {
        "name": "Free",
        "description": "Get started with basic lead management. Free forever.",
        "monthly_price": 0.0,
        "currency": "usd",
        "features": ["Up to 50 leads", "Basic lead scoring", "Email outreach", "Standard support"],
        "highlighted": False,
        "is_free": True,
        "lead_limit": 50,
        "channel_access": {"email": True},
        "sort_order": 0,
    },
    {
        "name": "Starter",
        "description": "Perfect for individuals and small teams getting started.",
        "monthly_price": 29.0,
        "currency": "usd",
        "features": ["Up to 100 leads", "Basic lead scoring", "Email outreach", "LinkedIn outreach", "Priority support"],
        "highlighted": True,
        "is_free": False,
        "lead_limit": 100,
        "channel_access": {"email": True, "linkedin": True},
        "sort_order": 1,
    },
    {
        "name": "Pro",
        "description": "For growing teams that need more leads and advanced features.",
        "monthly_price": 79.0,
        "currency": "usd",
        "features": ["Up to 500 leads", "Advanced lead scoring", "Email + LinkedIn outreach", "API access", "Priority support"],
        "highlighted": False,
        "is_free": False,
        "lead_limit": 500,
        "channel_access": {"email": True, "linkedin": True, "api": True},
        "sort_order": 2,
    },
    {
        "name": "Custom",
        "description": "Enterprise-grade solution for large teams with custom needs.",
        "monthly_price": 199.0,
        "currency": "usd",
        "features": ["Up to 2000 leads", "Advanced lead scoring", "All outreach channels", "API access", "Dedicated support", "Custom integrations"],
        "highlighted": False,
        "is_free": False,
        "lead_limit": 2000,
        "channel_access": {"email": True, "linkedin": True, "api": True, "phone": True},
        "sort_order": 3,
    },
]


def seed_default_plans() -> None:
    """Create/upsert 4 default plans: Free, Starter, Pro, Custom."""
    Session = get_session_factory()
    db = Session()
    try:
        now = _now()
        for p_data in _DEFAULT_PLANS:
            existing = db.scalar(select(Plan).where(Plan.name == p_data["name"]))
            if existing:
                for key in ("description", "monthly_price", "currency", "highlighted", "lead_limit", "sort_order"):
                    if key in p_data:
                        setattr(existing, key, float(p_data[key]) if key == "monthly_price" else int(p_data[key]) if key in ("lead_limit", "sort_order") else p_data[key])
                for key in ("highlighted", "is_free"):
                    if key in p_data:
                        setattr(existing, key, int(bool(p_data[key])))
                existing.features = json.dumps(p_data.get("features", []))
                existing.channel_access = json.dumps(p_data.get("channel_access", {}))
                existing.updated_at = now
            else:
                p = Plan(
                    id=str(uuid.uuid4()),
                    name=p_data["name"],
                    description=p_data.get("description", ""),
                    monthly_price=float(p_data.get("monthly_price", 0)),
                    currency=p_data.get("currency", "usd"),
                    features=json.dumps(p_data.get("features", [])),
                    highlighted=int(bool(p_data.get("highlighted", False))),
                    is_free=int(bool(p_data.get("is_free", False))),
                    lead_limit=int(p_data.get("lead_limit", 0)),
                    channel_access=json.dumps(p_data.get("channel_access", {})),
                    stripe_price_id="",
                    razorpay_plan_id="",
                    sort_order=int(p_data.get("sort_order", 0)),
                    is_active=1,
                    created_at=now,
                    updated_at=now,
                )
                db.add(p)
        db.commit()
        logger.info("Seeded/updated 4 default plans")
    finally:
        db.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# ── Plan CRUD ──────────────────────────────────────────────────────────

def list_plans(include_inactive: bool = False) -> List[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        stmt = select(Plan)
        if not include_inactive:
            stmt = stmt.where(Plan.is_active == 1)
        stmt = stmt.order_by(Plan.sort_order)
        rows = list(db.scalars(stmt))
        return [_plan_to_dict(p) for p in rows]
    finally:
        db.close()


def _plan_to_dict(p: Plan) -> Dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description or "",
        "monthly_price": float(p.monthly_price or 0),
        "currency": p.currency or "usd",
        "features": json.loads(p.features or "[]"),
        "highlighted": bool(int(p.highlighted or 0)),
        "is_free": bool(int(p.is_free or 0)),
        "lead_limit": int(p.lead_limit or 0),
        "channel_access": json.loads(p.channel_access or "{}"),
        "stripe_price_id": p.stripe_price_id or "",
        "razorpay_plan_id": p.razorpay_plan_id or "",
        "sort_order": int(p.sort_order or 0),
        "is_active": bool(int(p.is_active or 0)),
        "created_at": p.created_at or "",
        "updated_at": p.updated_at or "",
    }


def create_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        plan = Plan(
            id=str(uuid.uuid4()),
            name=data["name"],
            description=data.get("description", ""),
            monthly_price=float(data.get("monthly_price", 0)),
            currency=data.get("currency", "usd"),
            features=json.dumps(data.get("features", [])),
            highlighted=int(bool(data.get("highlighted", False))),
            is_free=int(bool(data.get("is_free", False))),
            lead_limit=int(data.get("lead_limit", 0)),
            channel_access=json.dumps(data.get("channel_access", {})),
            stripe_price_id=data.get("stripe_price_id", ""),
            razorpay_plan_id=data.get("razorpay_plan_id", ""),
            sort_order=int(data.get("sort_order", 0)),
            is_active=1,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(plan)
        db.commit()
        return _plan_to_dict(plan)
    finally:
        db.close()


def update_plan(plan_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        plan = db.get(Plan, plan_id)
        if not plan:
            return None
        for key in ("name", "description", "currency", "stripe_price_id", "razorpay_plan_id"):
            if key in data:
                setattr(plan, key, data[key])
        for key in ("monthly_price", "lead_limit", "sort_order"):
            if key in data:
                setattr(plan, key, float(data[key]) if key == "monthly_price" else int(data[key]))
        for key in ("highlighted", "is_free", "is_active"):
            if key in data:
                setattr(plan, key, int(bool(data[key])))
        if "features" in data:
            plan.features = json.dumps(data["features"])
        if "channel_access" in data:
            plan.channel_access = json.dumps(data["channel_access"])
        plan.updated_at = _now()
        db.commit()
        return _plan_to_dict(plan)
    finally:
        db.close()


def delete_plan(plan_id: str) -> bool:
    _PROTECTED_PLAN_NAMES = {"Free", "Starter", "Pro", "Custom"}
    Session = get_session_factory()
    db = Session()
    try:
        plan = db.get(Plan, plan_id)
        if not plan:
            return False
        if plan.name in _PROTECTED_PLAN_NAMES:
            logger.warning("Attempted to delete protected plan: %s", plan.name)
            return False
        db.delete(plan)
        db.commit()
        return True
    finally:
        db.close()


# ── Subscription Management ────────────────────────────────────────────

def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = db.scalar(stmt)
        if not sub:
            return None
        plan = db.get(Plan, sub.plan_id)
        usage = db.scalar(
            select(UserUsage).where(UserUsage.subscription_id == sub.id).order_by(UserUsage.updated_at.desc()).limit(1)
        )
        return {
            "id": sub.id,
            "user_id": sub.user_id,
            "plan_id": sub.plan_id,
            "plan_name": plan.name if plan else "Unknown",
            "plan_monthly_price": float(plan.monthly_price) if plan else 0,
            "is_free": bool(int(plan.is_free)) if plan else False,
            "lead_limit": int(plan.lead_limit) if plan else 0,
            "status": sub.status,
            "gateway": sub.gateway,
            "start_date": sub.start_date or "",
            "end_date": sub.end_date or "",
            "auto_renew": bool(int(sub.auto_renew or 0)),
            "leads_consumed": int(usage.leads_consumed) if usage else 0,
            "period_start": usage.period_start if usage else "",
            "period_end": usage.period_end if usage else "",
            "created_at": sub.created_at or "",
        }
    finally:
        db.close()


def create_free_subscription(user_id: str, plan_id: str) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        now = _now()
        period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        sub = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_id=plan_id,
            status="active",
            start_date=now,
            end_date=period_end,
            gateway="free",
            auto_renew=1,
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
        usage = UserUsage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subscription_id=sub.id,
            leads_consumed=0,
            period_start=now,
            period_end=period_end,
            updated_at=now,
        )
        db.add(usage)
        db.commit()
        return {"id": sub.id, "status": "active", "period_end": period_end}
    finally:
        db.close()


def create_pending_subscription(user_id: str, plan_id: str, gateway: str) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        now = _now()
        sub = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_id=plan_id,
            status="pending_payment",
            gateway=gateway,
            auto_renew=1,
            created_at=now,
            updated_at=now,
        )
        db.add(sub)
        db.commit()
        return {"id": sub.id}
    finally:
        db.close()


def activate_subscription(sub_id: str, gateway_sub_id: str = "") -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        sub = db.get(Subscription, sub_id)
        if not sub:
            return False
        now = _now()
        period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        sub.status = "active"
        sub.start_date = now
        sub.end_date = period_end
        if gateway_sub_id:
            if sub.gateway == "stripe":
                sub.stripe_sub_id = gateway_sub_id
            elif sub.gateway == "razorpay":
                sub.razorpay_sub_id = gateway_sub_id
        sub.updated_at = now
        usage = UserUsage(
            id=str(uuid.uuid4()),
            user_id=sub.user_id,
            subscription_id=sub.id,
            leads_consumed=0,
            period_start=now,
            period_end=period_end,
            updated_at=now,
        )
        db.add(usage)
        db.commit()
        return True
    finally:
        db.close()


def cancel_subscription(sub_id: str) -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        sub = db.get(Subscription, sub_id)
        if not sub:
            return False
        sub.status = "cancelled"
        sub.auto_renew = 0
        sub.updated_at = _now()
        db.commit()
        return True
    finally:
        db.close()


def handle_period_expiry(user_id: str) -> Optional[Dict[str, Any]]:
    """Check if user's subscription period ended. If free plan, renew it. If paid, mark expired."""
    sub_data = get_user_subscription(user_id)
    if not sub_data:
        return None
    if sub_data["status"] != "active":
        return sub_data
    now = datetime.now(timezone.utc)
    period_end = sub_data.get("period_end", "")
    if period_end:
        try:
            pe = datetime.fromisoformat(period_end)
            if pe > now:
                return sub_data  # still valid
        except ValueError:
            pass
    # Period expired
    if sub_data["is_free"]:
        renew_free_subscription(user_id)
        return get_user_subscription(user_id)
    Session = get_session_factory()
    db = Session()
    try:
        sub = db.scalar(
            select(Subscription).where(
                and_(Subscription.user_id == user_id, Subscription.id == sub_data["id"])
            )
        )
        if sub:
            sub.status = "expired"
            sub.updated_at = _now()
            db.commit()
    finally:
        db.close()
    sub_data["status"] = "expired"
    return sub_data


def renew_free_subscription(user_id: str) -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        sub = db.scalar(
            select(Subscription)
            .where(and_(Subscription.user_id == user_id, Subscription.gateway == "free"))
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        if not sub:
            return False
        now = _now()
        period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        sub.start_date = now
        sub.end_date = period_end
        sub.status = "active"
        sub.updated_at = now
        usage = UserUsage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subscription_id=sub.id,
            leads_consumed=0,
            period_start=now,
            period_end=period_end,
            updated_at=now,
        )
        db.add(usage)
        db.commit()
        return True
    finally:
        db.close()


# ── Transactions ───────────────────────────────────────────────────────

def create_transaction(
    user_id: str, subscription_id: str, plan_id: str,
    amount: float, currency: str, gateway: str,
    gateway_txn_id: str = "", status: str = "pending",
) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        txn = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subscription_id=subscription_id,
            plan_id=plan_id,
            amount=amount,
            currency=currency,
            gateway=gateway,
            gateway_txn_id=gateway_txn_id,
            status=status,
            created_at=_now(),
        )
        db.add(txn)
        db.commit()
        return {
            "id": txn.id,
            "amount": float(txn.amount),
            "currency": txn.currency,
            "gateway": txn.gateway,
            "status": txn.status,
            "gateway_txn_id": txn.gateway_txn_id,
            "created_at": txn.created_at,
        }
    finally:
        db.close()


def update_transaction_status(txn_id: str, status: str, failure_reason: str = "", invoice_url: str = "") -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        txn = db.get(Transaction, txn_id)
        if not txn:
            return False
        txn.status = status
        if failure_reason:
            txn.failure_reason = failure_reason
        if invoice_url:
            txn.invoice_url = invoice_url
        db.commit()
        return True
    finally:
        db.close()


def list_transactions(
    user_id: Optional[str] = None,
    gateway: Optional[str] = None,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        stmt = select(Transaction).order_by(Transaction.created_at.desc())
        if user_id:
            stmt = stmt.where(Transaction.user_id == user_id)
        if gateway:
            stmt = stmt.where(Transaction.gateway == gateway)
        if status:
            stmt = stmt.where(Transaction.status == status)
        if plan_id:
            stmt = stmt.where(Transaction.plan_id == plan_id)
        if date_from:
            stmt = stmt.where(Transaction.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Transaction.created_at <= date_to)
        stmt = stmt.offset(offset).limit(limit)
        rows = list(db.scalars(stmt))
        result = []
        for t in rows:
            user = db.get(User, t.user_id)
            plan = db.get(Plan, t.plan_id)
            result.append({
                "id": t.id,
                "user_id": t.user_id,
                "user_email": user.email if user else "",
                "user_name": user.email.split("@")[0] if user else "",
                "subscription_id": t.subscription_id,
                "plan_id": t.plan_id,
                "plan_name": plan.name if plan else "Deleted",
                "amount": float(t.amount),
                "currency": t.currency,
                "gateway": t.gateway,
                "gateway_txn_id": t.gateway_txn_id,
                "status": t.status,
                "payment_method": t.payment_method or "",
                "failure_reason": t.failure_reason or "",
                "invoice_url": t.invoice_url or "",
                "created_at": t.created_at or "",
            })
        return result
    finally:
        db.close()


# ── Usage ──────────────────────────────────────────────────────────────

def increment_lead_consumed(user_id: str) -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        usage = db.scalar(
            select(UserUsage)
            .where(UserUsage.user_id == user_id)
            .order_by(UserUsage.updated_at.desc())
            .limit(1)
        )
        if usage:
            usage.leads_consumed = int(usage.leads_consumed) + 1
            usage.updated_at = _now()
            db.commit()
        return True
    finally:
        db.close()


def reset_usage_if_expired(user_id: str) -> Dict[str, Any]:
    sub_data = get_user_subscription(user_id)
    if not sub_data:
        return {"ok": False, "reason": "no_subscription"}
    now = datetime.now(timezone.utc)
    period_end_str = sub_data.get("period_end", "")
    if period_end_str:
        try:
            pe = datetime.fromisoformat(period_end_str)
            if pe > now:
                return {"ok": True, "renewed": False}
        except ValueError:
            pass
    if sub_data.get("is_free"):
        renew_free_subscription(user_id)
        return {"ok": True, "renewed": True}
    return {"ok": False, "reason": "expired_paid"}


# ── Payment Gateway Config ─────────────────────────────────────────────

def get_gateway_config(gateway: str) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        row = db.scalar(
            select(PaymentGatewayConfig).where(PaymentGatewayConfig.gateway == gateway)
        )
        if not row:
            return None
        return {
            "id": row.id,
            "gateway": row.gateway,
            "is_active": bool(int(row.is_active or 0)),
            "publishable_key": row.publishable_key[:12] + "..." if row.publishable_key else "",
            "has_secret": bool(row.secret_key),
            "has_webhook_secret": bool(row.webhook_secret),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    finally:
        db.close()


def save_gateway_config(gateway: str, data: Dict[str, Any]) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        row = db.scalar(
            select(PaymentGatewayConfig).where(PaymentGatewayConfig.gateway == gateway)
        )
        now = _now()
        if row:
            if "publishable_key" in data:
                row.publishable_key = data["publishable_key"]
            if "secret_key" in data:
                row.secret_key = data["secret_key"]
            if "webhook_secret" in data:
                row.webhook_secret = data["webhook_secret"]
            if "is_active" in data:
                row.is_active = int(bool(data["is_active"]))
            row.updated_at = now
        else:
            row = PaymentGatewayConfig(
                id=str(uuid.uuid4()),
                gateway=gateway,
                is_active=int(bool(data.get("is_active", True))),
                publishable_key=data.get("publishable_key", ""),
                secret_key=data.get("secret_key", ""),
                webhook_secret=data.get("webhook_secret", ""),
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        db.commit()
        return {
            "gateway": row.gateway,
            "is_active": bool(int(row.is_active or 0)),
            "publishable_key": row.publishable_key[:12] + "..." if row.publishable_key else "",
            "has_secret": bool(row.secret_key),
        }
    finally:
        db.close()


def get_gateway_keys(gateway: str) -> Optional[Dict[str, str]]:
    """Return raw keys for payment processing (NOT exposed via API)."""
    Session = get_session_factory()
    db = Session()
    try:
        row = db.scalar(
            select(PaymentGatewayConfig).where(
                and_(PaymentGatewayConfig.gateway == gateway, PaymentGatewayConfig.is_active == 1)
            )
        )
        if not row:
            return None
        return {
            "publishable_key": row.publishable_key or "",
            "secret_key": row.secret_key or "",
            "webhook_secret": row.webhook_secret or "",
        }
    finally:
        db.close()


# ── Email Config ───────────────────────────────────────────────────────

def get_email_config() -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        row = db.scalar(select(EmailConfig).limit(1))
        if not row:
            return None
        return {
            "smtp_host": row.smtp_host or "",
            "smtp_port": int(row.smtp_port or 587),
            "smtp_user": row.smtp_user or "",
            "has_password": bool(row.smtp_pass),
            "from_email": row.from_email or "",
            "from_name": row.from_name or "",
            "is_active": bool(int(row.is_active or 0)),
        }
    finally:
        db.close()


def save_email_config(data: Dict[str, Any]) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        row = db.scalar(select(EmailConfig).limit(1))
        now = _now()
        if row:
            for key in ("smtp_host", "smtp_user", "from_email", "from_name"):
                if key in data:
                    setattr(row, key, data[key])
            if "smtp_port" in data:
                row.smtp_port = int(data["smtp_port"])
            if "smtp_pass" in data:
                row.smtp_pass = data["smtp_pass"]
            if "is_active" in data:
                row.is_active = int(bool(data["is_active"]))
            row.updated_at = now
        else:
            row = EmailConfig(
                id=str(uuid.uuid4()),
                smtp_host=data.get("smtp_host", ""),
                smtp_port=int(data.get("smtp_port", 587)),
                smtp_user=data.get("smtp_user", ""),
                smtp_pass=data.get("smtp_pass", ""),
                from_email=data.get("from_email", ""),
                from_name=data.get("from_name", ""),
                is_active=int(bool(data.get("is_active", True))),
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# ── Email Templates ────────────────────────────────────────────────────

def get_email_templates() -> List[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        rows = list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.name)))
        return [
            {
                "id": r.id,
                "name": r.name,
                "subject": r.subject or "",
                "body_html": r.body_html or "",
                "variables": json.loads(r.variables or "[]"),
                "created_at": r.created_at or "",
                "updated_at": r.updated_at or "",
            }
            for r in rows
        ]
    finally:
        db.close()


def get_email_template(name: str) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        r = db.scalar(select(EmailTemplate).where(EmailTemplate.name == name))
        if not r:
            return None
        return {
            "id": r.id,
            "name": r.name,
            "subject": r.subject or "",
            "body_html": r.body_html or "",
            "variables": json.loads(r.variables or "[]"),
        }
    finally:
        db.close()


def save_email_template(data: Dict[str, Any]) -> Dict[str, Any]:
    Session = get_session_factory()
    db = Session()
    try:
        now = _now()
        existing = db.scalar(select(EmailTemplate).where(EmailTemplate.name == data["name"]))
        if existing:
            existing.subject = data.get("subject", existing.subject)
            existing.body_html = data.get("body_html", existing.body_html)
            if "variables" in data:
                existing.variables = json.dumps(data["variables"])
            existing.updated_at = now
        else:
            existing = EmailTemplate(
                id=str(uuid.uuid4()),
                name=data["name"],
                subject=data.get("subject", ""),
                body_html=data.get("body_html", ""),
                variables=json.dumps(data.get("variables", [])),
                created_at=now,
                updated_at=now,
            )
            db.add(existing)
        db.commit()
        return {"id": existing.id, "name": existing.name}
    finally:
        db.close()


def delete_email_template(template_id: str) -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        t = db.get(EmailTemplate, template_id)
        if not t:
            return False
        db.delete(t)
        db.commit()
        return True
    finally:
        db.close()


# ── Send Welcome Email ─────────────────────────────────────────────────

def send_welcome_email(user_id: str) -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        user = db.get(User, user_id)
        plan = None
        sub = db.scalar(
            select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.created_at.desc()).limit(1)
        )
        if sub:
            plan = db.get(Plan, sub.plan_id)
        if not user or not plan:
            return False
        email_cfg = db.scalar(select(EmailConfig).limit(1))
        tmpl = db.scalar(select(EmailTemplate).where(EmailTemplate.name == "welcome_email"))
        if not tmpl or not email_cfg or not email_cfg.is_active or not email_cfg.smtp_host:
            return False
        from backend.services.email_service import send_html as _send
        body = tmpl.body_html
        subject = tmpl.subject
        vars_map = {
            "userName": user.email.split("@")[0],
            "planName": plan.name or "",
            "leadLimit": str(plan.lead_limit or 0),
            "loginUrl": getattr(config, "FRONTEND_URL", "") + "/login",
        }
        for k, v in vars_map.items():
            body = body.replace("{{" + k + "}}", str(v))
            subject = subject.replace("{{" + k + "}}", str(v))
        _send(
            to=user.email,
            subject=subject,
            body_html=body,
            smtp_host=email_cfg.smtp_host or "",
            smtp_port=int(email_cfg.smtp_port or 587),
            smtp_user=email_cfg.smtp_user or "",
            smtp_password=email_cfg.smtp_pass or "",
            from_email=email_cfg.from_email or "",
            from_name=email_cfg.from_name or "",
        )
        return True
    except Exception as e:
        logger.error("send_welcome_email failed: %s", e)
        return False
    finally:
        db.close()


# ── Check login eligibility ────────────────────────────────────────────

def send_payment_email(subscription_id: str) -> bool:
    """Send payment confirmation email using stored SMTP config + template."""
    Session = get_session_factory()
    db = Session()
    try:
        sub = db.get(Subscription, subscription_id)
        if not sub:
            return False
        user = db.get(User, sub.user_id)
        plan = db.get(Plan, sub.plan_id)
        if not user or not plan:
            return False
        email_cfg = db.scalar(select(EmailConfig).limit(1))
        txn = db.scalar(
            select(Transaction)
            .where(Transaction.subscription_id == sub.id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        tmpl = db.scalar(select(EmailTemplate).where(EmailTemplate.name == "payment_confirmation"))
        if not tmpl:
            logger.info("No payment_confirmation email template found, skipping email")
            return False
        if not email_cfg or not email_cfg.is_active or not email_cfg.smtp_host:
            logger.info("SMTP not configured, skipping email")
            return False

        from backend.services.email_service import send_html as _send
        body = tmpl.body_html
        subject = tmpl.subject
        vars_map = {
            "userName": user.email.split("@")[0],
            "planName": plan.name or "",
            "amount": f"{float(txn.amount):.2f}" if txn else "0.00",
            "currency": (txn.currency or "usd").upper() if txn else "USD",
            "transactionId": txn.id if txn else "",
            "invoiceUrl": txn.invoice_url if txn and txn.invoice_url else "",
            "loginUrl": config.FRONTEND_URL + "/login" if getattr(config, "FRONTEND_URL", None) else "",
        }
        for k, v in vars_map.items():
            body = body.replace("{{" + k + "}}", str(v))
            subject = subject.replace("{{" + k + "}}", str(v))

        _send(
            to=user.email,
            subject=subject,
            body_html=body,
            smtp_host=email_cfg.smtp_host or "",
            smtp_port=int(email_cfg.smtp_port or 587),
            smtp_user=email_cfg.smtp_user or "",
            smtp_password=email_cfg.smtp_pass or "",
            from_email=email_cfg.from_email or "",
            from_name=email_cfg.from_name or "",
        )
        logger.info("Payment confirmation email sent to %s", user.email)
        return True
    except Exception as e:
        logger.error("Failed to send payment email: %s", e)
        return False
    finally:
        db.close()


# ── Seed default email templates ────────────────────────────────────────

_DEFAULT_TEMPLATES = {
    "payment_confirmation": {
        "subject": "Payment Confirmed — {{planName}} Plan",
        "body_html": """<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:32px">
<div style="text-align:center;margin-bottom:32px"><h1 style="color:#d97706;font-size:24px;font-weight:700">LeadPilot</h1></div>
<h2 style="font-size:20px;font-weight:600;margin-bottom:16px">Payment Confirmed</h2>
<p style="color:#52525b;line-height:1.6">Hi {{userName}},</p>
<p style="color:#52525b;line-height:1.6">Your payment of <strong>{{currency}} {{amount}}</strong> for the <strong>{{planName}}</strong> plan has been received.</p>
<div style="background:#fafafa;border-radius:12px;padding:24px;margin:24px 0;border:1px solid #e4e4e7">
<p style="margin:4px 0;color:#71717a;font-size:14px">Transaction: {{transactionId}}</p>
{% if invoiceUrl %}<p style="margin:4px 0"><a href="{{invoiceUrl}}" style="color:#d97706">View Invoice</a></p>{% endif %}
</div>
<a href="{{loginUrl}}" style="display:inline-block;background:#d97706;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:24px">Go to Dashboard</a>
<p style="color:#a1a1aa;font-size:12px;margin-top:32px;border-top:1px solid #e4e4e7;padding-top:16px">&copy; 2026 LeadPilot. All rights reserved.</p>
</div>""",
        "variables": ["userName", "planName", "amount", "currency", "transactionId", "invoiceUrl", "loginUrl"],
    },
    "payment_failed": {
        "subject": "Payment Failed — {{planName}} Plan",
        "body_html": """<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:32px">
<div style="text-align:center;margin-bottom:32px"><h1 style="color:#d97706;font-size:24px;font-weight:700">LeadPilot</h1></div>
<h2 style="font-size:20px;font-weight:600;margin-bottom:16px;color:#dc2626">Payment Failed</h2>
<p style="color:#52525b;line-height:1.6">Hi {{userName}},</p>
<p style="color:#52525b;line-height:1.6">Your payment of <strong>{{currency}} {{amount}}</strong> for the <strong>{{planName}}</strong> plan could not be processed.</p>
<p style="color:#52525b;line-height:1.6">Reason: {{failureReason}}</p>
<p style="color:#52525b;line-height:1.6">Please try again with a different payment method.</p>
<a href="{{retryUrl}}" style="display:inline-block;background:#d97706;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:24px">Retry Payment</a>
<p style="color:#a1a1aa;font-size:12px;margin-top:32px;border-top:1px solid #e4e4e7;padding-top:16px">&copy; 2026 LeadPilot. All rights reserved.</p>
</div>""",
        "variables": ["userName", "planName", "amount", "currency", "failureReason", "retryUrl"],
    },
    "free_plan_renewed": {
        "subject": "Your Free Plan Has Been Renewed",
        "body_html": """<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:32px">
<div style="text-align:center;margin-bottom:32px"><h1 style="color:#d97706;font-size:24px;font-weight:700">LeadPilot</h1></div>
<h2 style="font-size:20px;font-weight:600;margin-bottom:16px">Free Plan Renewed</h2>
<p style="color:#52525b;line-height:1.6">Hi {{userName}},</p>
<p style="color:#52525b;line-height:1.6">Your Free plan has been renewed for another 30 days. You now have <strong>{{leadLimit}} leads</strong> available.</p>
<p style="color:#52525b;line-height:1.6">New period ends: {{periodEnd}}</p>
<a href="{{loginUrl}}" style="display:inline-block;background:#d97706;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:24px">Go to Dashboard</a>
<p style="color:#a1a1aa;font-size:12px;margin-top:32px;border-top:1px solid #e4e4e7;padding-top:16px">&copy; 2026 LeadPilot. All rights reserved.</p>
</div>""",
        "variables": ["userName", "leadLimit", "periodEnd", "loginUrl"],
    },
    "welcome_email": {
        "subject": "Welcome to LeadPilot — Get Started Today",
        "body_html": """<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:32px">
<div style="text-align:center;margin-bottom:32px"><h1 style="color:#d97706;font-size:24px;font-weight:700">LeadPilot</h1></div>
<h2 style="font-size:20px;font-weight:600;margin-bottom:16px">Welcome, {{userName}}!</h2>
<p style="color:#52525b;line-height:1.6">Your {{planName}} plan is ready. You can now manage up to <strong>{{leadLimit}} leads</strong>.</p>
<p style="color:#52525b;line-height:1.6">Start by exploring leads or setting up your first outreach campaign.</p>
<a href="{{loginUrl}}" style="display:inline-block;background:#d97706;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:24px">Go to Dashboard</a>
<p style="color:#a1a1aa;font-size:12px;margin-top:32px;border-top:1px solid #e4e4e7;padding-top:16px">&copy; 2026 LeadPilot. All rights reserved.</p>
</div>""",
        "variables": ["userName", "planName", "leadLimit", "loginUrl"],
    },
    "subscription_expiring": {
        "subject": "Your {{planName}} Plan Expires Soon",
        "body_html": """<div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:32px">
<div style="text-align:center;margin-bottom:32px"><h1 style="color:#d97706;font-size:24px;font-weight:700">LeadPilot</h1></div>
<h2 style="font-size:20px;font-weight:600;margin-bottom:16px">Plan Expiring Soon</h2>
<p style="color:#52525b;line-height:1.6">Hi {{userName}},</p>
<p style="color:#52525b;line-height:1.6">Your <strong>{{planName}}</strong> plan will expire on <strong>{{expiryDate}}</strong>.</p>
<p style="color:#52525b;line-height:1.6">Renew now to keep accessing all your leads and features without interruption.</p>
<a href="{{renewUrl}}" style="display:inline-block;background:#d97706;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:24px">Renew Plan</a>
<p style="color:#a1a1aa;font-size:12px;margin-top:32px;border-top:1px solid #e4e4e7;padding-top:16px">&copy; 2026 LeadPilot. All rights reserved.</p>
</div>""",
        "variables": ["userName", "planName", "expiryDate", "renewUrl"],
    },
}


def seed_default_email_templates() -> None:
    """Create default email templates if none exist."""
    Session = get_session_factory()
    db = Session()
    try:
        count = db.scalar(select(EmailTemplate).with_only_columns(EmailTemplate.id).limit(1))
        if count is not None:
            return
        now = _now()
        for name, data in _DEFAULT_TEMPLATES.items():
            t = EmailTemplate(
                id=str(uuid.uuid4()),
                name=name,
                subject=data["subject"],
                body_html=data["body_html"],
                variables=json.dumps(data["variables"]),
                created_at=now,
                updated_at=now,
            )
            db.add(t)
        db.commit()
        logger.info("Seeded %d default email templates", len(_DEFAULT_TEMPLATES))
    finally:
        db.close()


def check_login_eligibility(user_id: str) -> Dict[str, Any]:
    """Returns subscription status for login gate."""
    sub_data = get_user_subscription(user_id)
    if not sub_data:
        return {
            "allowed": True,
            "has_subscription": False,
            "is_free": True,
            "status": "none",
            "reason": "",
        }
    if sub_data["status"] == "pending_payment":
        # Check if there are failed transactions
        Session = get_session_factory()
        db = Session()
        try:
            failed_txn = db.scalar(
                select(Transaction).where(
                    and_(
                        Transaction.subscription_id == sub_data["id"],
                        Transaction.status == "failed",
                    )
                ).limit(1)
            )
        finally:
            db.close()
        if failed_txn:
            return {
                "allowed": False,
                "has_subscription": True,
                "is_free": False,
                "status": "payment_failed",
                "reason": "Your last payment failed. Please retry.",
                "subscription_id": sub_data["id"],
            }
        return {
            "allowed": False,
            "has_subscription": True,
            "is_free": False,
            "status": "pending_payment",
            "reason": "Payment not yet completed.",
            "subscription_id": sub_data["id"],
        }
    if sub_data["status"] == "active" or sub_data["is_free"]:
        return {
            "allowed": True,
            "has_subscription": True,
            "is_free": sub_data["is_free"],
            "status": sub_data["status"],
            "reason": "",
            "leads_consumed": sub_data.get("leads_consumed", 0),
            "lead_limit": sub_data.get("lead_limit", 0),
        }
    return {
        "allowed": False,
        "has_subscription": True,
        "is_free": False,
        "status": sub_data["status"],
        "reason": f"Subscription is {sub_data['status']}. Please renew.",
    }
