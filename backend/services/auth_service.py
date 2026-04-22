"""User accounts for JWT API auth (SQLAlchemy + SQLite)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import bcrypt
from sqlalchemy import delete, select

from database.orm.bootstrap import get_session_factory
from database.orm.models import User
from backend.settings.lead_schema import utc_now_iso


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        return False


def create_user(email: str, password: str) -> Dict[str, Any]:
    uid = str(uuid.uuid4())
    em = email.strip().lower()
    Session = get_session_factory()
    db = Session()
    try:
        if db.scalar(select(User.id).where(User.email == em)):
            raise ValueError("email_taken")
        u = User(
            id=uid,
            email=em,
            password_hash=hash_password(password),
            created_at=utc_now_iso(),
            is_active=1,
            last_login_at="",
        )
        db.add(u)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return get_user_by_id(uid)


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        u = db.get(User, user_id)
        if not u:
            return None
        return {
            "id": u.id,
            "email": u.email,
            "created_at": u.created_at,
            "is_active": bool(int(getattr(u, "is_active", 1) or 0)),
            "last_login_at": str(getattr(u, "last_login_at", "") or ""),
        }
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        em = email.strip().lower()
        u = db.scalar(select(User).where(User.email == em))
        if not u:
            return None
        return {
            "id": u.id,
            "email": u.email,
            "password_hash": u.password_hash,
            "created_at": u.created_at,
            "is_active": int(getattr(u, "is_active", 1) or 0),
        }
    finally:
        db.close()


def _touch_last_login(db, user_id: str) -> None:
    u = db.get(User, user_id)
    if u:
        u.last_login_at = utc_now_iso()


def authenticate(email: str, password: str) -> Optional[Dict[str, Any]]:
    row = get_user_by_email(email)
    if not row:
        return None
    if not int(row.get("is_active", 1) or 0):
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    Session = get_session_factory()
    db = Session()
    try:
        _touch_last_login(db, row["id"])
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    return get_user_by_id(row["id"])


def list_users() -> List[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        rows = db.scalars(select(User).order_by(User.created_at.desc())).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "created_at": u.created_at,
                "is_active": bool(int(getattr(u, "is_active", 1) or 0)),
                "last_login_at": str(getattr(u, "last_login_at", "") or ""),
            }
            for u in rows
        ]
    finally:
        db.close()


def set_user_active(user_id: str, active: bool) -> Optional[Dict[str, Any]]:
    Session = get_session_factory()
    db = Session()
    try:
        u = db.get(User, user_id)
        if not u:
            return None
        u.is_active = 1 if active else 0
        db.commit()
        return get_user_by_id(user_id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def set_user_password(user_id: str, plain_password: str) -> bool:
    Session = get_session_factory()
    db = Session()
    try:
        u = db.get(User, user_id)
        if not u:
            return False
        u.password_hash = hash_password(plain_password)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_users(user_ids: List[str]) -> int:
    clean = [str(x).strip() for x in user_ids if str(x).strip()]
    if not clean:
        return 0
    Session = get_session_factory()
    db = Session()
    try:
        res = db.execute(delete(User).where(User.id.in_(clean)))
        db.commit()
        return int(res.rowcount or 0)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
