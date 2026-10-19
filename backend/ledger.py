from datetime import timedelta
from pymongo.errors import DuplicateKeyError, BulkWriteError
from core import db, now

GATEWAY = "asset:gateway_clearing"
PREPAY = "liability:customer_prepayments"
COMMISSION = "revenue:consultation_commission"
LISTING = "revenue:listing_fees"
FEES = "expense:gateway_fees"
TAX = "liability:tax_payable"
PAYOUTS_PROCESSING = "liability:payouts_processing"


def payable(aid: str) -> str:
    return f"liability:astrologer_payable:{aid}"


async def post_journal(key: str, kind: str, lines: list, refs: dict = None) -> bool:
    """Append-only, balanced, idempotent journal. Returns False if key already posted."""
    for ln in lines:
        if int(ln.get("debit", 0)) < 0 or int(ln.get("credit", 0)) < 0:
            raise ValueError("Negative ledger amount")
    total_d = sum(int(ln.get("debit", 0)) for ln in lines)
    total_c = sum(int(ln.get("credit", 0)) for ln in lines)
    if total_d != total_c or total_d <= 0:
        raise ValueError("Unbalanced journal")
    refs = refs or {}
    if await db.journals.find_one({"_id": key}, {"_id": 1}):
        return False
    ts = now()
    # deterministic entry ids: a retried/concurrent post can't duplicate lines; header written last marks completion
    docs = [{
        "_id": f"{key}#{i}", "journal_id": key, "kind": kind, "account": ln["account"],
        "debit": int(ln.get("debit", 0)), "credit": int(ln.get("credit", 0)),
        "astrologer_id": ln.get("astrologer_id"), "booking_id": refs.get("booking_id"),
        "payment_id": refs.get("payment_id"), "payout_id": refs.get("payout_id"),
        "available_at": ln.get("available_at"), "memo": ln.get("memo", ""), "created_at": ts,
    } for i, ln in enumerate(lines) if ln.get("debit") or ln.get("credit")]
    try:
        await db.ledger_entries.insert_many(docs, ordered=False)
    except BulkWriteError as e:
        if any(err.get("code") != 11000 for err in e.details.get("writeErrors", [])):
            raise
    try:
        await db.journals.insert_one({"_id": key, "kind": kind, "refs": refs, "total_paise": total_d, "created_at": ts})
    except DuplicateKeyError:
        return False
    return True


def split_amount(amount: int, commission_bps: int, tax_bps: int) -> dict:
    commission = amount * commission_bps // 10000
    tax = commission * tax_bps // (10000 + tax_bps) if tax_bps else 0
    return {"commission": commission - tax, "tax": tax, "share": amount - commission}


def settlement_lines(retained: int, split: dict, aid: str, hold_hours: int) -> list:
    if retained <= 0:
        return []
    return [
        {"account": COMMISSION, "credit": split["commission"], "memo": "platform commission"},
        {"account": TAX, "credit": split["tax"], "memo": "tax on commission"},
        {"account": payable(aid), "credit": split["share"], "astrologer_id": aid,
         "available_at": now() + timedelta(hours=hold_hours), "memo": "astrologer share"},
    ]


async def astrologer_balances(aid: str) -> dict:
    entries = await db.ledger_entries.find({"account": payable(aid)}).to_list(None)
    disputed = {b["_id"] async for b in db.bookings.find({"astrologer_id": aid, "status": "disputed"}, {"_id": 1})}
    pay_ids = {e["payment_id"] for e in entries if e.get("payment_id")}
    unrec = {p["_id"] async for p in db.payments.find({"_id": {"$in": list(pay_ids)}, "reconciled": {"$ne": True}}, {"_id": 1})}
    t = now()
    total = sum(e["credit"] - e["debit"] for e in entries)
    hold = sum(e["credit"] for e in entries if e["credit"] > 0 and (
        (e.get("available_at") and e["available_at"] > t) or e.get("booking_id") in disputed or e.get("payment_id") in unrec))
    pays = await db.payouts.find({"astrologer_id": aid}).to_list(None)
    requested = sum(p["amount_paise"] for p in pays if p["status"] == "requested")
    eligible = max(0, total - hold)
    pending = 0
    async for b in db.bookings.find({"astrologer_id": aid, "status": {"$in": ["confirmed", "in_progress"]}}):
        pending += b["price"]["est_astrologer_share_paise"]
    return {
        "upcoming_paise": pending,
        "ledger_balance_paise": total,
        "on_hold_paise": min(hold, max(total, 0)),
        "eligible_paise": eligible,
        "requestable_paise": max(0, eligible - requested),
        "requested_paise": requested,
        "processing_paise": sum(p["amount_paise"] for p in pays if p["status"] in ("approved", "processing")),
        "paid_paise": sum(p["amount_paise"] for p in pays if p["status"] == "paid"),
        "failed_paise": sum(p["amount_paise"] for p in pays if p["status"] == "failed"),
    }
