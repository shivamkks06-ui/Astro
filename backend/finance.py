"""Payment provider boundary, booking state machine and money movements."""
import os
import hmac
import hashlib
import json
import math
from datetime import timedelta

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, get_settings, logger
from ledger import post_journal, split_amount, settlement_lines, GATEWAY, PREPAY, LISTING, FEES, PAYOUTS_PROCESSING, COMMISSION, TAX, payable


# ---------- Payment provider boundary ----------
class PaymentProvider:
    name = "none"
    operational = False
    test_mode = False

    def _off(self):
        raise HTTPException(503, "Payment provider is not configured yet")

    def create_order(self, amount, receipt): self._off()
    def verify_webhook(self, body: bytes, signature: str) -> bool: return False
    async def create_refund(self, provider_payment_id, amount): self._off()
    async def create_payout(self, amount, account): self._off()
    async def fetch_payment(self, provider_payment_id): self._off()


class MockSandboxProvider(PaymentProvider):
    """TEST-ONLY simulator. No real money moves. Webhooks are HMAC-SHA256 signed like real gateways."""
    name = "mock_sandbox"
    operational = True
    test_mode = True

    def __init__(self, secret: str):
        self.secret = secret

    def sign(self, body: bytes) -> str:
        return hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()

    def verify_webhook(self, body, signature):
        return bool(signature) and hmac.compare_digest(self.sign(body), signature)

    def fee_for(self, amount):
        return amount * 2 // 100

    def create_order(self, amount, receipt):
        return {"order_id": "mock_order_" + new_id()[:18]}

    async def create_refund(self, provider_payment_id, amount):
        return {"refund_id": "mock_rfnd_" + new_id()[:16], "status": "processed"}

    async def create_payout(self, amount, account):
        return {"payout_id": "mock_pout_" + new_id()[:16], "status": "processing"}

    async def fetch_payment(self, provider_payment_id):
        return await db.mock_provider_records.find_one({"_id": provider_payment_id})


def get_provider() -> PaymentProvider:
    if os.environ.get("PAYMENT_PROVIDER") == "mock":
        return MockSandboxProvider(os.environ["PAYMENT_WEBHOOK_SECRET"])
    return PaymentProvider()


def call_provider_status():
    name = os.environ.get("CALL_PROVIDER", "none")
    return {"provider": name, "operational": False,
            "message": "Audio/video calling is not yet operational: no communication SDK credentials configured."}


# ---------- Payments ----------
async def create_payment(user, purpose, amount, target_id, astrologer_id, idem_key, booking_id=None):
    key = f"{user['_id']}:{idem_key}"
    existing = await db.payments.find_one({"idempotency_key": key})
    if existing:
        if existing["target_id"] != target_id:
            raise HTTPException(409, "Idempotency key already used for a different payment")
        return existing
    existing = await db.payments.find_one({"target_id": target_id, "status": "created", "user_id": user["_id"]})
    if existing:
        return existing
    provider = get_provider()
    order = provider.create_order(amount, target_id)
    doc = {"_id": new_id(), "user_id": user["_id"], "purpose": purpose, "target_id": target_id, "booking_id": booking_id,
           "astrologer_id": astrologer_id, "amount_paise": int(amount), "currency": "INR", "status": "created",
           "provider": provider.name, "provider_order_id": order["order_id"], "provider_payment_id": None,
           "idempotency_key": key, "gateway_fee_paise": 0, "tax_paise": 0, "reconciled": False, "created_at": now()}
    await db.payments.insert_one(doc)
    return doc


async def process_webhook(body: bytes, signature: str):
    provider = get_provider()
    if not provider.verify_webhook(body, signature):
        raise HTTPException(401, "Invalid webhook signature")
    evt = json.loads(body)
    try:
        await db.webhook_events.insert_one({"_id": evt["id"], "type": evt["type"], "provider": provider.name, "received_at": now(), "status": "processing"})
    except DuplicateKeyError:
        return {"status": "duplicate_ignored"}
    try:
        data = evt["data"]
        if evt["type"] == "payment.captured":
            await on_payment_captured(data)
        elif evt["type"] == "payment.failed":
            await db.payments.update_one({"provider_order_id": data["order_id"], "status": "created"}, {"$set": {"status": "failed", "failure_reason": data.get("reason", "failed"), "failed_at": now()}})
        elif evt["type"] in ("payout.processed", "payout.failed"):
            await on_payout_event(evt["type"], data)
        await db.webhook_events.update_one({"_id": evt["id"]}, {"$set": {"status": "processed"}})
    except Exception:
        await db.webhook_events.delete_one({"_id": evt["id"]})
        logger.exception("webhook processing failed")
        raise HTTPException(500, "Webhook processing error")
    return {"status": "processed"}


async def on_payment_captured(data):
    pay = await db.payments.find_one({"provider_order_id": data["order_id"]})
    if not pay:
        return
    if int(data["amount"]) != pay["amount_paise"] or data.get("currency", "INR") != "INR":
        await db.payments.update_one({"_id": pay["_id"], "status": "created"}, {"$set": {"status": "amount_mismatch", "provider_payment_id": data["payment_id"]}})
        return
    fee = int(data.get("fee", 0))
    upd = {"status": "captured", "provider_payment_id": data["payment_id"], "gateway_fee_paise": fee, "captured_at": now()}
    try:
        updated = await db.payments.find_one_and_update({"_id": pay["_id"], "status": {"$in": ["created", "failed"]}}, {"$set": upd}, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        dup = await db.payments.find_one_and_update({"_id": pay["_id"], "status": {"$in": ["created", "failed"]}},
                                                   {"$set": {**upd, "status": "duplicate"}}, return_document=ReturnDocument.AFTER)
        if dup:
            await post_capture_journal(dup)
            await issue_refund(f"dup:{dup['_id']}", dup, dup["amount_paise"], "duplicate_payment", [{"account": PREPAY if dup["purpose"] != "listing" else LISTING, "debit": dup["amount_paise"]}])
        return
    if not updated:
        return
    await post_capture_journal(updated)
    if updated["purpose"] == "listing":
        await activate_subscription(updated)
    elif updated["purpose"] == "consultation":
        b = await move(updated["booking_id"], {"payment_pending"}, "confirmed", "system", note="payment verified via webhook")
        if not b:
            await issue_refund(f"late:{updated['_id']}", updated, updated["amount_paise"], "booking_no_longer_valid", [{"account": PREPAY, "debit": updated["amount_paise"]}])
    elif updated["purpose"] == "extension":
        await apply_extension(updated)


async def post_capture_journal(pay):
    credit_acct = LISTING if pay["purpose"] == "listing" else PREPAY
    lines = [{"account": GATEWAY, "debit": pay["amount_paise"]}, {"account": credit_acct, "credit": pay["amount_paise"]}]
    if pay.get("gateway_fee_paise"):
        lines += [{"account": FEES, "debit": pay["gateway_fee_paise"]}, {"account": GATEWAY, "credit": pay["gateway_fee_paise"]}]
    await post_journal(f"capture:{pay['_id']}", f"{pay['purpose']}_payment", lines, {"payment_id": pay["_id"], "booking_id": pay.get("booking_id")})


async def issue_refund(key, pay, amount, reason, debit_lines, booking_id=None, actor_id="system"):
    """Idempotent refund: record -> provider -> balanced reversal journal."""
    if amount <= 0:
        return None
    rec = {"_id": key, "type": "refund", "payment_id": pay["_id"], "booking_id": booking_id or pay.get("booking_id"),
           "user_id": pay["user_id"], "amount_paise": int(amount), "reason": reason, "status": "pending", "created_by": actor_id, "created_at": now()}
    try:
        await db.refunds_disputes.insert_one(rec)
    except DuplicateKeyError:
        return None
    res = await get_provider().create_refund(pay.get("provider_payment_id"), amount)
    await db.refunds_disputes.update_one({"_id": key}, {"$set": {"status": res["status"], "provider_refund_id": res["refund_id"], "processed_at": now()}})
    await post_journal(f"refund:{key}", "refund", debit_lines + [{"account": GATEWAY, "credit": int(amount)}], {"payment_id": pay["_id"], "booking_id": rec["booking_id"]})
    return rec


async def activate_subscription(pay):
    sub = await db.listing_subscriptions.find_one({"_id": pay["target_id"]})
    if not sub or sub["status"] != "pending_payment":
        return
    prof = await db.astrologer_profiles.find_one({"_id": sub["astrologer_id"]})
    current = prof.get("listing_expires_at")
    start = current if current and current > now() else now()
    expires = start + timedelta(days=sub["plan"]["duration_days"])
    res = await db.listing_subscriptions.update_one({"_id": sub["_id"], "status": "pending_payment"},
        {"$set": {"status": "active", "payment_id": pay["_id"], "payment_ref": pay["provider_payment_id"], "activated_at": now(), "starts_at": start, "expires_at": expires}})
    if res.modified_count:
        await db.astrologer_profiles.update_one({"_id": sub["astrologer_id"]}, {"$set": {"listing_expires_at": expires}})


# ---------- Booking state machine ----------
TRANSITIONS = {
    "accept": ({"requested"}, "accepted", {"astrologer"}),
    "decline": ({"requested"}, "cancelled", {"astrologer"}),
    "cancel": ({"requested", "accepted", "payment_pending", "confirmed"}, "cancelled", {"customer", "astrologer", "admin"}),
    "start": ({"confirmed"}, "in_progress", {"astrologer"}),
    "complete": ({"in_progress"}, "completed", {"customer", "astrologer"}),
    "claim_no_show": ({"confirmed"}, "cancelled", {"customer"}),
    "dispute": ({"completed"}, "disputed", {"customer"}),
}


async def move(booking_id, frm, to, actor_id, extra=None, note=""):
    t = now()
    upd = {"$set": {"status": to, "updated_at": t, **(extra or {})}, "$push": {"history": {"to": to, "by": actor_id, "at": t, "note": note}}}
    if to in ("cancelled", "expired"):
        upd["$set"]["active"] = False
    before = await db.bookings.find_one_and_update({"_id": booking_id, "status": {"$in": list(frm)}}, upd, return_document=ReturnDocument.BEFORE)
    if before and to in ("cancelled", "expired"):
        reopen = before["slot_start"] > t + timedelta(minutes=30)
        await db.slots.update_one({"_id": before["slot_id"], "booking_id": booking_id}, {"$set": {"status": "open" if reopen else "closed", "booking_id": None}})
    return before


async def captured_payments(booking_id):
    return await db.payments.find({"booking_id": booking_id, "status": "captured"}).sort("created_at", 1).to_list(None)


async def refund_across(booking, pays, amount, reason, key_prefix, extra_debits_fn):
    """Refund `amount` spread over captured payments (newest first)."""
    remaining = amount
    for p in reversed(pays):
        if remaining <= 0:
            break
        part = min(remaining, p["amount_paise"])
        await issue_refund(f"{key_prefix}:{p['_id']}", p, part, reason, extra_debits_fn(part), booking_id=booking["_id"])
        remaining -= part


async def settle_cancellation(before, by_role):
    pays = await captured_payments(before["_id"])
    gross = sum(p["amount_paise"] for p in pays)
    if gross == 0:
        return {"gross": 0, "refund": 0, "retained": 0}
    pol = before["price"]["policy"]
    hours_left = (before["slot_start"] - now()).total_seconds() / 3600
    refund = gross
    if by_role == "customer" and hours_left < pol["cancellation_window_hours"]:
        refund = gross * pol["late_cancel_refund_pct"] // 100
    retained = gross - refund
    await refund_across(before, pays, refund, f"cancelled_by_{by_role}", f"cancel:{before['_id']}", lambda part: [{"account": PREPAY, "debit": part}])
    if retained > 0:
        sp = split_amount(retained, before["price"]["commission_bps"], before["price"]["tax_bps"])
        s = await get_settings()
        await post_journal(f"cancel_retain:{before['_id']}", "late_cancellation_settlement",
                           [{"account": PREPAY, "debit": retained}] + settlement_lines(retained, sp, before["astrologer_id"], s["payout_hold_hours"]),
                           {"booking_id": before["_id"], "payment_id": pays[0]["_id"]})
    summary = {"gross": gross, "refund": refund, "retained": retained}
    await db.bookings.update_one({"_id": before["_id"]}, {"$set": {"settlement": summary}})
    return summary


async def settle_completion(b):
    pays = await captured_payments(b["_id"])
    gross = sum(p["amount_paise"] for p in pays)
    booked = b["booked_minutes"]
    actual = min(booked, max(0, math.ceil((b["ended_at"] - b["started_at"]).total_seconds() / 60)))
    reason = None
    refund = 0
    if b["mode"] in ("audio", "video") and not b.get("call_connected"):
        refund, reason = gross, "call_never_connected"
    elif b.get("customer_joined") and b.get("ended_by") == "astrologer" and actual < booked:
        refund, reason = gross * (booked - actual) // booked, "astrologer_ended_early_prorata"
    retained = gross - refund
    if refund:
        await refund_across(b, pays, refund, reason, f"complete:{b['_id']}", lambda part: [{"account": PREPAY, "debit": part}])
    sp = split_amount(retained, b["price"]["commission_bps"], b["price"]["tax_bps"])
    if retained > 0:
        s = await get_settings()
        await post_journal(f"settle:{b['_id']}", "consultation_settlement",
                           [{"account": PREPAY, "debit": retained}] + settlement_lines(retained, sp, b["astrologer_id"], s["payout_hold_hours"]),
                           {"booking_id": b["_id"], "payment_id": pays[0]["_id"]})
    summary = {"gross": gross, "refund": refund, "refund_reason": reason, "retained": retained, "actual_minutes": actual,
               "commission": sp["commission"], "tax": sp["tax"], "astrologer_share": sp["share"],
               "gateway_fees": sum(p.get("gateway_fee_paise", 0) for p in pays)}
    await db.bookings.update_one({"_id": b["_id"]}, {"$set": {"settlement": summary}})
    return summary


async def complete_booking(booking_id, ended_by):
    t = now()
    before = await move(booking_id, {"in_progress"}, "completed", ended_by, extra={"ended_at": t, "ended_by": ended_by})
    if not before:
        raise HTTPException(409, "Booking is not in progress")
    b = await db.bookings.find_one({"_id": booking_id})
    return await settle_completion(b)


async def resolve_dispute(b, refund_paise, notes, admin):
    st = b.get("settlement") or {}
    retained = st.get("retained", 0)
    if refund_paise < 0 or refund_paise > retained:
        raise HTTPException(400, f"Refund must be between 0 and {retained} paise")
    before = await move(b["_id"], {"disputed"}, "completed", admin["_id"], extra={"dispute_resolution": {"refund_paise": refund_paise, "notes": notes, "by": admin["_id"], "at": now()}}, note="dispute resolved")
    if not before:
        raise HTTPException(409, "Booking is not disputed")
    if refund_paise:
        share_rev = refund_paise * st["astrologer_share"] // retained
        tax_rev = refund_paise * st["tax"] // retained
        comm_rev = refund_paise - share_rev - tax_rev
        pays = await captured_payments(b["_id"])
        debits = [{"account": payable(b["astrologer_id"]), "debit": share_rev, "astrologer_id": b["astrologer_id"], "memo": "dispute reversal"},
                  {"account": COMMISSION, "debit": comm_rev, "memo": "dispute reversal"}, {"account": TAX, "debit": tax_rev}]
        await issue_refund(f"dispute:{b['_id']}", pays[-1], refund_paise, "dispute_resolution", debits, booking_id=b["_id"], actor_id=admin["_id"])
    await db.refunds_disputes.update_one({"booking_id": b["_id"], "type": "dispute", "status": "open"}, {"$set": {"status": "resolved", "resolution": notes, "refund_paise": refund_paise, "resolved_by": admin["_id"], "resolved_at": now()}})


async def apply_extension(pay):
    ext = await db.booking_extensions.find_one_and_update({"_id": pay["target_id"], "status": "awaiting_payment"}, {"$set": {"status": "paid", "paid_at": now()}})
    if not ext:
        return
    res = await db.bookings.update_one({"_id": ext["booking_id"], "status": "in_progress"},
                                       {"$inc": {"booked_minutes": ext["minutes"]}, "$push": {"extensions": {"id": ext["_id"], "minutes": ext["minutes"], "amount_paise": ext["amount_paise"]}}})
    if not res.modified_count:
        await issue_refund(f"ext_late:{pay['_id']}", pay, pay["amount_paise"], "extension_after_session", [{"account": PREPAY, "debit": pay["amount_paise"]}])


# ---------- Payouts ----------
async def on_payout_event(typ, data):
    po = await db.payouts.find_one({"provider_payout_id": data["payout_id"]})
    if not po:
        return
    if typ == "payout.processed":
        r = await db.payouts.update_one({"_id": po["_id"], "status": "processing"}, {"$set": {"status": "paid", "open": False, "settlement_ref": data.get("utr"), "settled_at": now()}})
        if r.modified_count:
            await post_journal(f"payout_paid:{po['_id']}", "payout_settled", [{"account": PAYOUTS_PROCESSING, "debit": po["amount_paise"]}, {"account": GATEWAY, "credit": po["amount_paise"]}], {"payout_id": po["_id"]})
    else:
        r = await db.payouts.update_one({"_id": po["_id"], "status": "processing"}, {"$set": {"status": "failed", "open": False, "failure_reason": data.get("reason", "failed"), "failed_at": now()}})
        if r.modified_count:
            await post_journal(f"payout_failed:{po['_id']}", "payout_reversal",
                               [{"account": PAYOUTS_PROCESSING, "debit": po["amount_paise"]}, {"account": payable(po["astrologer_id"]), "credit": po["amount_paise"], "astrologer_id": po["astrologer_id"], "memo": "failed payout reversal"}],
                               {"payout_id": po["_id"]})


# ---------- Background sweep ----------
async def sweep():
    t = now()
    s = await get_settings()
    grace = timedelta(minutes=s["session_grace_minutes"])
    async for b in db.bookings.find({"status": {"$in": ["requested", "accepted", "payment_pending"]}, "slot_start": {"$lte": t}}):
        await move(b["_id"], {"requested", "accepted", "payment_pending"}, "expired", "system", note="not confirmed before slot start")
    async for b in db.bookings.find({"status": "confirmed", "slot_end": {"$lt": t - grace}}):
        before = await move(b["_id"], {"confirmed"}, "cancelled", "system", extra={"cancelled_by": "system", "cancel_reason": "astrologer_no_show"}, note="astrologer did not start")
        if before:
            await settle_cancellation(before, "astrologer")
    async for b in db.bookings.find({"status": "in_progress"}):
        if b["started_at"] + timedelta(minutes=b["booked_minutes"]) + grace < t:
            try:
                await complete_booking(b["_id"], "system")
            except HTTPException:
                pass
    await db.listing_subscriptions.update_many({"status": {"$in": ["active", "cancelled"]}, "expires_at": {"$lt": t}}, {"$set": {"status": "expired"}})
