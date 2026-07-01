from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

import config
from backend.app.api.deps import get_current_user, get_current_admin
from backend.app.middleware.jwt import create_access_token
from backend.services import auth_service, subscription_service as svc
from backend.services.email_service import send_html as send_smtp_email
from backend.utils.logger import get_logger

router = APIRouter(tags=["subscriptions"])
logger = get_logger(__name__)


# ── Schemas ────────────────────────────────────────────────────────────

class PlanCreateBody(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    monthly_price: float = 0.0
    currency: str = "usd"
    features: List[str] = []
    highlighted: bool = False
    is_free: bool = False
    lead_limit: int = 0
    channel_access: Dict[str, Any] = {}
    stripe_price_id: str = ""
    razorpay_plan_id: str = ""
    sort_order: int = 0

class PlanUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[float] = None
    currency: Optional[str] = None
    features: Optional[List[str]] = None
    highlighted: Optional[bool] = None
    is_free: Optional[bool] = None
    lead_limit: Optional[int] = None
    channel_access: Optional[Dict[str, Any]] = None
    stripe_price_id: Optional[str] = None
    razorpay_plan_id: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class CreateSubscriptionBody(BaseModel):
    plan_id: str = Field(..., min_length=1)
    gateway: str = Field(..., pattern="^(stripe|razorpay)$")

class VerifyRazorpayBody(BaseModel):
    payment_id: str
    order_id: str
    signature: str
    subscription_id: str

class GatewayConfigBody(BaseModel):
    publishable_key: str = ""
    secret_key: str = ""
    webhook_secret: str = ""
    is_active: bool = True

class EmailConfigBody(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    from_email: str = ""
    from_name: str = ""
    is_active: bool = True

class EmailTemplateBody(BaseModel):
    name: str = Field(..., min_length=1)
    subject: str = ""
    body_html: str = ""
    variables: List[str] = []


# ── Public Endpoints ───────────────────────────────────────────────────

@router.get("/public/plans")
def public_list_plans() -> Dict[str, Any]:
    plans = svc.list_plans(include_inactive=False)
    return {"plans": plans}


@router.get("/public/subscriptions/status")
def public_subscription_status(user_id: str = Query(...)) -> Dict[str, Any]:
    return svc.check_login_eligibility(user_id)


@router.post("/public/subscriptions/create")
def public_create_subscription(body: CreateSubscriptionBody, user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    user_id = user["id"]
    plans = svc.list_plans(include_inactive=False)
    plan = next((p for p in plans if p["id"] == body.plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan["is_free"]:
        sub = svc.create_free_subscription(user_id, body.plan_id)
        svc.send_welcome_email(user_id)
        return {"url": "", "subscription_id": sub["id"], "status": "active", "is_free": True}

    sub = svc.create_pending_subscription(user_id, body.plan_id, body.gateway)
    keys = svc.get_gateway_keys(body.gateway)
    if not keys:
        raise HTTPException(status_code=503, detail=f"{body.gateway} gateway not configured")

    gateway_url = ""
    gateway_order_id = ""
    gateway_sub_id = ""

    if body.gateway == "stripe":
        try:
            import stripe as stripe_lib
            stripe_lib.api_key = keys["secret_key"]
            session = stripe_lib.checkout.Session.create(
                mode="subscription" if plan["stripe_price_id"] else "payment",
                line_items=[{
                    "price": plan["stripe_price_id"] or "",
                    "quantity": 1,
                }] if plan["stripe_price_id"] else [{
                    "price_data": {
                        "currency": plan["currency"],
                        "product_data": {"name": plan["name"]},
                        "unit_amount": int(plan["monthly_price"] * 100),
                    },
                    "quantity": 1,
                }],
                success_url=f"{config.FRONTEND_URL or ''}/payment/success?session_id={{CHECKOUT_SESSION_ID}}&subscription_id={sub['id']}",
                cancel_url=f"{config.FRONTEND_URL or ''}/payment/failed?subscription_id={sub['id']}",
                client_reference_id=user_id,
                metadata={"plan_id": plan["id"], "subscription_id": sub["id"]},
            )
            gateway_url = session.url or ""
            gateway_sub_id = session.subscription or ""
        except Exception as e:
            logger.error("Stripe checkout error: %s", e)
            raise HTTPException(status_code=502, detail="Stripe checkout failed")

    elif body.gateway == "razorpay":
        try:
            import razorpay
            client = razorpay.Client(auth=(keys["publishable_key"], keys["secret_key"]))
            rp_plan = None
            if plan.get("razorpay_plan_id"):
                rp_plan = plan["razorpay_plan_id"]
            else:
                rp_resp = client.plan.create({
                    "period": "monthly",
                    "interval": 1,
                    "item": {
                        "name": plan["name"],
                        "amount": int(plan["monthly_price"] * 100),
                        "currency": plan["currency"].upper(),
                    },
                })
                rp_plan = rp_resp["id"]
            rp_sub = client.subscription.create({
                "plan_id": rp_plan,
                "total_count": 12,
                "customer_notify": 1,
                "notes": {"plan_id": plan["id"], "user_id": user_id, "subscription_id": sub["id"]},
            })
            gateway_order_id = rp_sub["id"]
            gateway_sub_id = rp_sub["id"]
        except Exception as e:
            logger.error("Razorpay subscription error: %s", e)
            raise HTTPException(status_code=502, detail="Razorpay checkout failed")

    # Save gateway IDs on subscription
    Session_factory = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
    db = Session_factory()
    try:
        from database.orm.models import Subscription as SubModel
        sub_row = db.get(SubModel, sub["id"])
        if sub_row:
            if body.gateway == "stripe":
                sub_row.stripe_sub_id = gateway_sub_id
            elif body.gateway == "razorpay":
                sub_row.razorpay_sub_id = gateway_sub_id
            db.commit()
    finally:
        db.close()

    # Create pending transaction
    txn = svc.create_transaction(
        user_id=user_id, subscription_id=sub["id"], plan_id=plan["id"],
        amount=plan["monthly_price"], currency=plan["currency"],
        gateway=body.gateway, gateway_txn_id=gateway_order_id,
    )

    return {
        "url": gateway_url,
        "order_id": gateway_order_id,
        "subscription_id": sub["id"],
        "transaction_id": txn["id"],
        "gateway": body.gateway,
        "amount": plan["monthly_price"],
        "currency": plan["currency"],
        "publishable_key": keys["publishable_key"] if body.gateway == "razorpay" else "",
    }


@router.post("/public/subscriptions/verify-razorpay")
def verify_razorpay_payment(body: VerifyRazorpayBody) -> Dict[str, Any]:
    import hashlib, hmac
    keys = svc.get_gateway_keys("razorpay")
    if not keys:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    expected = hmac.new(
        keys["webhook_secret"].encode() if keys["webhook_secret"] else keys["secret_key"].encode(),
        f"{body.order_id}|{body.payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if expected != body.signature:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    ok = svc.activate_subscription(body.subscription_id, gateway_sub_id=body.order_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Subscription not found")
    # Update transaction
    Session = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
    db = Session()
    try:
        from database.orm.models import Transaction as TxnModel
        txn = db.scalar(
            __import__("sqlalchemy", fromlist=["select"]).select(TxnModel).where(
                TxnModel.gateway_txn_id == body.order_id
            )
        )
        if txn:
            txn.status = "success"
            db.commit()
    finally:
        db.close()
    svc.send_payment_email(body.subscription_id)
    return {"ok": True, "status": "active"}


@router.get("/public/subscriptions/callback")
def subscription_callback(session_id: str = "", subscription_id: str = "") -> Dict[str, Any]:
    if not session_id and not subscription_id:
        raise HTTPException(status_code=400, detail="Missing session_id or subscription_id")
    if session_id:
        keys = svc.get_gateway_keys("stripe")
        if not keys:
            raise HTTPException(status_code=503, detail="Stripe not configured")
        import stripe as stripe_lib
        stripe_lib.api_key = keys["secret_key"]
        try:
            session = stripe_lib.checkout.Session.retrieve(session_id)
            sub_id = session.metadata.get("subscription_id", "") if session.metadata else ""
            if sub_id:
                svc.activate_subscription(sub_id, gateway_sub_id=session.subscription or "")
                svc.send_payment_email(sub_id)
            return {"ok": True, "status": "active"}
        except Exception as e:
            logger.error("Stripe callback error: %s", e)
            return {"ok": False, "status": "failed"}
    if subscription_id:
        ok = svc.activate_subscription(subscription_id)
        if ok:
            svc.send_payment_email(subscription_id)
        return {"ok": ok, "status": "active" if ok else "failed"}
    return {"ok": False, "status": "failed"}


# ── User Endpoints ─────────────────────────────────────────────────────

@router.get("/user/subscription")
def user_subscription(user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    sub = svc.handle_period_expiry(user["id"])
    if not sub:
        return {"has_subscription": False}
    return {"has_subscription": True, "subscription": sub}


@router.get("/user/transactions")
def user_transactions(
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    txns = svc.list_transactions(
        user_id=user["id"], status=status,
        date_from=date_from, date_to=date_to,
    )
    return {"transactions": txns}


@router.get("/user/usage")
def user_usage(user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    sub = svc.get_user_subscription(user["id"])
    if not sub:
        return {"leads_consumed": 0, "lead_limit": 0, "period_end": ""}
    return {
        "leads_consumed": sub.get("leads_consumed", 0),
        "lead_limit": sub.get("lead_limit", 0),
        "period_start": sub.get("period_start", ""),
        "period_end": sub.get("period_end", ""),
        "plan_name": sub.get("plan_name", ""),
    }


# ── Admin Endpoints ────────────────────────────────────────────────────

@router.get("/admin/plans")
def admin_list_plans(_admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return {"plans": svc.list_plans(include_inactive=True)}

@router.post("/admin/plans")
def admin_create_plan(body: PlanCreateBody, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return svc.create_plan(body.model_dump())

@router.patch("/admin/plans/{plan_id}")
def admin_update_plan(plan_id: str, body: PlanUpdateBody, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    plan = svc.update_plan(plan_id, data)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@router.delete("/admin/plans/{plan_id}")
def admin_delete_plan(plan_id: str, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    ok = svc.delete_plan(plan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"ok": True}


@router.get("/admin/payment-gateway/{gateway}")
def admin_get_gateway(gateway: str, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    cfg = svc.get_gateway_config(gateway)
    return cfg or {"gateway": gateway, "is_active": False, "publishable_key": "", "has_secret": False}

@router.put("/admin/payment-gateway/{gateway}")
def admin_save_gateway(gateway: str, body: GatewayConfigBody, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return svc.save_gateway_config(gateway, body.model_dump())


@router.get("/admin/email-config")
def admin_get_email_config(_admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    cfg = svc.get_email_config()
    return cfg or {}

@router.put("/admin/email-config")
def admin_save_email_config(body: EmailConfigBody, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return svc.save_email_config(body.model_dump())

@router.post("/admin/email-config/test")
def admin_test_email(_admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    cfg = svc.get_email_config()
    if not cfg or not cfg.get("from_email"):
        raise HTTPException(status_code=400, detail="Email config incomplete")
    from database.orm.bootstrap import get_session_factory
    from database.orm.models import EmailConfig as EC
    Session = get_session_factory()
    db = Session()
    try:
        row = db.scalar(__import__("sqlalchemy", fromlist=["select"]).select(EC).limit(1))
        password = row.smtp_pass if row else ""
    finally:
        db.close()
    try:
        send_smtp_email(
            to=cfg["from_email"],
            subject="Test Email from LeadPilot Admin",
            body_html="<p>If you receive this, your SMTP settings are correct.</p>",
            smtp_host=cfg["smtp_host"],
            smtp_port=cfg["smtp_port"],
            smtp_user=cfg["smtp_user"],
            smtp_password=password,
            from_email=cfg["from_email"],
            from_name=cfg.get("from_name", ""),
        )
        return {"ok": True, "message": "Test email sent"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/admin/email-templates")
def admin_list_templates(_admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return {"templates": svc.get_email_templates()}

@router.post("/admin/email-templates")
def admin_save_template(body: EmailTemplateBody, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    return svc.save_email_template(body.model_dump())

@router.delete("/admin/email-templates/{template_id}")
def admin_delete_template(template_id: str, _admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    ok = svc.delete_email_template(template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


@router.get("/admin/transactions")
def admin_list_transactions(
    user_id: Optional[str] = Query(None),
    gateway: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: Dict = Depends(get_current_admin),
) -> Dict[str, Any]:
    txns = svc.list_transactions(
        user_id=user_id, gateway=gateway, status=status,
        plan_id=plan_id, date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    return {"transactions": txns, "total": len(txns)}


@router.get("/admin/subscriptions")
def admin_list_subscriptions(_admin: Dict = Depends(get_current_admin)) -> Dict[str, Any]:
    from database.orm.bootstrap import get_session_factory
    from database.orm.models import Subscription as SubModel, User as UserModel, Plan as PlanModel
    from sqlalchemy import select
    Session = get_session_factory()
    db = Session()
    try:
        rows = list(db.scalars(select(SubModel).order_by(SubModel.created_at.desc()).limit(100)))
        result = []
        for s in rows:
            user = db.get(UserModel, s.user_id)
            plan = db.get(PlanModel, s.plan_id)
            result.append({
                "id": s.id,
                "user_id": s.user_id,
                "user_email": user.email if user else "",
                "plan_id": s.plan_id,
                "plan_name": plan.name if plan else "",
                "status": s.status,
                "gateway": s.gateway,
                "start_date": s.start_date or "",
                "end_date": s.end_date or "",
                "created_at": s.created_at or "",
            })
        return {"subscriptions": result}
    finally:
        db.close()


# ── Webhooks ───────────────────────────────────────────────────────────

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> Dict[str, Any]:
    import stripe as stripe_lib
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    keys = svc.get_gateway_keys("stripe")
    if not keys:
        logger.warning("Stripe webhook: gateway not configured")
        return {"ok": False}
    stripe_lib.api_key = keys["secret_key"]
    try:
        event = stripe_lib.Webhook.construct_event(payload, sig, keys.get("webhook_secret", ""))
    except Exception:
        return {"ok": False}
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        sub_id = session.get("metadata", {}).get("subscription_id", "") if session.get("metadata") else ""
        if sub_id:
            svc.activate_subscription(sub_id, gateway_sub_id=session.get("subscription", ""))
            svc.send_payment_email(sub_id)
    elif event["type"] == "invoice.paid":
        inv = event["data"]["object"]
        sub_stripe_id = inv.get("subscription", "")
        if sub_stripe_id:
            Session = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
            db = Session()
            try:
                from database.orm.models import Subscription as SubM
                sub = db.scalar(
                    __import__("sqlalchemy", fromlist=["select"]).select(SubM).where(SubM.stripe_sub_id == sub_stripe_id)
                )
                if sub:
                    from datetime import datetime, timezone, timedelta
                    sub.end_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                    db.commit()
            finally:
                db.close()
    elif event["type"] == "customer.subscription.deleted":
        sub_stripe_id = event["data"]["object"].get("id", "")
        if sub_stripe_id:
            Session = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
            db = Session()
            try:
                from database.orm.models import Subscription as SubM
                sub = db.scalar(
                    __import__("sqlalchemy", fromlist=["select"]).select(SubM).where(SubM.stripe_sub_id == sub_stripe_id)
                )
                if sub:
                    sub.status = "cancelled"
                    sub.auto_renew = 0
                    db.commit()
            finally:
                db.close()
    return {"ok": True}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request) -> Dict[str, Any]:
    import hashlib, hmac
    payload = await request.body()
    sig = request.headers.get("x-razorpay-signature", "")
    keys = svc.get_gateway_keys("razorpay")
    if not keys:
        logger.warning("Razorpay webhook: gateway not configured")
        return {"ok": False}
    secret = keys.get("webhook_secret", "") or keys["secret_key"]
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return {"ok": False}
    import json as _json
    event = _json.loads(payload)
    if event.get("event") == "payment.captured":
        pay = event.get("payload", {}).get("payment", {}).get("entity", {})
        sub_id_rz = pay.get("subscription_id", "")
        txn_id = pay.get("id", "")
        if sub_id_rz:
            Session = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
            db = Session()
            try:
                from database.orm.models import Subscription as SubM, Transaction as TxnM
                from sqlalchemy import select
                sub = db.scalar(select(SubM).where(SubM.razorpay_sub_id == sub_id_rz))
                if sub:
                    svc.activate_subscription(sub.id, gateway_sub_id=sub_id_rz)
                    svc.send_payment_email(sub.id)
                txn = db.scalar(select(TxnM).where(TxnM.gateway_txn_id == txn_id))
                if txn:
                    txn.status = "success"
                    db.commit()
            finally:
                db.close()
    elif event.get("event") == "subscription.charged":
        sub_entity = event.get("payload", {}).get("subscription", {}).get("entity", {})
        sub_id_rz = sub_entity.get("id", "")
        if sub_id_rz:
            Session = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
            db = Session()
            try:
                from database.orm.models import Subscription as SubM
                from sqlalchemy import select
                from datetime import datetime, timezone, timedelta
                sub = db.scalar(select(SubM).where(SubM.razorpay_sub_id == sub_id_rz))
                if sub:
                    sub.end_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                    sub.status = "active"
                    svc.send_payment_email(sub.id)
                    db.commit()
            finally:
                db.close()
    elif event.get("event") == "subscription.cancelled":
        sub_id_rz = event.get("payload", {}).get("subscription", {}).get("entity", {}).get("id", "")
        if sub_id_rz:
            Session = __import__("database.orm.bootstrap", fromlist=["get_session_factory"]).get_session_factory()
            db = Session()
            try:
                from database.orm.models import Subscription as SubM
                from sqlalchemy import select
                sub = db.scalar(select(SubM).where(SubM.razorpay_sub_id == sub_id_rz))
                if sub:
                    sub.status = "cancelled"
                    sub.auto_renew = 0
                    db.commit()
            finally:
                db.close()
    return {"ok": True}
