from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, out, current_user, require_roles, audit, rate_limit, get_settings, rx, public_filter, LANGUAGES, EXPERTISE, MODES, SLOT_DURATIONS
from finance import get_provider, call_provider_status

router = APIRouter(prefix="/api")

PUBLIC_FIELDS = ["display_name", "bio", "languages", "expertise", "experience_years", "rates", "modes_enabled",
                 "identity_status", "credential_status", "credential_summary", "rating_avg", "rating_count"]


def public_profile(p):
    d = {k: p.get(k) for k in PUBLIC_FIELDS}
    d["id"] = p["_id"]
    d["identity_verified"] = p.get("identity_status") == "approved"
    d["credential_verified"] = p.get("credential_status") == "approved"
    d.pop("identity_status")
    d.pop("credential_status")
    return d


@router.get("/public/config")
async def public_config():
    s = await get_settings()
    prov = get_provider()
    plans = await db.listing_plans.find({"active": True}).sort("price_paise", 1).to_list(20)
    return {"languages": LANGUAGES, "expertise": EXPERTISE, "modes": MODES, "slot_durations": SLOT_DURATIONS,
            "payments": {"provider": prov.name, "operational": prov.operational, "test_mode": prov.test_mode},
            "calls": call_provider_status(),
            "policy": {k: s[k] for k in ("cancellation_window_hours", "late_cancel_refund_pct", "dispute_window_hours", "session_grace_minutes")},
            "plans": [out(p) for p in plans]}


@router.get("/astrologers")
async def list_astrologers(language: Optional[str] = None, expertise: Optional[str] = None, mode: Optional[str] = None,
                           min_exp: int = 0, max_rate: Optional[int] = None, verified_credential: bool = False,
                           q: Optional[str] = None, sort: str = "rating", page: int = Query(1, ge=1), limit: int = Query(12, ge=1, le=50)):
    f = public_filter()
    if language:
        f["languages"] = language
    if expertise:
        f["expertise"] = expertise
    if mode in MODES:
        f["modes_enabled"] = mode
        if max_rate:
            f[f"rates.{mode}"] = {"$lte": max_rate}
    if min_exp:
        f["experience_years"] = {"$gte": min_exp}
    if verified_credential:
        f["credential_status"] = "approved"
    if q:
        f["display_name"] = rx(q[:60])
    order = {"rating": [("rating_avg", -1)], "experience": [("experience_years", -1)], "price": [("rates.chat", 1)]}.get(sort, [("rating_avg", -1)])
    total = await db.astrologer_profiles.count_documents(f)
    items = await db.astrologer_profiles.find(f).sort(order).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": [public_profile(p) for p in items], "total": total, "page": page}


@router.get("/astrologers/{aid}")
async def get_astrologer(aid: str):
    p = await db.astrologer_profiles.find_one({"_id": aid, **public_filter()})
    if not p:
        raise HTTPException(404, "Astrologer not found or not currently listed")
    slots = await db.slots.find({"astrologer_id": aid, "status": "open", "start_at": {"$gt": now()}}).sort("start_at", 1).limit(60).to_list(60)
    reviews = await db.reviews.find({"astrologer_id": aid, "hidden": False}).sort("created_at", -1).limit(20).to_list(20)
    return {**public_profile(p),
            "slots": [{"id": s["_id"], "start_at": s["start_at"], "duration_min": s["duration_min"]} for s in slots],
            "reviews": [{"id": r["_id"], "rating": r["rating"], "comment": r["comment"], "customer_name": r["customer_name"], "created_at": r["created_at"]} for r in reviews]}


# ---------- Birth profiles ----------
class BirthIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=80)
    birth_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    birth_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    birth_place: str = Field(min_length=1, max_length=120)
    gender: Optional[Literal["female", "male", "other", "prefer_not"]] = None


def _check_date(body: BirthIn):
    try:
        d = datetime.strptime(body.birth_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(422, "Invalid birth date")
    if d.year < 1900 or d.date() > now().date():
        raise HTTPException(422, "Birth date must be between 1900 and today")


@router.get("/me/birth-profiles")
async def list_birth(user=Depends(require_roles("customer"))):
    return [out(b) for b in await db.birth_profiles.find({"owner_id": user["_id"]}).sort("created_at", 1).to_list(50)]


@router.post("/me/birth-profiles")
async def add_birth(body: BirthIn, user=Depends(require_roles("customer"))):
    _check_date(body)
    if await db.birth_profiles.count_documents({"owner_id": user["_id"]}) >= 10:
        raise HTTPException(400, "Maximum 10 birth profiles")
    doc = {"_id": new_id(), "owner_id": user["_id"], **body.model_dump(), "created_at": now()}
    await db.birth_profiles.insert_one(doc)
    return out(doc)


@router.put("/me/birth-profiles/{bid}")
async def edit_birth(bid: str, body: BirthIn, user=Depends(require_roles("customer"))):
    _check_date(body)
    r = await db.birth_profiles.update_one({"_id": bid, "owner_id": user["_id"]}, {"$set": {**body.model_dump(), "updated_at": now()}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.delete("/me/birth-profiles/{bid}")
async def del_birth(bid: str, user=Depends(require_roles("customer"))):
    r = await db.birth_profiles.delete_one({"_id": bid, "owner_id": user["_id"]})
    if not r.deleted_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ---------- Payments / receipts ----------
@router.get("/me/payments")
async def my_payments(user=Depends(current_user)):
    pays = await db.payments.find({"user_id": user["_id"]}).sort("created_at", -1).limit(200).to_list(200)
    refunds = await db.refunds_disputes.find({"user_id": user["_id"], "type": "refund"}).sort("created_at", -1).to_list(200)
    return {"payments": [out(p, "idempotency_key") for p in pays], "refunds": [out(r) for r in refunds]}


@router.get("/me/payments/{pid}/receipt")
async def receipt(pid: str, user=Depends(current_user)):
    p = await db.payments.find_one({"_id": pid, "user_id": user["_id"], "status": {"$in": ["captured", "duplicate"]}})
    if not p:
        raise HTTPException(404, "Receipt not found")
    refunds = await db.refunds_disputes.find({"payment_id": pid, "type": "refund"}).to_list(20)
    return {"receipt_no": f"RCPT-{p['_id'][:10].upper()}", "issued_to": user["name"], "email": user["email"], "purpose": p["purpose"],
            "amount_paise": p["amount_paise"], "currency": "INR", "paid_at": p.get("captured_at"), "provider": p["provider"],
            "provider_payment_id": p["provider_payment_id"], "refunded_paise": sum(r["amount_paise"] for r in refunds),
            "note": "Payment receipt. Not a GST tax invoice."}


# ---------- Safety: blocks & reports ----------
class BlockIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)


class ReportIn(BaseModel):
    target_user_id: str = Field(min_length=1, max_length=64)
    booking_id: Optional[str] = Field(None, max_length=64)
    reason: Literal["harassment", "coercion_or_pressure", "guaranteed_outcome_claims", "fraud", "inappropriate_content", "spam", "other"]
    details: str = Field("", max_length=2000)


@router.get("/me/blocks")
async def my_blocks(user=Depends(current_user)):
    blocks = await db.blocks.find({"blocker_id": user["_id"]}).to_list(200)
    names = {u["_id"]: u["name"] async for u in db.users.find({"_id": {"$in": [b["blocked_id"] for b in blocks]}}, {"name": 1})}
    return [{"user_id": b["blocked_id"], "name": names.get(b["blocked_id"], "User"), "created_at": b["created_at"]} for b in blocks]


@router.post("/me/blocks")
async def block(body: BlockIn, user=Depends(current_user)):
    if body.user_id == user["_id"] or not await db.users.find_one({"_id": body.user_id, "role": {"$ne": "admin"}}):
        raise HTTPException(400, "Cannot block this user")
    try:
        await db.blocks.insert_one({"_id": new_id(), "blocker_id": user["_id"], "blocked_id": body.user_id, "created_at": now()})
    except DuplicateKeyError:
        pass
    return {"ok": True}


@router.delete("/me/blocks/{uid}")
async def unblock(uid: str, user=Depends(current_user)):
    await db.blocks.delete_one({"blocker_id": user["_id"], "blocked_id": uid})
    return {"ok": True}


@router.post("/reports")
async def report(body: ReportIn, user=Depends(current_user)):
    await rate_limit(f"report:{user['_id']}", 10, 3600)
    if body.target_user_id == user["_id"] or not await db.users.find_one({"_id": body.target_user_id}):
        raise HTTPException(400, "Invalid report target")
    doc = {"_id": new_id(), "reporter_id": user["_id"], "target_user_id": body.target_user_id, "booking_id": body.booking_id,
           "reason": body.reason, "details": body.details, "status": "open", "created_at": now()}
    await db.reports.insert_one(doc)
    return {"ok": True, "id": doc["_id"]}


# ---------- Privacy ----------
class PrivacyIn(BaseModel):
    share_birth_details: bool
    marketing_opt_in: bool


@router.put("/me/privacy")
async def privacy(body: PrivacyIn, user=Depends(current_user)):
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"privacy": body.model_dump()}})
    return {"ok": True}


@router.get("/me/export")
async def export_data(request: Request, user=Depends(current_user)):
    await rate_limit(f"export:{user['_id']}", 5, 3600)
    uid = user["_id"]
    q = {"$or": [{"customer_id": uid}, {"astrologer_id": uid}]}
    bookings = await db.bookings.find(q).to_list(1000)
    data = {"account": out(user), "birth_profiles": [out(b) for b in await db.birth_profiles.find({"owner_id": uid}).to_list(50)],
            "bookings": [out(b) for b in bookings],
            "messages": [out(m) for m in await db.chat_messages.find({"booking_id": {"$in": [b["_id"] for b in bookings]}, "sender_id": uid}).to_list(5000)],
            "payments": [out(p, "idempotency_key") for p in await db.payments.find({"user_id": uid}).to_list(1000)],
            "reviews": [out(r) for r in await db.reviews.find({"customer_id": uid}).to_list(500)],
            "exported_at": now()}
    await audit(user, "data_export", "user", uid, request=request)
    return data


class DeletionIn(BaseModel):
    reason: str = Field("", max_length=500)


@router.post("/me/deletion-request")
async def deletion_request(body: DeletionIn, request: Request, user=Depends(require_roles("customer", "astrologer"))):
    try:
        await db.deletion_requests.insert_one({"_id": new_id(), "user_id": user["_id"], "email": user["email"], "role": user["role"], "reason": body.reason, "status": "pending", "created_at": now()})
    except DuplicateKeyError:
        raise HTTPException(409, "A deletion request is already pending")
    await audit(user, "deletion_requested", "user", user["_id"], request=request)
    return {"ok": True}


@router.get("/me/deletion-request")
async def deletion_status(user=Depends(current_user)):
    d = await db.deletion_requests.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    return out(d) if d else None
