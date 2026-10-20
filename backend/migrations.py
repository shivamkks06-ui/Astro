"""Versioned, additive migrations. Never drop collections; corrections ship as new versions."""
import os
from pymongo import ASCENDING, DESCENDING
from core import db, now, new_id, DEFAULT_SETTINGS, hash_password, verify_password, logger


async def m001_indexes():
    await db.users.create_index("email", unique=True)
    await db.kundlis.create_index([("user_id", 1), ("created_at", -1)])
    await db.users.create_index([("role", 1), ("status", 1)])
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("expires_at", expireAfterSeconds=0)
    await db.rate_limits.create_index("expires_at", expireAfterSeconds=0)
    await db.astrologer_profiles.create_index([("identity_status", 1), ("listing_expires_at", 1), ("account_status", 1)])
    await db.astrologer_profiles.create_index("languages")
    await db.astrologer_profiles.create_index("expertise")
    await db.verification_cases.create_index([("astrologer_id", 1), ("kind", 1)], unique=True)
    await db.verification_cases.create_index("status")
    await db.documents.create_index([("owner_id", 1), ("kind", 1)])
    await db.listing_plans.create_index("code", unique=True)
    await db.listing_subscriptions.create_index([("astrologer_id", 1), ("status", 1)])
    await db.slots.create_index([("astrologer_id", 1), ("start_at", 1)], unique=True)
    await db.bookings.create_index("slot_id", unique=True, partialFilterExpression={"active": True})
    await db.bookings.create_index([("customer_id", 1), ("created_at", DESCENDING)])
    await db.bookings.create_index([("astrologer_id", 1), ("created_at", DESCENDING)])
    await db.bookings.create_index("status")
    await db.booking_extensions.create_index("booking_id")
    await db.chat_messages.create_index([("booking_id", 1), ("created_at", ASCENDING)])
    await db.chat_messages.create_index([("booking_id", 1), ("sender_id", 1), ("client_msg_id", 1)], unique=True)
    await db.call_sessions.create_index("booking_id")
    await db.payments.create_index("idempotency_key", unique=True)
    await db.payments.create_index("provider_order_id", unique=True)
    await db.payments.create_index("provider_payment_id", unique=True, partialFilterExpression={"provider_payment_id": {"$type": "string"}})
    await db.payments.create_index("target_id", unique=True, partialFilterExpression={"status": "captured"})
    await db.payments.create_index([("user_id", 1), ("created_at", DESCENDING)])
    await db.webhook_events.create_index("received_at")
    await db.ledger_entries.create_index([("account", 1), ("created_at", 1)])
    await db.ledger_entries.create_index("journal_id")
    await db.ledger_entries.create_index("booking_id")
    await db.payouts.create_index("astrologer_id", unique=True, name="one_open_payout", partialFilterExpression={"open": True})
    await db.payouts.create_index([("astrologer_id", 1), ("created_at", DESCENDING)])
    await db.refunds_disputes.create_index([("booking_id", 1), ("type", 1)])
    await db.refunds_disputes.create_index("status")
    await db.reviews.create_index("booking_id", unique=True)
    await db.reviews.create_index([("astrologer_id", 1), ("hidden", 1)])
    await db.reports.create_index("status")
    await db.blocks.create_index([("blocker_id", 1), ("blocked_id", 1)], unique=True)
    await db.birth_profiles.create_index("owner_id")
    await db.audit_logs.create_index([("created_at", DESCENDING)])
    await db.audit_logs.create_index("actor_id")
    await db.deletion_requests.create_index("user_id", unique=True, partialFilterExpression={"status": "pending"})


async def _validator(name, schema):
    if name not in await db.list_collection_names():
        await db.create_collection(name)
    await db.command({"collMod": name, "validator": {"$jsonSchema": schema}, "validationLevel": "strict", "validationAction": "error"})


async def m002_validators():
    await _validator("ledger_entries", {"bsonType": "object", "required": ["journal_id", "account", "debit", "credit", "created_at"],
        "properties": {"debit": {"bsonType": ["int", "long"], "minimum": 0}, "credit": {"bsonType": ["int", "long"], "minimum": 0}, "account": {"bsonType": "string"}}})
    await _validator("bookings", {"bsonType": "object", "required": ["customer_id", "astrologer_id", "slot_id", "status", "price", "mode"],
        "properties": {"status": {"enum": ["requested", "accepted", "payment_pending", "confirmed", "in_progress", "completed", "cancelled", "expired", "disputed"]},
                       "mode": {"enum": ["chat", "audio", "video"]}}})
    await _validator("payments", {"bsonType": "object", "required": ["user_id", "purpose", "amount_paise", "currency", "status", "idempotency_key"],
        "properties": {"amount_paise": {"bsonType": ["int", "long"], "minimum": 1}, "currency": {"enum": ["INR"]},
                       "purpose": {"enum": ["listing", "consultation", "extension"]},
                       "status": {"enum": ["created", "captured", "failed", "duplicate", "amount_mismatch"]}}})
    await _validator("payouts", {"bsonType": "object", "required": ["astrologer_id", "amount_paise", "status"],
        "properties": {"amount_paise": {"bsonType": ["int", "long"], "minimum": 1},
                       "status": {"enum": ["requested", "approved", "processing", "paid", "failed", "rejected"]}}})
    await _validator("users", {"bsonType": "object", "required": ["email", "role", "status"],
        "properties": {"role": {"enum": ["customer", "astrologer", "admin"]}, "status": {"enum": ["active", "suspended", "deleted"]}}})


async def m003_seed_config():
    await db.settings.update_one({"_id": "platform"}, {"$setOnInsert": {**DEFAULT_SETTINGS, "updated_at": now()}}, upsert=True)
    for code, name, price, days in [("monthly", "Monthly Listing", 29900, 30), ("quarterly", "Quarterly Listing", 79900, 90)]:
        await db.listing_plans.update_one({"code": code}, {"$setOnInsert": {"_id": new_id(), "name": name, "price_paise": price, "duration_days": days, "active": True, "created_at": now()}}, upsert=True)


MIGRATIONS = [("001_indexes", m001_indexes), ("002_validators", m002_validators), ("003_seed_config", m003_seed_config)]


async def run_migrations():
    for version, fn in MIGRATIONS:
        if await db.schema_migrations.find_one({"_id": version}):
            continue
        await fn()
        await db.schema_migrations.insert_one({"_id": version, "applied_at": now()})
        logger.info(f"migration applied: {version}")


async def seed_admin():
    email = os.environ["ADMIN_EMAIL"].lower()
    pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one({"_id": new_id(), "email": email, "name": "Platform Admin", "role": "admin", "status": "active",
                                   "password_hash": hash_password(pw), "privacy": {}, "created_at": now()})
    elif not verify_password(pw, existing["password_hash"]):
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {"password_hash": hash_password(pw)}})
