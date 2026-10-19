"""Seed clearly-labelled DEMO data for previews/tests. Safe to re-run. Remove with: python seed_demo.py --remove"""
import asyncio
import sys
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

from core import db, now, new_id, hash_password  # noqa: E402

DEMO = [
    ("demo.astro1@nakshatraveda.test", "[DEMO] Acharya Raman Iyer", ["Tamil", "English"], ["Vedic", "Prashna"], 18, 2500, True),
    ("demo.astro2@nakshatraveda.test", "[DEMO] Pandita Meera Joshi", ["Hindi", "Marathi", "English"], ["KP System", "Numerology", "Vastu"], 11, 1800, False),
]
CUSTOMER = ("demo.customer@nakshatraveda.test", "Demo Customer")
PW = "DemoPass@123"


async def remove():
    ids = [u["_id"] async for u in db.users.find({"email": {"$regex": r"@nakshatraveda\.test$"}})]
    await db.astrologer_profiles.delete_many({"_id": {"$in": ids}})
    await db.slots.delete_many({"astrologer_id": {"$in": ids}})
    await db.users.delete_many({"_id": {"$in": ids}})
    print("removed", len(ids))


async def seed():
    for email, name, langs, exp, yrs, rate, cred in DEMO:
        u = await db.users.find_one({"email": email})
        uid = u["_id"] if u else new_id()
        if not u:
            await db.users.insert_one({"_id": uid, "email": email, "name": name, "role": "astrologer", "status": "active", "password_hash": hash_password(PW),
                                       "privacy": {"share_birth_details": True, "marketing_opt_in": False}, "terms_version": "demo", "created_at": now()})
        await db.astrologer_profiles.update_one({"_id": uid}, {"$set": {
            "display_name": name, "bio": "Demo profile for testing the marketplace. Offers interpretive guidance on birth charts; makes no guaranteed predictions.",
            "languages": langs, "expertise": exp, "experience_years": yrs, "credential_summary": "Demo credential", "rates": {"chat": rate, "audio": rate + 1000, "video": rate + 2000},
            "modes_enabled": ["chat", "audio", "video"], "payout_account": {"beneficiary_name": name, "method": "upi", "upi_id": "demo@upi", "account_last4": None, "ifsc": None},
            "identity_status": "approved", "credential_status": "approved" if cred else "not_submitted", "listing_expires_at": now() + timedelta(days=30),
            "account_status": "active", "updated_at": now()}, "$setOnInsert": {"rating_avg": 0, "rating_count": 0, "created_at": now()}}, upsert=True)
        for d in range(1, 4):
            for h in (10, 15):
                start = (now() + timedelta(days=d)).replace(hour=h, minute=0, second=0, microsecond=0)
                await db.slots.update_one({"astrologer_id": uid, "start_at": start}, {"$setOnInsert": {"_id": new_id(), "end_at": start + timedelta(minutes=30), "duration_min": 30, "status": "open", "booking_id": None, "created_at": now()}}, upsert=True)
    if not await db.users.find_one({"email": CUSTOMER[0]}):
        await db.users.insert_one({"_id": new_id(), "email": CUSTOMER[0], "name": CUSTOMER[1], "role": "customer", "status": "active", "password_hash": hash_password(PW),
                                   "privacy": {"share_birth_details": True, "marketing_opt_in": False}, "terms_version": "demo", "created_at": now()})
    print("seeded")


asyncio.run(remove() if "--remove" in sys.argv else seed())
