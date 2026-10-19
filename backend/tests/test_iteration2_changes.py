# Iteration 2: ledger idempotency (deterministic entry ids), capture retry path, late capture auto-refund,
# XFF-spoof lockout, per-account lock, same-host origin guard, finance summary names, refund_sub 409
import os, sys, json, uuid
sys.path.insert(0, os.path.dirname(__file__))
import pytest, requests
from test_marketplace_e2e import BASE, FE, BE, mdb, register, login, insert_slot, confirmed_booking, act, h, idem, sign, checkout


def post_evt(evt):
    raw = json.dumps(evt).encode()
    return requests.post(f"{BASE}/payments/webhook", data=raw, headers={"X-Webhook-Signature": sign(raw), "Content-Type": "application/json"})


def trial_balance():
    rows = list(mdb.ledger_entries.aggregate([{"$group": {"_id": None, "d": {"$sum": "$debit"}, "c": {"$sum": "$credit"}}}]))
    return rows[0]["d"], rows[0]["c"]


def capture_evt(pay, rec, evt_id=None):
    return {"id": evt_id or "evt_TEST_" + uuid.uuid4().hex, "type": "payment.captured",
            "data": {"order_id": pay["provider_order_id"], "payment_id": rec["_id"], "amount": pay["amount_paise"], "currency": "INR", "fee": rec["fee"]}}


@pytest.fixture(scope="module")
def admin_tok():
    return login(BE["ADMIN_EMAIL"], BE["ADMIN_PASSWORD"])


@pytest.fixture(scope="module")
def astro():
    u = mdb.users.find_one({"email": {"$regex": "^test_astro_"}, "role": "astrologer", "status": "active"}, sort=[("created_at", -1)])
    if not u:
        pytest.skip("run test_marketplace_e2e first")
    return {"id": u["_id"], "token": login(u["email"], "TestPass@123")}


@pytest.fixture(scope="module")
def confirmed(astro):
    c = register("customer", "it2")
    bid, pid = confirmed_booking(c["token"], astro["token"], insert_slot(astro["id"], 400))
    return {"c": c, "bid": bid, "pid": pid}


# --- ledger / webhook idempotency ---
class TestLedgerIdempotency:
    def test_replay_and_new_event_same_capture_no_dupes(self, confirmed):
        pay = mdb.payments.find_one({"_id": confirmed["pid"]})
        rec = mdb.mock_provider_records.find_one({"order_id": pay["provider_order_id"]})
        n_entries = mdb.ledger_entries.count_documents({})
        n_ref = mdb.refunds_disputes.count_documents({"payment_id": pay["_id"]})
        evt = capture_evt(pay, rec)
        r1 = post_evt(evt)
        assert r1.status_code == 200 and r1.json()["status"] == "processed", r1.text
        r2 = post_evt(evt)
        assert r2.json()["status"] == "duplicate_ignored"
        assert mdb.ledger_entries.count_documents({}) == n_entries
        assert mdb.refunds_disputes.count_documents({"payment_id": pay["_id"]}) == n_ref
        b = mdb.bookings.find_one({"_id": confirmed["bid"]})
        assert b["status"] == "confirmed"
        assert sum(1 for x in b["history"] if x["to"] == "confirmed") == 1
        d, c = trial_balance()
        assert d == c

    def test_partial_journal_retry_does_not_duplicate_lines(self, confirmed):
        pay = mdb.payments.find_one({"_id": confirmed["pid"]})
        rec = mdb.mock_provider_records.find_one({"order_id": pay["provider_order_id"]})
        key = f"capture:{pay['_id']}"
        lines_before = mdb.ledger_entries.count_documents({"journal_id": key})
        assert lines_before >= 2
        assert all(e["_id"].startswith(key + "#") for e in mdb.ledger_entries.find({"journal_id": key}))
        # simulate crash after entries but before header
        mdb.journals.delete_one({"_id": key})
        r = post_evt(capture_evt(pay, rec))
        assert r.status_code == 200, r.text
        assert mdb.journals.find_one({"_id": key}) is not None
        assert mdb.ledger_entries.count_documents({"journal_id": key}) == lines_before
        d, c = trial_balance()
        assert d == c

    def test_capture_after_cancel_while_pending_refunds_once(self, astro):
        c = register("customer", "it2late")
        r = requests.post(f"{BASE}/bookings", json={"slot_id": insert_slot(astro["id"], 500), "mode": "chat", "accept_terms": True}, headers=h(c["token"]))
        assert r.status_code == 200, r.text
        bid = r.json()["id"]
        assert act(astro["token"], bid, "accept").status_code == 200
        p = requests.post(f"{BASE}/bookings/{bid}/pay", headers=h(c["token"], **idem()))
        pid = p.json()["payment_id"]
        assert act(c["token"], bid, "cancel", "changed mind").status_code == 200
        assert checkout(c["token"], pid) == "captured"
        refs = list(mdb.refunds_disputes.find({"payment_id": pid, "type": "refund"}))
        assert len(refs) == 1 and refs[0]["_id"] == f"late:{pid}" and refs[0]["amount_paise"] == p.json().get("amount_paise", refs[0]["amount_paise"])
        pay = mdb.payments.find_one({"_id": pid})
        rec = mdb.mock_provider_records.find_one({"order_id": pay["provider_order_id"]})
        n = mdb.ledger_entries.count_documents({})
        assert post_evt(capture_evt(pay, rec)).status_code == 200
        assert mdb.refunds_disputes.count_documents({"payment_id": pid, "type": "refund"}) == 1
        assert mdb.ledger_entries.count_documents({}) == n
        assert mdb.bookings.find_one({"_id": bid})["status"] == "cancelled"
        d, cr = trial_balance()
        assert d == cr


# --- auth hardening ---
class TestAuthHardening:
    def test_xff_spoof_does_not_bypass_lockout(self):
        u = register("customer", "xff")
        codes = [requests.post(f"{BASE}/auth/login", json={"email": u["email"], "password": "wrong"},
                               headers={"X-Forwarded-For": f"10.9.8.{i}"}).status_code for i in range(7)]
        assert codes[:5] == [401] * 5 and codes[5] == 429 and codes[6] == 429, codes
        r = requests.post(f"{BASE}/auth/login", json={"email": u["email"], "password": "TestPass@123"}, headers={"X-Forwarded-For": "1.1.1.1"})
        assert r.status_code == 429
        mdb.login_attempts.delete_many({"identifier": {"$regex": u["email"]}})

    def test_per_account_lock(self, confirmed):
        u = confirmed["c"]  # reuse (register is rate-limited 10/h per IP)
        from datetime import datetime, timezone, timedelta
        t = datetime.now(timezone.utc) + timedelta(minutes=15)
        mdb.login_attempts.insert_one({"identifier": f"acct:{u['email']}", "count": 20, "locked_until": t, "expires_at": t})
        r = requests.post(f"{BASE}/auth/login", json={"email": u["email"], "password": "TestPass@123"})
        assert r.status_code == 429
        mdb.login_attempts.delete_many({"identifier": {"$regex": u["email"]}})
        assert requests.post(f"{BASE}/auth/login", json={"email": u["email"], "password": "TestPass@123"}).status_code == 200

    def test_origin_guard_same_host_and_foreign(self):
        host = FE["REACT_APP_BACKEND_URL"].split("//")[1].rstrip("/")
        assert requests.post(f"{BASE}/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
        assert requests.post(f"{BASE}/auth/logout", headers={"Origin": f"https://{host}"}).status_code == 200
        assert requests.post(f"{BASE}/auth/logout", headers={"Origin": f"https://{host}.evil.example"}).status_code == 403
        assert requests.post(f"{BASE}/auth/logout").status_code == 200


# --- admin finance ---
class TestAdminFinance:
    def test_finance_summary_names_and_late_cancel(self, admin_tok, astro):
        r = requests.get(f"{BASE}/admin/finance/summary", headers=h(admin_tok))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["trial_balance_ok"] is True
        rows = {x["astrologer_id"]: x for x in d["commission_report"]}
        assert all(x.get("name") for x in d["commission_report"]), [x for x in d["commission_report"] if not x.get("name")]
        assert astro["id"] in rows
        late = list(mdb.bookings.find({"astrologer_id": astro["id"], "settlement.retained": {"$gt": 0}, "status": "cancelled"}))
        for b in late:
            assert b["settlement"]["commission"] + b["settlement"]["tax"] + b["settlement"]["astrologer_share"] == b["settlement"]["retained"]
        exp_comm = sum(b["settlement"].get("commission", 0) for b in mdb.bookings.find({"astrologer_id": astro["id"], "settlement": {"$exists": True}}))
        assert rows[astro["id"]]["commission"] == exp_comm

    def test_refund_sub_without_captured_payment_409(self, admin_tok, astro):
        sid = "TEST_sub_" + uuid.uuid4().hex[:8]
        mdb.listing_subscriptions.insert_one({"_id": sid, "astrologer_id": astro["id"], "status": "active", "payment_id": None,
                                              "plan": {"id": "x", "price_paise": 1000, "duration_days": 30}})
        r = requests.post(f"{BASE}/admin/subscriptions/{sid}/refund", json={"reason": "test refund"}, headers=h(admin_tok))
        assert r.status_code == 409, r.text
        assert mdb.listing_subscriptions.find_one({"_id": sid})["status"] == "active"
        mdb.listing_subscriptions.delete_one({"_id": sid})
