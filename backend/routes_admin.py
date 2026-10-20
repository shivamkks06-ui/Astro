import csv
import io
import json
import secrets
from typing import Optional, Literal

import jwt
from fastapi import APIRouter, Request, HTTPException, Depends, Query, Response
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, out, require_roles, audit, get_settings, rx, make_token, decode_token, hash_password, SETTINGS_LIMITS
from finance import move, settle_cancellation, resolve_dispute, issue_refund, get_provider, MockSandboxProvider, process_webhook, call_provider_status
from ledger import post_journal, astrologer_balances, payable, PAYOUTS_PROCESSING, LISTING
from storage import get_object
from routes_bookings import recompute_rating

router = APIRouter(prefix="/api")
admin = require_roles("admin")

LISTS = {
    "users": (["email", "name"], ["role", "status"]),
    "astrologer_profiles": (["display_name"], ["identity_status", "credential_status", "account_status"]),
    "verification_cases": ([], ["status", "kind"]),
    "listing_plans": ([], ["active"]),
    "listing_subscriptions": ([], ["status"]),
    "bookings": ([], ["status", "mode"]),
    "call_sessions": ([], ["status"]),
    "payments": (["provider_order_id", "provider_payment_id"], ["status", "purpose", "reconciled"]),
    "ledger_entries": (["account"], ["kind"]),
    "journals": ([], ["kind"]),
    "payouts": ([], ["status"]),
    "refunds_disputes": ([], ["type", "status"]),
    "reviews": (["comment"], ["hidden"]),
    "reports": ([], ["status", "reason"]),
    "audit_logs": (["action"], ["actor_role", "target_type"]),
    "deletion_requests": (["email"], ["status"]),
    "webhook_events": ([], ["type", "status"]),
}
HIDE = ("password_hash", "idempotency_key", "storage_path", "photo_path", "history")


def _coerce(v: str):
    return {"true": True, "false": False}.get(v, v)


def _query(name, q, filters):
    if name not in LISTS:
        raise HTTPException(404, "Unknown list")
    search, allowed = LISTS[name]
    f = {}
    for k, v in filters.items():
        if k in allowed and v not in (None, ""):
            f[k] = _coerce(v)
    if q:
        f["$or"] = [{"_id": q}] + [{fld: rx(q[:80])} for fld in search]
    return f


@router.get("/admin/list/{name}")
async def admin_list(name: str, request: Request, q: Optional[str] = None, page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100), user=Depends(admin)):
    filters = {k: v for k, v in request.query_params.items() if k not in ("q", "page", "limit")}
    f = _query(name, q, filters)
    total = await db[name].count_documents(f)
    items = await db[name].find(f).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": [out(i, *HIDE) for i in items], "total": total, "page": page, "filters": LISTS[name][1]}


@router.get("/admin/export/{name}")
async def admin_export(name: str, request: Request, q: Optional[str] = None, user=Depends(admin)):
    filters = {k: v for k, v in request.query_params.items() if k != "q"}
    f = _query(name, q, filters)
    items = [out(i, *HIDE) for i in await db[name].find(f).sort("created_at", -1).limit(5000).to_list(5000)]
    cols = sorted({k for i in items for k in i.keys()})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for i in items:
        w.writerow([json.dumps(i.get(c), default=str) if isinstance(i.get(c), (dict, list)) else i.get(c, "") for c in cols])
    await audit(user, "admin_export", name, None, {"rows": len(items), "filters": filters}, request)
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={name}.csv"})


@router.get("/admin/overview")
async def overview(user=Depends(admin)):
    c = db
    return {
        "customers": await c.users.count_documents({"role": "customer"}),
        "astrologers": await c.users.count_documents({"role": "astrologer"}),
        "verification_pending": await c.verification_cases.count_documents({"status": "submitted"}),
        "bookings_active": await c.bookings.count_documents({"status": {"$in": ["requested", "accepted", "payment_pending", "confirmed", "in_progress"]}}),
        "disputes_open": await c.refunds_disputes.count_documents({"type": "dispute", "status": "open"}),
        "payouts_requested": await c.payouts.count_documents({"status": "requested"}),
        "reports_open": await c.reports.count_documents({"status": "open"}),
        "deletions_pending": await c.deletion_requests.count_documents({"status": "pending"}),
        "unreconciled_payments": await c.payments.count_documents({"status": "captured", "reconciled": False}),
        "payment_provider": {"name": get_provider().name, "operational": get_provider().operational, "test_mode": get_provider().test_mode},
        "calls": call_provider_status(),
    }


@router.get("/admin/finance/summary")
async def finance_summary(user=Depends(admin)):
    rows = await db.ledger_entries.aggregate([{"$group": {"_id": "$account", "debit": {"$sum": "$debit"}, "credit": {"$sum": "$credit"}}}, {"$sort": {"_id": 1}}]).to_list(1000)
    by_astro = await db.bookings.aggregate([
        {"$match": {"settlement": {"$exists": True}}},
        {"$group": {"_id": "$astrologer_id", "bookings": {"$sum": 1}, "gross": {"$sum": "$settlement.gross"}, "refunds": {"$sum": "$settlement.refund"},
                    "commission": {"$sum": {"$ifNull": ["$settlement.commission", 0]}}, "share": {"$sum": {"$ifNull": ["$settlement.astrologer_share", 0]}}}}]).to_list(500)
    names = {p["_id"]: p["display_name"] async for p in db.astrologer_profiles.find({"_id": {"$in": [r["_id"] for r in by_astro]}}, {"display_name": 1})}
    return {"accounts": [{"account": r["_id"], "debit": r["debit"], "credit": r["credit"], "balance": r["credit"] - r["debit"]} for r in rows],
            "commission_report": [{**{k: v for k, v in r.items() if k != "_id"}, "astrologer_id": r["_id"], "name": names.get(r["_id"], "")} for r in by_astro],
            "trial_balance_ok": sum(r["debit"] for r in rows) == sum(r["credit"] for r in rows)}


class StatusIn(BaseModel):
    status: Literal["active", "suspended"]
    reason: str = Field(min_length=3, max_length=500)


@router.post("/admin/users/{uid}/status")
async def set_status(uid: str, body: StatusIn, request: Request, user=Depends(admin)):
    if uid == user["_id"]:
        raise HTTPException(400, "You cannot change your own account status")
    target = await db.users.find_one({"_id": uid})
    if not target or target["role"] == "admin" or target["status"] == "deleted":
        raise HTTPException(404, "User not found")
    await db.users.update_one({"_id": uid}, {"$set": {"status": body.status, "status_reason": body.reason, "status_changed_at": now()}})
    await db.astrologer_profiles.update_one({"_id": uid}, {"$set": {"account_status": body.status}})
    await audit(user, f"user_{body.status}", "user", uid, {"reason": body.reason}, request)
    return {"ok": True}


@router.get("/admin/verification/{case_id}")
async def get_case(case_id: str, user=Depends(admin)):
    c = await db.verification_cases.find_one({"_id": case_id})
    if not c:
        raise HTTPException(404, "Case not found")
    p = await db.astrologer_profiles.find_one({"_id": c["astrologer_id"]})
    u = await db.users.find_one({"_id": c["astrologer_id"]})
    docs = await db.documents.find({"_id": {"$in": c.get("document_ids", [])}}).to_list(20)
    return {"case": out(c), "profile": out(p), "user": {"name": u["name"], "email": u["email"]},
            "documents": [{"id": d["_id"], "doc_type": d["doc_type"], "original_filename": d["original_filename"], "content_type": d["content_type"], "size": d["size"]} for d in docs]}


@router.post("/admin/documents/{doc_id}/access")
async def doc_access(doc_id: str, request: Request, user=Depends(admin)):
    d = await db.documents.find_one({"_id": doc_id, "is_deleted": False})
    if not d:
        raise HTTPException(404, "Document not found")
    token = make_token(user["_id"], "doc", 5, {"doc": doc_id})
    await audit(user, "document_access_granted", "document", doc_id, {"ttl_min": 5}, request)
    return {"url_path": f"/api/documents/stream?token={token}", "expires_in": 300}


@router.get("/documents/stream")
async def doc_stream(token: str):
    try:
        payload = decode_token(token, "doc")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Link expired or invalid")
    viewer = await db.users.find_one({"_id": payload["sub"], "role": "admin", "status": "active"})
    d = await db.documents.find_one({"_id": payload["doc"], "is_deleted": False})
    if not viewer or not d:
        raise HTTPException(404, "Not found")
    try:
        data, _ = get_object(d["storage_path"])
    except Exception:
        raise HTTPException(502, "Storage unavailable")
    return Response(data, media_type=d["content_type"], headers={"Cache-Control": "no-store", "Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"})


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    notes: str = Field(min_length=3, max_length=1000)


@router.post("/admin/verification/{case_id}/decision")
async def decide(case_id: str, body: DecisionIn, request: Request, user=Depends(admin)):
    c = await db.verification_cases.find_one({"_id": case_id})
    if not c:
        raise HTTPException(404, "Case not found")
    if c["astrologer_id"] == user["_id"]:
        raise HTTPException(403, "You cannot review your own verification")
    new = "approved" if body.decision == "approve" else "rejected"
    r = await db.verification_cases.update_one({"_id": case_id, "status": "submitted"}, {"$set": {"status": new, "reviewer_id": user["_id"], "review_notes": body.notes, "reviewed_at": now()},
                                                                                      "$push": {"history": {"action": new, "by": user["_id"], "at": now(), "notes": body.notes}}})
    if not r.modified_count:
        raise HTTPException(409, "Case is not awaiting review")
    await db.astrologer_profiles.update_one({"_id": c["astrologer_id"]}, {"$set": {f"{c['kind']}_status": new}})
    await audit(user, f"verification_{new}", "verification_case", case_id, {"kind": c["kind"], "astrologer_id": c["astrologer_id"], "notes": body.notes}, request)
    return {"ok": True}


class PlanIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_]{3,30}$")
    name: str = Field(min_length=3, max_length=60)
    price_paise: int = Field(ge=100, le=10_000_000)
    duration_days: int = Field(ge=1, le=730)
    active: bool = True


class PlanPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=60)
    price_paise: Optional[int] = Field(None, ge=100, le=10_000_000)
    duration_days: Optional[int] = Field(None, ge=1, le=730)
    active: Optional[bool] = None


@router.post("/admin/plans")
async def create_plan(body: PlanIn, request: Request, user=Depends(admin)):
    doc = {"_id": new_id(), **body.model_dump(), "created_at": now()}
    try:
        await db.listing_plans.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "Plan code exists")
    await audit(user, "plan_created", "listing_plan", doc["_id"], body.model_dump(), request)
    return out(doc)


@router.patch("/admin/plans/{pid}")
async def patch_plan(pid: str, body: PlanPatch, request: Request, user=Depends(admin)):
    old = await db.listing_plans.find_one({"_id": pid})
    if not old:
        raise HTTPException(404, "Plan not found")
    upd = body.model_dump(exclude_none=True)
    await db.listing_plans.update_one({"_id": pid}, {"$set": {**upd, "updated_at": now()}})
    await audit(user, "plan_updated", "listing_plan", pid, {"before": {k: old.get(k) for k in upd}, "after": upd}, request)
    return {"ok": True}


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/admin/astrologers/{aid}/photo/remove")
async def remove_photo(aid: str, body: ReasonIn, request: Request, user=Depends(admin)):
    r = await db.astrologer_profiles.update_one({"_id": aid, "photo_path": {"$exists": True}}, {"$unset": {"photo_path": "", "photo_version": ""}, "$set": {"photo_removed_reason": body.reason, "photo_removed_at": now()}})
    if not r.modified_count:
        raise HTTPException(404, "No photo to remove")
    await audit(user, "profile_photo_removed_by_admin", "astrologer_profile", aid, {"reason": body.reason}, request)
    return {"ok": True}



@router.post("/admin/subscriptions/{sid}/refund")
async def refund_sub(sid: str, body: ReasonIn, request: Request, user=Depends(admin)):
    sub = await db.listing_subscriptions.find_one_and_update({"_id": sid, "status": {"$in": ["active", "cancelled"]}}, {"$set": {"status": "refunded", "refund_status": "processing", "refund_reason": body.reason}})
    if not sub:
        raise HTTPException(409, "Only active subscriptions can be refunded")
    pay = await db.payments.find_one({"_id": sub.get("payment_id"), "status": "captured"})
    if not pay:
        await db.listing_subscriptions.update_one({"_id": sid}, {"$set": {"status": sub["status"], "refund_status": None}})
        raise HTTPException(409, "No captured payment found for this subscription")
    amt = sub["plan"]["price_paise"]
    await issue_refund(f"sub:{sid}", pay, amt, "listing_refund", [{"account": LISTING, "debit": amt}], actor_id=user["_id"])
    await db.listing_subscriptions.update_one({"_id": sid}, {"$set": {"refund_status": "processed"}})
    prof = await db.astrologer_profiles.find_one({"_id": sub["astrologer_id"]})
    if prof.get("listing_expires_at"):
        from datetime import timedelta
        new_exp = prof["listing_expires_at"] - timedelta(days=sub["plan"]["duration_days"])
        await db.astrologer_profiles.update_one({"_id": prof["_id"]}, {"$set": {"listing_expires_at": new_exp}})
    await audit(user, "subscription_refunded", "listing_subscription", sid, {"amount_paise": amt, "reason": body.reason}, request)
    return {"ok": True}


@router.post("/admin/bookings/{bid}/cancel")
async def admin_cancel(bid: str, body: ReasonIn, request: Request, user=Depends(admin)):
    before = await move(bid, {"requested", "accepted", "payment_pending", "confirmed"}, "cancelled", user["_id"], extra={"cancelled_by": "admin", "cancel_reason": body.reason})
    if not before:
        raise HTTPException(409, "Booking cannot be cancelled in its current state")
    res = await settle_cancellation(before, "admin") if before["status"] == "confirmed" else None
    await audit(user, "booking_cancelled_by_admin", "booking", bid, {"reason": body.reason, "settlement": res}, request)
    return {"ok": True, "settlement": res}


@router.post("/admin/payments/{pid}/reconcile")
async def reconcile(pid: str, request: Request, user=Depends(admin)):
    p = await db.payments.find_one({"_id": pid, "status": "captured"})
    if not p:
        raise HTTPException(404, "Captured payment not found")
    rec = await get_provider().fetch_payment(p["provider_payment_id"])
    ok = bool(rec) and rec.get("status") == "captured" and int(rec.get("amount", -1)) == p["amount_paise"] and rec.get("order_id") == p["provider_order_id"]
    await db.payments.update_one({"_id": pid}, {"$set": {"reconciled": ok, "reconciliation": {"matched": ok, "checked_at": now(), "by": user["_id"]}}})
    await audit(user, "payment_reconciled" if ok else "payment_reconcile_mismatch", "payment", pid, {"matched": ok}, request)
    return {"matched": ok}


@router.post("/admin/payouts/{pid}/approve")
async def approve_payout(pid: str, request: Request, user=Depends(admin)):
    po = await db.payouts.find_one({"_id": pid, "status": "requested"})
    if not po:
        raise HTTPException(409, "Payout is not awaiting approval")
    prof = await db.astrologer_profiles.find_one({"_id": po["astrologer_id"]})
    if prof["identity_status"] != "approved":
        raise HTTPException(400, "Astrologer KYC not approved")
    bal = await astrologer_balances(po["astrologer_id"])
    if po["amount_paise"] > bal["eligible_paise"]:
        raise HTTPException(400, "Payout exceeds eligible reconciled balance")
    r = await db.payouts.update_one({"_id": pid, "status": "requested"}, {"$set": {"status": "approved", "approved_by": user["_id"], "approved_at": now()}})
    if not r.modified_count:
        raise HTTPException(409, "Payout changed")
    await post_journal(f"payout_approve:{pid}", "payout_approved", [{"account": payable(po["astrologer_id"]), "debit": po["amount_paise"], "astrologer_id": po["astrologer_id"]},
                                                                    {"account": PAYOUTS_PROCESSING, "credit": po["amount_paise"]}], {"payout_id": pid})
    res = await get_provider().create_payout(po["amount_paise"], po["payout_account"])
    await db.payouts.update_one({"_id": pid}, {"$set": {"status": "processing", "provider_payout_id": res["payout_id"]}})
    await audit(user, "payout_approved", "payout", pid, {"amount_paise": po["amount_paise"]}, request)
    return {"ok": True}


@router.post("/admin/payouts/{pid}/reject")
async def reject_payout(pid: str, body: ReasonIn, request: Request, user=Depends(admin)):
    r = await db.payouts.update_one({"_id": pid, "status": "requested"}, {"$set": {"status": "rejected", "open": False, "rejected_reason": body.reason, "rejected_by": user["_id"], "rejected_at": now()}})
    if not r.modified_count:
        raise HTTPException(409, "Payout is not awaiting approval")
    await audit(user, "payout_rejected", "payout", pid, {"reason": body.reason}, request)
    return {"ok": True}


class SettleIn(BaseModel):
    outcome: Literal["processed", "failed"]


@router.post("/admin/payouts/{pid}/mock-settlement")
async def mock_settlement(pid: str, body: SettleIn, request: Request, user=Depends(admin)):
    provider = get_provider()
    if not isinstance(provider, MockSandboxProvider):
        raise HTTPException(404, "Not available")
    po = await db.payouts.find_one({"_id": pid, "status": "processing"})
    if not po:
        raise HTTPException(409, "Payout is not processing")
    data = {"payout_id": po["provider_payout_id"], "utr": "MOCKUTR" + secrets.token_hex(5).upper()} if body.outcome == "processed" else {"payout_id": po["provider_payout_id"], "reason": "simulated_bank_failure"}
    raw = json.dumps({"id": "evt_" + new_id(), "type": f"payout.{body.outcome}", "data": data}).encode()
    await process_webhook(raw, provider.sign(raw))
    await audit(user, "payout_mock_settlement", "payout", pid, {"outcome": body.outcome}, request)
    return {"ok": True}


class DisputeIn(BaseModel):
    refund_paise: int = Field(ge=0, le=100_000_000)
    notes: str = Field(min_length=3, max_length=1000)


@router.post("/admin/disputes/{bid}/resolve")
async def resolve(bid: str, body: DisputeIn, request: Request, user=Depends(admin)):
    b = await db.bookings.find_one({"_id": bid})
    if not b:
        raise HTTPException(404, "Booking not found")
    await resolve_dispute(b, body.refund_paise, body.notes, user)
    await audit(user, "dispute_resolved", "booking", bid, body.model_dump(), request)
    return {"ok": True}


class ReportResolveIn(BaseModel):
    status: Literal["actioned", "dismissed"]
    notes: str = Field(min_length=3, max_length=1000)
    suspend_user: bool = False


@router.post("/admin/reports/{rid}/resolve")
async def resolve_report(rid: str, body: ReportResolveIn, request: Request, user=Depends(admin)):
    rep = await db.reports.find_one_and_update({"_id": rid, "status": "open"}, {"$set": {"status": body.status, "notes": body.notes, "resolved_by": user["_id"], "resolved_at": now()}})
    if not rep:
        raise HTTPException(409, "Report is not open")
    if body.suspend_user:
        await db.users.update_one({"_id": rep["target_user_id"], "role": {"$ne": "admin"}}, {"$set": {"status": "suspended", "status_reason": f"report {rid}"}})
        await db.astrologer_profiles.update_one({"_id": rep["target_user_id"]}, {"$set": {"account_status": "suspended"}})
    await audit(user, "report_resolved", "report", rid, body.model_dump(), request)
    return {"ok": True}


class ModerateIn(BaseModel):
    hidden: bool
    reason: str = Field(min_length=3, max_length=300)


@router.post("/admin/reviews/{rid}/moderate")
async def moderate(rid: str, body: ModerateIn, request: Request, user=Depends(admin)):
    rv = await db.reviews.find_one_and_update({"_id": rid}, {"$set": {"hidden": body.hidden, "moderation_reason": body.reason, "moderated_by": user["_id"]}})
    if not rv:
        raise HTTPException(404, "Review not found")
    await recompute_rating(rv["astrologer_id"])
    await audit(user, "review_moderated", "review", rid, body.model_dump(), request)
    return {"ok": True}


@router.get("/admin/settings")
async def read_settings(user=Depends(admin)):
    return {"settings": await get_settings(), "limits": SETTINGS_LIMITS}


@router.put("/admin/settings")
async def write_settings(body: dict, request: Request, user=Depends(admin)):
    upd = {}
    for k, v in body.items():
        if k not in SETTINGS_LIMITS or not isinstance(v, int) or isinstance(v, bool):
            raise HTTPException(422, f"Invalid setting: {k}")
        lo, hi = SETTINGS_LIMITS[k]
        if not lo <= v <= hi:
            raise HTTPException(422, f"{k} must be between {lo} and {hi}")
        upd[k] = v
    before = await get_settings()
    await db.settings.update_one({"_id": "platform"}, {"$set": {**upd, "updated_at": now(), "updated_by": user["_id"]}}, upsert=True)
    await audit(user, "settings_updated", "settings", "platform", {"before": {k: before[k] for k in upd}, "after": upd}, request)
    return {"ok": True}


class DeletionDecision(BaseModel):
    approve: bool
    notes: str = Field(min_length=3, max_length=500)


@router.post("/admin/deletion-requests/{did}/process")
async def process_deletion(did: str, body: DeletionDecision, request: Request, user=Depends(admin)):
    d = await db.deletion_requests.find_one({"_id": did, "status": "pending"})
    if not d:
        raise HTTPException(409, "Request is not pending")
    uid = d["user_id"]
    if body.approve:
        active = await db.bookings.count_documents({"$or": [{"customer_id": uid}, {"astrologer_id": uid}], "status": {"$in": ["requested", "accepted", "payment_pending", "confirmed", "in_progress", "disputed"]}})
        if active:
            raise HTTPException(409, "User has active bookings or disputes; resolve them first")
        await db.users.update_one({"_id": uid}, {"$set": {"email": f"deleted_{uid}@deleted.invalid", "name": "Deleted user", "status": "deleted",
                                                         "password_hash": hash_password(secrets.token_hex(16)), "privacy": {}, "deleted_at": now()}})
        await db.birth_profiles.delete_many({"owner_id": uid})
        await db.astrologer_profiles.update_one({"_id": uid}, {"$set": {"account_status": "deleted", "display_name": "Deleted astrologer", "bio": "", "payout_account": None}})
        await db.documents.update_many({"owner_id": uid}, {"$set": {"is_deleted": True}})
    await db.deletion_requests.update_one({"_id": did}, {"$set": {"status": "completed" if body.approve else "rejected", "notes": body.notes, "processed_by": user["_id"], "processed_at": now()}})
    await audit(user, "deletion_processed", "user", uid, {"approved": body.approve, "notes": body.notes}, request)
    return {"ok": True}
