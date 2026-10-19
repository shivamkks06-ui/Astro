import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, List, Dict

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form, Header
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, out, require_roles, audit, rate_limit, get_settings, LANGUAGES, EXPERTISE, MODES, SLOT_DURATIONS
from finance import create_payment, call_provider_status
from ledger import astrologer_balances
from storage import put_object, APP_NAME

router = APIRouter(prefix="/api/astrologer")
astro = require_roles("astrologer")

ALLOWED_DOC_TYPES = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_DOC_BYTES = 8 * 1024 * 1024


class PayoutAccount(BaseModel):
    beneficiary_name: str = Field(min_length=2, max_length=80)
    method: Literal["upi", "bank"]
    upi_id: Optional[str] = Field(None, max_length=60, pattern=r"^[\w.\-]{2,}@[a-zA-Z]{2,}$")
    account_last4: Optional[str] = Field(None, pattern=r"^\d{4}$")
    ifsc: Optional[str] = Field(None, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    bio: str = Field("", max_length=2000)
    languages: List[str] = Field(default_factory=list, max_length=11)
    expertise: List[str] = Field(default_factory=list, max_length=9)
    experience_years: int = Field(0, ge=0, le=70)
    credential_summary: str = Field("", max_length=300)
    rates: Dict[str, int]
    modes_enabled: List[Literal["chat", "audio", "video"]] = Field(min_length=1)
    payout_account: Optional[PayoutAccount] = None


@router.get("/profile")
async def get_profile(user=Depends(astro)):
    p = await db.astrologer_profiles.find_one({"_id": user["_id"]})
    cases = await db.verification_cases.find({"astrologer_id": user["_id"]}).to_list(5)
    docs = await db.documents.find({"owner_id": user["_id"], "is_deleted": False}).sort("created_at", -1).to_list(50)
    subs = await db.listing_subscriptions.find({"astrologer_id": user["_id"]}).sort("created_at", -1).to_list(50)
    listed = p["identity_status"] == "approved" and p.get("listing_expires_at") and p["listing_expires_at"] > now() and p["account_status"] == "active"
    return {"profile": out(p), "cases": [out(c) for c in cases], "subscriptions": [out(s) for s in subs], "is_publicly_listed": bool(listed),
            "documents": [{"id": d["_id"], "kind": d["kind"], "doc_type": d["doc_type"], "original_filename": d["original_filename"], "size": d["size"], "created_at": d["created_at"]} for d in docs],
            "calls": call_provider_status()}


@router.put("/profile")
async def update_profile(body: ProfileIn, request: Request, user=Depends(astro)):
    if any(lang not in LANGUAGES for lang in body.languages) or any(e not in EXPERTISE for e in body.expertise):
        raise HTTPException(422, "Unknown language or expertise")
    rates = {}
    for m in MODES:
        v = int(body.rates.get(m, 0))
        if v < 0 or v > 100000:
            raise HTTPException(422, "Rates must be between ₹0 and ₹1000 per minute")
        if m in body.modes_enabled and v < 100:
            raise HTTPException(422, f"Set a {m} rate of at least ₹1/min for enabled modes")
        rates[m] = v
    upd = {**body.model_dump(exclude={"rates", "payout_account"}), "rates": rates,
           "payout_account": body.payout_account.model_dump() if body.payout_account else None, "updated_at": now()}
    await db.astrologer_profiles.update_one({"_id": user["_id"]}, {"$set": upd})
    await audit(user, "astrologer_profile_updated", "astrologer_profile", user["_id"], {"rates": rates}, request)
    return {"ok": True}


@router.post("/documents")
async def upload_document(request: Request, kind: Literal["identity", "credential"] = Form(...), doc_type: str = Form(..., max_length=60), file: UploadFile = File(...), user=Depends(astro)):
    await rate_limit(f"upload:{user['_id']}", 20, 3600)
    ext = ALLOWED_DOC_TYPES.get(file.content_type or "")
    if not ext:
        raise HTTPException(415, "Only PDF, JPG, PNG or WEBP files are accepted")
    data = await file.read()
    if len(data) > MAX_DOC_BYTES or not data:
        raise HTTPException(413, "File must be between 1 byte and 8 MB")
    path = f"{APP_NAME}/private/kyc/{user['_id']}/{uuid.uuid4()}.{ext}"
    try:
        res = put_object(path, data, file.content_type)
    except Exception:
        raise HTTPException(502, "Secure storage is temporarily unavailable. Please retry.")
    doc = {"_id": new_id(), "owner_id": user["_id"], "kind": kind, "doc_type": doc_type[:60], "storage_path": res["path"],
           "original_filename": (file.filename or "document")[:120], "content_type": file.content_type, "size": len(data), "is_deleted": False, "created_at": now()}
    await db.documents.insert_one(doc)
    await audit(user, "document_uploaded", "document", doc["_id"], {"kind": kind}, request)
    return {"id": doc["_id"], "kind": kind, "doc_type": doc["doc_type"], "original_filename": doc["original_filename"]}


@router.post("/verification/{kind}/submit")
async def submit_verification(kind: Literal["identity", "credential"], request: Request, user=Depends(astro)):
    docs = await db.documents.find({"owner_id": user["_id"], "kind": kind, "is_deleted": False}, {"_id": 1}).to_list(20)
    if not docs:
        raise HTTPException(400, f"Upload at least one {kind} document first")
    if kind == "identity":
        p = await db.astrologer_profiles.find_one({"_id": user["_id"]})
        if not p.get("bio") or not p.get("languages") or not p.get("expertise"):
            raise HTTPException(400, "Complete your profile (bio, languages, expertise) before submitting")
    case = await db.verification_cases.find_one({"astrologer_id": user["_id"], "kind": kind})
    if case and case["status"] in ("submitted", "approved"):
        raise HTTPException(409, f"Verification already {case['status']}")
    entry = {"status": "submitted", "document_ids": [d["_id"] for d in docs], "submitted_at": now()}
    if case:
        await db.verification_cases.update_one({"_id": case["_id"], "status": case["status"]}, {"$set": {**entry, "resubmission": True}, "$push": {"history": {"action": "resubmitted", "at": now()}}})
    else:
        try:
            await db.verification_cases.insert_one({"_id": new_id(), "astrologer_id": user["_id"], "kind": kind, **entry, "history": [{"action": "submitted", "at": now()}], "created_at": now()})
        except DuplicateKeyError:
            raise HTTPException(409, "Verification already exists")
    await db.astrologer_profiles.update_one({"_id": user["_id"]}, {"$set": {f"{kind}_status": "submitted"}})
    await audit(user, "verification_submitted", "verification_case", user["_id"], {"kind": kind}, request)
    return {"ok": True}


class SubIn(BaseModel):
    plan_id: str = Field(min_length=1, max_length=64)


@router.post("/subscriptions")
async def buy_plan(body: SubIn, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=80), user=Depends(astro)):
    p = await db.astrologer_profiles.find_one({"_id": user["_id"]})
    if p["identity_status"] != "approved":
        raise HTTPException(400, "Identity verification must be approved before purchasing a listing")
    plan = await db.listing_plans.find_one({"_id": body.plan_id, "active": True})
    if not plan:
        raise HTTPException(404, "Plan not available")
    pending = await db.listing_subscriptions.find_one({"astrologer_id": user["_id"], "status": "pending_payment", "plan.id": plan["_id"]})
    sub = pending or {"_id": new_id(), "astrologer_id": user["_id"], "status": "pending_payment", "refund_status": None,
                      "plan": {"id": plan["_id"], "code": plan["code"], "name": plan["name"], "price_paise": plan["price_paise"], "duration_days": plan["duration_days"]},
                      "created_at": now()}
    if not pending:
        await db.listing_subscriptions.insert_one(sub)
    pay = await create_payment(user, "listing", sub["plan"]["price_paise"], sub["_id"], user["_id"], idempotency_key)
    await db.listing_subscriptions.update_one({"_id": sub["_id"]}, {"$set": {"payment_id": pay["_id"]}})
    return {"subscription_id": str(sub["_id"]), "payment_id": str(pay["_id"]), "amount_paise": pay["amount_paise"]}


@router.post("/subscriptions/{sid}/cancel")
async def cancel_sub(sid: str, request: Request, user=Depends(astro)):
    r = await db.listing_subscriptions.update_one({"_id": sid, "astrologer_id": user["_id"], "status": {"$in": ["active", "pending_payment"]}},
                                                  {"$set": {"cancel_requested": True, "cancelled_at": now()}})
    if not r.matched_count:
        raise HTTPException(404, "Subscription not found")
    await audit(user, "subscription_cancel_requested", "listing_subscription", sid, request=request)
    return {"ok": True, "message": "No further renewals. Listing stays active until its expiry date."}


class SlotIn(BaseModel):
    start_at: datetime
    duration_min: int


@router.get("/slots")
async def my_slots(user=Depends(astro)):
    slots = await db.slots.find({"astrologer_id": user["_id"], "start_at": {"$gt": now() - timedelta(days=1)}}).sort("start_at", 1).to_list(300)
    return [out(s) for s in slots]


@router.post("/slots")
async def add_slot(body: SlotIn, user=Depends(astro)):
    start = body.start_at if body.start_at.tzinfo else body.start_at.replace(tzinfo=timezone.utc)
    start = start.astimezone(timezone.utc).replace(second=0, microsecond=0)
    if body.duration_min not in SLOT_DURATIONS:
        raise HTTPException(422, f"Duration must be one of {SLOT_DURATIONS}")
    if start < now() + timedelta(minutes=30) or start > now() + timedelta(days=60):
        raise HTTPException(422, "Slots must start at least 30 minutes from now and within 60 days")
    end = start + timedelta(minutes=body.duration_min)
    clash = await db.slots.find_one({"astrologer_id": user["_id"], "start_at": {"$lt": end}, "end_at": {"$gt": start}})
    if clash:
        raise HTTPException(409, "This slot overlaps an existing slot")
    doc = {"_id": new_id(), "astrologer_id": user["_id"], "start_at": start, "end_at": end, "duration_min": body.duration_min, "status": "open", "booking_id": None, "created_at": now()}
    try:
        await db.slots.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "A slot already starts at this time")
    return out(doc)


@router.delete("/slots/{sid}")
async def remove_slot(sid: str, user=Depends(astro)):
    r = await db.slots.delete_one({"_id": sid, "astrologer_id": user["_id"], "status": "open", "booking_id": None})
    if not r.deleted_count:
        raise HTTPException(409, "Only open (unbooked) slots can be removed")
    return {"ok": True}


@router.get("/earnings")
async def earnings(user=Depends(astro)):
    from ledger import payable
    entries = await db.ledger_entries.find({"account": payable(user["_id"])}).sort("created_at", -1).limit(300).to_list(300)
    payouts = await db.payouts.find({"astrologer_id": user["_id"]}).sort("created_at", -1).to_list(200)
    s = await get_settings()
    return {"balances": await astrologer_balances(user["_id"]), "entries": [out(e) for e in entries], "payouts": [out(p) for p in payouts],
            "policy": {"payout_hold_hours": s["payout_hold_hours"], "min_payout_paise": s["min_payout_paise"], "commission_bps": s["commission_bps"]}}


class PayoutIn(BaseModel):
    amount_paise: int = Field(gt=0, le=100_000_000)


@router.post("/payouts")
async def request_payout(body: PayoutIn, request: Request, user=Depends(astro)):
    p = await db.astrologer_profiles.find_one({"_id": user["_id"]})
    if p["identity_status"] != "approved":
        raise HTTPException(400, "Identity (KYC) verification must be approved before payouts")
    if not p.get("payout_account"):
        raise HTTPException(400, "Add payout account details in your profile first")
    s = await get_settings()
    if body.amount_paise < s["min_payout_paise"]:
        raise HTTPException(400, f"Minimum payout is ₹{s['min_payout_paise'] // 100}")
    bal = await astrologer_balances(user["_id"])
    if body.amount_paise > bal["requestable_paise"]:
        raise HTTPException(400, "Amount exceeds your eligible, reconciled balance")
    doc = {"_id": new_id(), "astrologer_id": user["_id"], "amount_paise": body.amount_paise, "status": "requested", "open": True,
           "payout_account": p["payout_account"], "created_at": now()}
    try:
        await db.payouts.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "You already have a payout in progress")
    await audit(user, "payout_requested", "payout", doc["_id"], {"amount_paise": body.amount_paise}, request)
    return out(doc)
