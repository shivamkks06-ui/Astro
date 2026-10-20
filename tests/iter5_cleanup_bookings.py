# Iteration 5: remove demo-customer bookings created by UI tests and re-open their slots
import sys
from pymongo import MongoClient
from dotenv import dotenv_values

BE = dotenv_values("/app/backend/.env")
db = MongoClient(BE["MONGO_URL"])[BE["DB_NAME"]]
B = sys.argv[1:]
bks = list(db.bookings.find({"_id": {"$in": B}}))
slot_ids = [b.get("slot_id") for b in bks if b.get("slot_id")]
P = [p["_id"] for p in db.payments.find({"booking_id": {"$in": B}})]
orders = [p["provider_order_id"] for p in db.payments.find({"_id": {"$in": P}})]
J = [j["_id"] for j in db.journals.find({"$or": [{"refs.booking_id": {"$in": B}}, {"refs.payment_id": {"$in": P}}]})]
print({
    "ledger": db.ledger_entries.delete_many({"journal_id": {"$in": J}}).deleted_count,
    "journals": db.journals.delete_many({"_id": {"$in": J}}).deleted_count,
    "payments": db.payments.delete_many({"_id": {"$in": P}}).deleted_count,
    "mock": db.mock_provider_records.delete_many({"order_id": {"$in": orders}}).deleted_count,
    "refunds": db.refunds_disputes.delete_many({"booking_id": {"$in": B}}).deleted_count,
    "msgs": db.chat_messages.delete_many({"booking_id": {"$in": B}}).deleted_count,
    "bookings": db.bookings.delete_many({"_id": {"$in": B}}).deleted_count,
    "slots_reopened": db.slots.update_many({"_id": {"$in": slot_ids}}, {"$set": {"status": "open"}, "$unset": {"booking_id": ""}}).modified_count,
})
print("slot docs:", list(db.slots.find({"_id": {"$in": slot_ids}}, {"status": 1})))
print("trial balance:", list(db.ledger_entries.aggregate([{"$group": {"_id": None, "d": {"$sum": "$debit"}, "c": {"$sum": "$credit"}}}])))
