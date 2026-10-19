import json
from datetime import datetime, timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, out, current_user, require_roles, audit, rate_limit, get_settings, public_filter
from finance import (TRANSITIONS, move, settle_cancellation, complete_booking, create_payment, process_webhook, get_provider,
                     call_provider_status, MockSandboxProvider)

router = APIRouter(prefix="/api")
customer = require_roles("customer")


async def is_blocked(a, b):
    return bool(await db.blocks.find_one({"$or": [{"blocker_id": a, "blocked_id": b}, {"blocker_id": b, "blocked_id": a}]}))


async def load_booking(bid, user):
    b = await db.bookings.find_one({"_id": bid})
    if not b or (user["role"] != "admin" and user["_id"] not in (b["customer_id"], b["astrologer_id"])):
        raise HTTPException(404, "Booking not found")
    return b


def role_in(b, user):
    if user["_id"] == b["customer_id"]:
        return "customer"
    if user["_id"] == b["astrologer_id"]:
        return "astrologer"
    return "admin"


async def booking_view(b, user):
    role = role_in(b, user)
    d = out(b)
    names = {u["_id"]: u["name"] async for u in db.users.find({"_id": {"$in": [b["customer_id"], b["astrologer_id"]]}}, {"name": 1})}
    prof = await db.astrologer_profiles.find_one({"_id": b["astrologer_id"]}, {"display_name": 1})
    d["customer_name"] = names.get(b["customer_id"], "Customer")
    d["astrologer_name"] = (prof or {}).get("display_name") or names.get(b["astrologer_id"], "Astrologer")
    d["viewer_role"] = role
    d["birth_details"] = None
    if b.get("birth_profile_id") and (role == "customer" or (role == "astrologer" and b["status"] in ("confirmed", "in_progress"))):
        cust = await db.users.find_one({"_id": b["customer_id"]}, {"privacy": 1})
        if role == "customer" or (cust or {}).get("privacy", {}).get("share_birth_details", True):
            bp = await db.birth_profiles.find_one({"_id": b["birth_profile_id"]})
            d["birth_details"] = out(bp, "owner_id") if bp else None
    pays = await db.payments.find({"booking_id": b["_id"]}).sort("created_at", 1).to_list(20)
    d["payments"] = [{"id": p["_id"], "purpose": p["purpose"], "amount_paise": p["amount_paise"], "status": p["status"]} for p in pays]
    d["extensions_pending"] = [out(e) for e in await db.booking_extensions.find({"booking_id": b["_id"], "status": {"$in": ["pending_consent", "awaiting_payment"]}}).to_list(5)]
    d["has_review"] = bool(await db.reviews.find_one({"booking_id": b["_id"]}, {"_id": 1}))
    d["server_time"] = now()
    d.pop("history", None) if role != "admin" else None
    return d


class BookingIn(BaseModel):
    slot_id: str = Field(min_length=1, max_length=64)
    mode: Literal["chat", "audio", "video"]
    birth_profile_id: Optional[str] = Field(None, max_length=64)
    note: str = Field("", max_length=500)
    accept_terms: bool


@router.post("/bookings")
async def create_booking(body: BookingIn, request: Request, user=Depends(customer)):
    await rate_limit(f"book:{user['_id']}", 15, 3600)
    if not body.accept_terms:
        raise HTTPException(400, "Please accept the consultation price and refund terms")
    slot = await db.slots.find_one({"_id": body.slot_id})
    if not slot or slot["status"] != "open" or slot["start_at"] <= now() + timedelta(minutes=5):
        raise HTTPException(409, "This slot is no longer available")
    prof = await db.astrologer_profiles.find_one({"_id": slot["astrologer_id"], **public_filter()})
    if not prof:
        raise HTTPException(404, "Astrologer is not currently bookable")
    if body.mode not in prof["modes_enabled"] or prof["rates"].get(body.mode, 0) <= 0:
        raise HTTPException(400, "This consultation mode is not offered")
    if body.mode in ("audio", "video") and not call_provider_status()["operational"]:
        raise HTTPException(400, "Audio/video calling is not yet operational. Please choose chat.")
    if await is_blocked(user["_id"], prof["_id"]):
        raise HTTPException(403, "Booking is not possible between these accounts")
    if body.birth_profile_id and not await db.birth_profiles.find_one({"_id": body.birth_profile_id, "owner_id": user["_id"]}):
        raise HTTPException(404, "Birth profile not found")
    s = await get_settings()
    rate = int(prof["rates"][body.mode])
    gross = rate * slot["duration_min"]
    commission = gross * s["commission_bps"] // 10000
    bid = new_id()
    claimed = await db.slots.find_one_and_update({"_id": slot["_id"], "status": "open"}, {"$set": {"status": "held", "booking_id": bid}})
    if not claimed:
        raise HTTPException(409, "This slot was just taken by someone else")
    doc = {"_id": bid, "customer_id": user["_id"], "astrologer_id": prof["_id"], "slot_id": slot["_id"], "slot_start": slot["start_at"],
           "slot_end": slot["end_at"], "mode": body.mode, "booked_minutes": slot["duration_min"], "birth_profile_id": body.birth_profile_id,
           "note": body.note, "status": "requested", "active": True, "customer_joined": False, "call_connected": False,
           "price": {"currency": "INR", "rate_paise_per_min": rate, "duration_min": slot["duration_min"], "gross_paise": gross,
                     "platform_fee_paise": 0, "commission_bps": s["commission_bps"], "tax_bps": s["tax_on_commission_bps"],
                     "est_commission_paise": commission, "est_astrologer_share_paise": gross - commission,
                     "policy": {k: s[k] for k in ("cancellation_window_hours", "late_cancel_refund_pct", "dispute_window_hours")},
                     "snapshot_at": now()},
           "history": [{"to": "requested", "by": user["_id"], "at": now(), "note": ""}], "created_at": now(), "updated_at": now()}
    try:
        await db.bookings.insert_one(doc)
    except DuplicateKeyError:
        await db.slots.update_one({"_id": slot["_id"], "booking_id": bid}, {"$set": {"status": "open", "booking_id": None}})
        raise HTTPException(409, "This slot was just taken by someone else")
    await audit(user, "booking_requested", "booking", bid, {"gross_paise": gross}, request)
    return await booking_view(doc, user)


@router.get("/me/bookings")
async def my_bookings(status: Optional[str] = None, user=Depends(require_roles("customer", "astrologer"))):
    key = "customer_id" if user["role"] == "customer" else "astrologer_id"
    f = {key: user["_id"]}
    if status:
        f["status"] = status
    items = await db.bookings.find(f).sort("slot_start", -1).limit(200).to_list(200)
    ids = {b["customer_id"] for b in items} | {b["astrologer_id"] for b in items}
    names = {u["_id"]: u["name"] async for u in db.users.find({"_id": {"$in": list(ids)}}, {"name": 1})}
    return [{"id": b["_id"], "status": b["status"], "mode": b["mode"], "slot_start": b["slot_start"], "slot_end": b["slot_end"],
             "booked_minutes": b["booked_minutes"], "gross_paise": b["price"]["gross_paise"], "customer_name": names.get(b["customer_id"]),
             "astrologer_name": names.get(b["astrologer_id"]), "counterpart_id": b["astrologer_id"] if key == "customer_id" else b["customer_id"]} for b in items]


@router.get("/bookings/{bid}")
async def get_booking(bid: str, user=Depends(current_user)):
    b = await load_booking(bid, user)
    return await booking_view(b, user)


class ActionIn(BaseModel):
    reason: str = Field("", max_length=500)


@router.post("/bookings/{bid}/actions/{action}")
async def booking_action(bid: str, action: str, body: ActionIn, request: Request, user=Depends(current_user)):
    b = await load_booking(bid, user)
    if action not in TRANSITIONS:
        raise HTTPException(404, "Unknown action")
    frm, to, roles = TRANSITIONS[action]
    role = role_in(b, user)
    if role not in roles:
        raise HTTPException(403, "You cannot perform this action")
    if b["status"] not in frm:
        raise HTTPException(409, f"Cannot {action.replace('_', ' ')} a booking that is {b['status'].replace('_', ' ')}")
    t = now()
    result = None
    if action == "accept":
        if not await move(bid, frm, to, user["_id"]):
            raise HTTPException(409, "Booking changed, please refresh")
    elif action in ("decline", "cancel"):
        before = await move(bid, frm, to, user["_id"], extra={"cancelled_by": role, "cancel_reason": body.reason or action})
        if not before:
            raise HTTPException(409, "Booking changed, please refresh")
        if before["status"] == "confirmed":
            result = await settle_cancellation(before, role)
    elif action == "start":
        if t < b["slot_start"] - timedelta(minutes=10) or t > b["slot_end"]:
            raise HTTPException(409, "Session can start from 10 minutes before the slot until the slot ends")
        if not await move(bid, frm, to, user["_id"], extra={"started_at": t}):
            raise HTTPException(409, "Booking changed, please refresh")
    elif action == "complete":
        result = await complete_booking(bid, role)
    elif action == "claim_no_show":
        if t < b["slot_start"] + timedelta(minutes=10):
            raise HTTPException(409, "You can report a no-show 10 minutes after the scheduled start")
        before = await move(bid, frm, to, user["_id"], extra={"cancelled_by": "system", "cancel_reason": "astrologer_no_show"})
        if not before:
            raise HTTPException(409, "Booking changed, please refresh")
        result = await settle_cancellation(before, "astrologer")
    elif action == "dispute":
        if not body.reason.strip():
            raise HTTPException(400, "Please describe the issue")
        window = timedelta(hours=b["price"]["policy"]["dispute_window_hours"])
        if t > b["ended_at"] + window:
            raise HTTPException(409, "The dispute window for this booking has closed")
        if not await move(bid, frm, to, user["_id"], note="dispute opened"):
            raise HTTPException(409, "Booking changed, please refresh")
        await db.refunds_disputes.insert_one({"_id": new_id(), "type": "dispute", "booking_id": bid, "user_id": user["_id"], "astrologer_id": b["astrologer_id"],
                                              "reason": body.reason, "status": "open", "created_at": t})
    await audit(user, f"booking_{action}", "booking", bid, {"settlement": result} if result else None, request)
    return await booking_view(await db.bookings.find_one({"_id": bid}), user)


@router.post("/bookings/{bid}/join")
async def join(bid: str, user=Depends(customer)):
    b = await load_booking(bid, user)
    if b["status"] != "in_progress":
        raise HTTPException(409, "Session has not started")
    await db.bookings.update_one({"_id": bid}, {"$set": {"customer_joined": True, "customer_joined_at": now()}})
    return {"ok": True}


@router.post("/bookings/{bid}/pay")
async def pay_booking(bid: str, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=80), user=Depends(customer)):
    b = await load_booking(bid, user)
    if b["status"] not in ("accepted", "payment_pending"):
        raise HTTPException(409, "This booking is not awaiting payment")
    pay = await create_payment(user, "consultation", b["price"]["gross_paise"], bid, b["astrologer_id"], idempotency_key, booking_id=bid)
    await move(bid, {"accepted"}, "payment_pending", user["_id"], note="payment initiated")
    return {"payment_id": str(pay["_id"]), "amount_paise": pay["amount_paise"]}


class ExtIn(BaseModel):
    minutes: Literal[5, 10, 15]


@router.post("/bookings/{bid}/extensions")
async def request_extension(bid: str, body: ExtIn, user=Depends(customer)):
    b = await load_booking(bid, user)
    if b["status"] != "in_progress":
        raise HTTPException(409, "Extensions are only possible during a live session")
    if await db.booking_extensions.find_one({"booking_id": bid, "status": {"$in": ["pending_consent", "awaiting_payment"]}}):
        raise HTTPException(409, "An extension request is already pending")
    doc = {"_id": new_id(), "booking_id": bid, "minutes": body.minutes, "amount_paise": b["price"]["rate_paise_per_min"] * body.minutes,
           "status": "pending_consent", "customer_consent_at": now(), "created_at": now()}
    await db.booking_extensions.insert_one(doc)
    return out(doc)


class ExtRespond(BaseModel):
    accept: bool


@router.post("/bookings/{bid}/extensions/{eid}/respond")
async def respond_extension(bid: str, eid: str, body: ExtRespond, user=Depends(require_roles("astrologer"))):
    b = await load_booking(bid, user)
    if b["status"] != "in_progress":
        raise HTTPException(409, "Session is not live")
    if body.accept:
        new_end = b["started_at"] + timedelta(minutes=b["booked_minutes"] + 15)
        clash = await db.bookings.find_one({"astrologer_id": user["_id"], "active": True, "_id": {"$ne": bid}, "slot_start": {"$gte": b["slot_start"], "$lt": new_end}, "status": {"$in": ["accepted", "payment_pending", "confirmed"]}})
        if clash:
            raise HTTPException(409, "You have another booking right after this session")
    r = await db.booking_extensions.update_one({"_id": eid, "booking_id": bid, "status": "pending_consent"},
                                               {"$set": {"status": "awaiting_payment" if body.accept else "declined", "astrologer_response_at": now()}})
    if not r.modified_count:
        raise HTTPException(404, "Extension request not found")
    return {"ok": True}


@router.post("/bookings/{bid}/extensions/{eid}/pay")
async def pay_extension(bid: str, eid: str, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=80), user=Depends(customer)):
    b = await load_booking(bid, user)
    ext = await db.booking_extensions.find_one({"_id": eid, "booking_id": bid, "status": "awaiting_payment"})
    if not ext or b["status"] != "in_progress":
        raise HTTPException(409, "Extension is not awaiting payment")
    pay = await create_payment(user, "extension", ext["amount_paise"], eid, b["astrologer_id"], idempotency_key, booking_id=bid)
    return {"payment_id": str(pay["_id"]), "amount_paise": pay["amount_paise"]}


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field("", max_length=1000)


@router.post("/bookings/{bid}/review")
async def review(bid: str, body: ReviewIn, user=Depends(customer)):
    b = await load_booking(bid, user)
    if b["status"] != "completed" or not b.get("customer_joined"):
        raise HTTPException(403, "Only completed consultations you attended can be reviewed")
    try:
        await db.reviews.insert_one({"_id": new_id(), "booking_id": bid, "astrologer_id": b["astrologer_id"], "customer_id": user["_id"],
                                     "customer_name": user["name"].split(" ")[0], "rating": body.rating, "comment": body.comment, "hidden": False, "created_at": now()})
    except DuplicateKeyError:
        raise HTTPException(409, "You already reviewed this consultation")
    await recompute_rating(b["astrologer_id"])
    return {"ok": True}


async def recompute_rating(aid):
    agg = await db.reviews.aggregate([{"$match": {"astrologer_id": aid, "hidden": False}}, {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "n": {"$sum": 1}}}]).to_list(1)
    avg, n = (round(agg[0]["avg"], 2), agg[0]["n"]) if agg else (0, 0)
    await db.astrologer_profiles.update_one({"_id": aid}, {"$set": {"rating_avg": avg, "rating_count": n}})


# ---------- Chat ----------
class MsgIn(BaseModel):
    client_msg_id: str = Field(min_length=6, max_length=64)
    text: str = Field(min_length=1, max_length=2000)


@router.get("/bookings/{bid}/messages")
async def get_messages(bid: str, request: Request, after: Optional[datetime] = None, user=Depends(current_user)):
    b = await load_booking(bid, user)
    if b["status"] in ("requested", "accepted", "payment_pending", "expired"):
        return []
    if role_in(b, user) == "admin" and not after:
        await audit(user, "chat_history_viewed", "booking", bid, request=request)
    f = {"booking_id": bid}
    if after:
        f["created_at"] = {"$gt": after}
    msgs = await db.chat_messages.find(f).sort("created_at", 1).limit(500).to_list(500)
    return [{"id": m["_id"], "client_msg_id": m["client_msg_id"], "sender_role": m["sender_role"], "text": m["text"], "created_at": m["created_at"]} for m in msgs]


@router.post("/bookings/{bid}/messages")
async def send_message(bid: str, body: MsgIn, user=Depends(require_roles("customer", "astrologer"))):
    b = await load_booking(bid, user)
    if b["status"] != "in_progress":
        raise HTTPException(409, "Messages can only be sent during a live session")
    if await is_blocked(b["customer_id"], b["astrologer_id"]):
        raise HTTPException(403, "Messaging is blocked for this conversation")
    s = await get_settings()
    await rate_limit(f"chat:{user['_id']}", s["chat_messages_per_minute"], 60)
    role = role_in(b, user)
    doc = {"_id": new_id(), "booking_id": bid, "sender_id": user["_id"], "sender_role": role, "client_msg_id": body.client_msg_id,
           "text": body.text.strip(), "created_at": now()}
    try:
        await db.chat_messages.insert_one(doc)
    except DuplicateKeyError:
        doc = await db.chat_messages.find_one({"booking_id": bid, "sender_id": user["_id"], "client_msg_id": body.client_msg_id})
    if role == "customer" and not b.get("customer_joined"):
        await db.bookings.update_one({"_id": bid}, {"$set": {"customer_joined": True, "customer_joined_at": now()}})
    return {"id": doc["_id"], "client_msg_id": doc["client_msg_id"], "sender_role": doc["sender_role"], "text": doc["text"], "created_at": doc["created_at"]}


# ---------- Calls (provider boundary, not operational) ----------
@router.post("/bookings/{bid}/call-token")
async def call_token(bid: str, user=Depends(require_roles("customer", "astrologer"))):
    b = await load_booking(bid, user)
    if b["mode"] not in ("audio", "video"):
        raise HTTPException(400, "This booking is a chat consultation")
    if b["status"] != "in_progress":
        raise HTTPException(409, "Calls are only available during a live session")
    status = call_provider_status()
    await db.call_sessions.insert_one({"_id": new_id(), "booking_id": bid, "requested_by": user["_id"], "provider": status["provider"],
                                       "status": "rejected_not_configured", "connected": False, "created_at": now()})
    raise HTTPException(503, status["message"])


# ---------- Payments ----------
@router.get("/payments/{pid}")
async def get_payment(pid: str, user=Depends(current_user)):
    p = await db.payments.find_one({"_id": pid, "user_id": user["_id"]})
    if not p:
        raise HTTPException(404, "Payment not found")
    return {**out(p, "idempotency_key"), "provider_test_mode": get_provider().test_mode}


class MockCheckoutIn(BaseModel):
    outcome: Literal["success", "failure"]


@router.post("/payments/{pid}/mock-checkout")
async def mock_checkout(pid: str, body: MockCheckoutIn, user=Depends(current_user)):
    provider = get_provider()
    if not isinstance(provider, MockSandboxProvider):
        raise HTTPException(404, "Not available")
    p = await db.payments.find_one({"_id": pid, "user_id": user["_id"]})
    if not p:
        raise HTTPException(404, "Payment not found")
    if p["status"] != "created":
        return {"status": p["status"]}
    if body.outcome == "success":
        ppid = "mock_pay_" + new_id()[:18]
        fee = provider.fee_for(p["amount_paise"])
        await db.mock_provider_records.insert_one({"_id": ppid, "order_id": p["provider_order_id"], "amount": p["amount_paise"], "status": "captured", "fee": fee, "created_at": now()})
        evt = {"id": "evt_" + new_id(), "type": "payment.captured", "data": {"order_id": p["provider_order_id"], "payment_id": ppid, "amount": p["amount_paise"], "currency": "INR", "fee": fee}}
    else:
        evt = {"id": "evt_" + new_id(), "type": "payment.failed", "data": {"order_id": p["provider_order_id"], "reason": "declined_in_simulator"}}
    raw = json.dumps(evt).encode()
    await process_webhook(raw, provider.sign(raw))
    return {"status": (await db.payments.find_one({"_id": pid}))["status"]}


@router.post("/payments/webhook")
async def payment_webhook(request: Request, x_signature: str = Header("", alias="X-Webhook-Signature")):
    raw = await request.body()
    return await process_webhook(raw, x_signature)
