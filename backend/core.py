import os
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from fastapi import Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

logger = logging.getLogger("app")
client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
db = client[os.environ["DB_NAME"]]

JWT_ALG = "HS256"
TERMS_VERSION = "2026-10-v1"
MODES = ["chat", "audio", "video"]
LANGUAGES = ["Hindi", "English", "Tamil", "Telugu", "Kannada", "Malayalam", "Bengali", "Marathi", "Gujarati", "Punjabi", "Odia"]
EXPERTISE = ["Vedic", "KP System", "Nadi", "Numerology", "Tarot", "Vastu", "Palmistry", "Prashna", "Lal Kitab"]
SLOT_DURATIONS = [15, 30, 45, 60]

DEFAULT_SETTINGS = {
    "commission_bps": 2500,
    "tax_on_commission_bps": 0,
    "cancellation_window_hours": 2,
    "late_cancel_refund_pct": 50,
    "dispute_window_hours": 48,
    "payout_hold_hours": 48,
    "min_payout_paise": 50000,
    "session_grace_minutes": 15,
    "chat_messages_per_minute": 20,
}
SETTINGS_LIMITS = {
    "commission_bps": (0, 5000), "tax_on_commission_bps": (0, 2800), "cancellation_window_hours": (0, 72),
    "late_cancel_refund_pct": (0, 100), "dispute_window_hours": (1, 336), "payout_hold_hours": (0, 720),
    "min_payout_paise": (100, 10_000_000), "session_grace_minutes": (5, 60), "chat_messages_per_minute": (5, 120),
}


def now():
    return datetime.now(timezone.utc)


def new_id():
    return uuid.uuid4().hex


def out(doc, *drop):
    if doc is None:
        return None
    d = {k: v for k, v in doc.items() if k not in ("password_hash",) + drop}
    d["id"] = d.pop("_id")
    return d


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(uid: str, typ: str, minutes: int, extra=None) -> str:
    payload = {"sub": uid, "type": typ, "exp": now() + timedelta(minutes=minutes), **(extra or {})}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALG)


def decode_token(token: str, typ: str) -> dict:
    payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    if payload.get("type") != typ:
        raise jwt.InvalidTokenError("wrong type")
    return payload


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return fwd or (request.client.host if request.client else "unknown")


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(token, "access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid session")
    user = await db.users.find_one({"_id": payload["sub"]})
    if not user:
        raise HTTPException(401, "Invalid session")
    if user["status"] != "active":
        raise HTTPException(403, f"Account is {user['status']}")
    return user


def require_roles(*roles):
    async def dep(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Not permitted for your role")
        return user
    return dep


async def audit(actor, action, target_type, target_id, details=None, request=None):
    await db.audit_logs.insert_one({
        "_id": new_id(),
        "actor_id": actor["_id"] if actor else "system",
        "actor_role": actor["role"] if actor else "system",
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "details": details or {},
        "ip": client_ip(request) if request else None,
        "created_at": now(),
    })


async def rate_limit(key: str, limit: int, window: int):
    bucket = int(now().timestamp()) // window
    doc = await db.rate_limits.find_one_and_update(
        {"_id": f"{key}:{bucket}"},
        {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now() + timedelta(seconds=window * 2)}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    if doc["count"] > limit:
        raise HTTPException(429, "Too many requests. Please wait a moment and retry.")


async def get_settings() -> dict:
    s = await db.settings.find_one({"_id": "platform"}) or {}
    return {**DEFAULT_SETTINGS, **{k: v for k, v in s.items() if k in DEFAULT_SETTINGS}}


def rx(q: str):
    return {"$regex": re.escape(q), "$options": "i"}


def public_filter():
    return {"identity_status": "approved", "listing_expires_at": {"$gt": now()}, "account_status": "active"}
