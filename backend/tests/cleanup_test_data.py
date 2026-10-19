# Removes all TEST_ data (users with emails starting test_ @testmail.in) and every linked financial record, keeping the ledger balanced
from pymongo import MongoClient
from dotenv import dotenv_values

BE = dotenv_values("/app/backend/.env")
db = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
U = [u["_id"] for u in db.users.find({"email": {"$regex": r"^test_.*@testmail\.in$"}})]
U += [d["user_id"] for d in db.deletion_requests.find({"email": {"$regex": r"^test_.*@testmail\.in$"}})]
B = [b["_id"] for b in db.bookings.find({"$or": [{"customer_id": {"$in": U}}, {"astrologer_id": {"$in": U}}]})]
P = [p["_id"] for p in db.payments.find({"$or": [{"user_id": {"$in": U}}, {"booking_id": {"$in": B}}, {"astrologer_id": {"$in": U}}]})]
orders = [p["provider_order_id"] for p in db.payments.find({"_id": {"$in": P}})]
PO = [p["_id"] for p in db.payouts.find({"astrologer_id": {"$in": U}})]
J = [j["_id"] for j in db.journals.find({"$or": [{"refs.booking_id": {"$in": B}}, {"refs.payment_id": {"$in": P}}, {"refs.payout_id": {"$in": PO}}]})]
res = {
    "ledger_entries": db.ledger_entries.delete_many({"journal_id": {"$in": J}}).deleted_count,
    "journals": db.journals.delete_many({"_id": {"$in": J}}).deleted_count,
    "payments": db.payments.delete_many({"_id": {"$in": P}}).deleted_count,
    "mock_provider_records": db.mock_provider_records.delete_many({"order_id": {"$in": orders}}).deleted_count,
    "refunds_disputes": db.refunds_disputes.delete_many({"$or": [{"booking_id": {"$in": B}}, {"payment_id": {"$in": P}}, {"user_id": {"$in": U}}]}).deleted_count,
    "payouts": db.payouts.delete_many({"_id": {"$in": PO}}).deleted_count,
    "chat_messages": db.chat_messages.delete_many({"booking_id": {"$in": B}}).deleted_count,
    "booking_extensions": db.booking_extensions.delete_many({"booking_id": {"$in": B}}).deleted_count,
    "reviews": db.reviews.delete_many({"booking_id": {"$in": B}}).deleted_count,
    "call_sessions": db.call_sessions.delete_many({"booking_id": {"$in": B}}).deleted_count,
    "bookings": db.bookings.delete_many({"_id": {"$in": B}}).deleted_count,
    "slots": db.slots.delete_many({"$or": [{"astrologer_id": {"$in": U}}, {"_id": {"$regex": "^TEST_slot_"}}]}).deleted_count,
    "listing_subscriptions": db.listing_subscriptions.delete_many({"astrologer_id": {"$in": U}}).deleted_count,
    "documents": db.documents.delete_many({"owner_id": {"$in": U}}).deleted_count,
    "verification_cases": db.verification_cases.delete_many({"astrologer_id": {"$in": U}}).deleted_count,
    "birth_profiles": db.birth_profiles.delete_many({"owner_id": {"$in": U}}).deleted_count,
    "deletion_requests": db.deletion_requests.delete_many({"user_id": {"$in": U}}).deleted_count,
    "astrologer_profiles": db.astrologer_profiles.delete_many({"_id": {"$in": U}}).deleted_count,
    "users": db.users.delete_many({"_id": {"$in": U}}).deleted_count,
}
print(res)
rows = list(db.ledger_entries.aggregate([{"$group": {"_id": None, "d": {"$sum": "$debit"}, "c": {"$sum": "$credit"}}}]))
print("trial balance:", rows)
