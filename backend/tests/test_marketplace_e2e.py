# End-to-end regression suite: auth, authz, onboarding, listing, payments/webhooks, bookings, chat, ledger, disputes, payouts, admin, privacy
import os, json, hmac, hashlib, uuid, time
from datetime import datetime, timedelta, timezone
import pytest, requests
from pymongo import MongoClient
from dotenv import dotenv_values

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
BASE = FE["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
SECRET = BE["PAYMENT_WEBHOOK_SECRET"]
mdb = MongoClient(BE["MONGO_URL"], tz_aware=True)[BE["DB_NAME"]]
RUN = uuid.uuid4().hex[:6]
DOM = "testmail.in"
S = {}  # shared state across ordered tests


def now():
    return datetime.now(timezone.utc)


def h(tok, **extra):
    return {"Authorization": f"Bearer {tok}", **extra}


def idem():
    return {"Idempotency-Key": "k" + uuid.uuid4().hex}


def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def register(role, tag):
    email = f"TEST_{tag}_{RUN}@{DOM}"
    r = requests.post(f"{BASE}/auth/register", json={"name": f"TEST {tag}", "email": email, "password": "TestPass@123", "role": role, "accept_terms": True})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"token": d["access_token"], "id": d["user"]["id"], "email": email.lower()}


def sign(body: bytes):
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def checkout(tok, pid, outcome="success"):
    r = requests.post(f"{BASE}/payments/{pid}/mock-checkout", json={"outcome": outcome}, headers=h(tok))
    assert r.status_code == 200, r.text
    return r.json()["status"]


def insert_slot(aid, minutes_ahead, dur=30):
    sid = "TEST_slot_" + uuid.uuid4().hex[:10]
    st = (now() + timedelta(minutes=minutes_ahead)).replace(microsecond=0)
    mdb.slots.insert_one({"_id": sid, "astrologer_id": aid, "start_at": st, "end_at": st + timedelta(minutes=dur), "duration_min": dur, "status": "open", "booking_id": None, "created_at": now()})
    return sid


def act(tok, bid, action, reason=""):
    return requests.post(f"{BASE}/bookings/{bid}/actions/{action}", json={"reason": reason}, headers=h(tok))


def confirmed_booking(cust, astro, slot_id):
    r = requests.post(f"{BASE}/bookings", json={"slot_id": slot_id, "mode": "chat", "accept_terms": True}, headers=h(cust))
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    assert act(astro, bid, "accept").status_code == 200
    p = requests.post(f"{BASE}/bookings/{bid}/pay", headers=h(cust, **idem()))
    assert p.status_code == 200, p.text
    assert checkout(cust, p.json()["payment_id"]) == "captured"
    assert requests.get(f"{BASE}/bookings/{bid}", headers=h(cust)).json()["status"] == "confirmed"
    return bid, p.json()["payment_id"]


# ---------- Auth ----------
class TestAuth:
    def test_setup_accounts(self):
        S["admin"] = login(BE["ADMIN_EMAIL"], BE["ADMIN_PASSWORD"])
        S["c1"], S["c2"], S["c3"] = register("customer", "c1"), register("customer", "c2"), register("customer", "c3")
        S["a"] = register("astrologer", "astro")
        S["demo_c"] = login("demo.customer@nakshatraveda.test", "DemoPass@123")
        S["demo_a1"] = login("demo.astro1@nakshatraveda.test", "DemoPass@123")

    def test_register_admin_role_rejected(self):
        r = requests.post(f"{BASE}/auth/register", json={"name": "x y", "email": f"TEST_adm_{RUN}@{DOM}", "password": "TestPass@123", "role": "admin", "accept_terms": True})
        assert r.status_code == 422

    def test_register_requires_terms(self):
        r = requests.post(f"{BASE}/auth/register", json={"name": "x y", "email": f"TEST_nt_{RUN}@{DOM}", "password": "TestPass@123", "role": "customer", "accept_terms": False})
        assert r.status_code in (400, 422)

    def test_bcrypt_and_cookies_me_refresh_logout(self):
        u = mdb.users.find_one({"email": S["c1"]["email"]})
        assert u["password_hash"].startswith("$2b$")
        s = requests.Session()
        r = s.post(f"{BASE}/auth/login", json={"email": S["c1"]["email"], "password": "TestPass@123"})
        sc = r.headers.get("set-cookie", "").lower()
        assert "httponly" in sc and "access_token" in sc and "refresh_token" in sc
        assert s.get(f"{BASE}/auth/me").json()["email"] == S["c1"]["email"]
        assert s.post(f"{BASE}/auth/refresh").status_code == 200
        assert s.post(f"{BASE}/auth/logout").status_code == 200

    def test_lockout_after_5_failures(self):
        e = S["c3"]["email"]
        codes = [requests.post(f"{BASE}/auth/login", json={"email": e, "password": "wrong"}).status_code for _ in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429
        assert requests.post(f"{BASE}/auth/login", json={"email": e, "password": "TestPass@123"}).status_code == 429
        mdb.login_attempts.delete_many({"identifier": {"$regex": e}})

    def test_cors_and_origin_guard(self):
        r = requests.post(f"{BASE}/auth/logout", headers={"Origin": "https://evil.example"})
        assert r.status_code == 403
        r = requests.options(f"{BASE}/auth/login", headers={"Origin": FE["REACT_APP_BACKEND_URL"], "Access-Control-Request-Method": "POST"})
        assert r.headers.get("access-control-allow-origin") == FE["REACT_APP_BACKEND_URL"]


# ---------- AuthZ + onboarding ----------
class TestOnboarding:
    def test_customer_cannot_admin(self):
        assert requests.get(f"{BASE}/admin/list/users", headers=h(S["c1"]["token"])).status_code == 403
        assert requests.get(f"{BASE}/admin/overview", headers=h(S["a"]["token"])).status_code == 403

    def test_new_astrologer_not_listed(self):
        assert requests.get(f"{BASE}/astrologers/{S['a']['id']}").status_code == 404
        ids = [i["id"] for i in requests.get(f"{BASE}/astrologers?limit=50").json()["items"]]
        assert S["a"]["id"] not in ids

    def test_profile_update_ignores_privileged_fields(self):
        body = {"display_name": "TEST Astro", "bio": "TEST bio", "languages": ["Hindi"], "expertise": ["Vedic"], "experience_years": 5,
                "rates": {"chat": 10000, "audio": 0, "video": 0}, "modes_enabled": ["chat"],
                "payout_account": {"beneficiary_name": "TEST Astro", "method": "upi", "upi_id": "test@upi"},
                "identity_status": "approved", "listing_expires_at": "2099-01-01T00:00:00Z", "commission_bps": 0}
        r = requests.put(f"{BASE}/astrologer/profile", json=body, headers=h(S["a"]["token"]))
        assert r.status_code in (200, 422)
        p = mdb.astrologer_profiles.find_one({"_id": S["a"]["id"]})
        assert p["identity_status"] == "not_submitted" and p["listing_expires_at"] is None and "commission_bps" not in p
        if r.status_code == 422:
            body = {k: v for k, v in body.items() if k not in ("identity_status", "listing_expires_at", "commission_bps")}
            assert requests.put(f"{BASE}/astrologer/profile", json=body, headers=h(S["a"]["token"])).status_code == 200

    def test_subscription_blocked_before_approval(self):
        plan = mdb.listing_plans.find_one({"active": True}, sort=[("price_paise", 1)])
        S["plan"] = plan
        r = requests.post(f"{BASE}/astrologer/subscriptions", json={"plan_id": plan["_id"]}, headers=h(S["a"]["token"], **idem()))
        assert r.status_code == 400

    def test_upload_and_submit(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        r = requests.post(f"{BASE}/astrologer/documents", data={"kind": "identity", "doc_type": "PAN"}, files={"file": ("pan.png", png, "image/png")}, headers=h(S["a"]["token"]))
        assert r.status_code == 200, r.text
        S["doc"] = r.json()["id"]
        bad = requests.post(f"{BASE}/astrologer/documents", data={"kind": "identity", "doc_type": "PAN"}, files={"file": ("x.txt", b"hi", "text/plain")}, headers=h(S["a"]["token"]))
        assert bad.status_code == 415
        assert requests.post(f"{BASE}/astrologer/verification/identity/submit", headers=h(S["a"]["token"])).status_code == 200
        S["case"] = mdb.verification_cases.find_one({"astrologer_id": S["a"]["id"], "kind": "identity"})["_id"]

    def test_astrologer_cannot_decide_or_settings(self):
        assert requests.post(f"{BASE}/admin/verification/{S['case']}/decision", json={"decision": "approve", "notes": "self"}, headers=h(S["a"]["token"])).status_code == 403
        assert requests.put(f"{BASE}/admin/settings", json={"commission_bps": 0}, headers=h(S["a"]["token"])).status_code == 403

    def test_admin_review_doc_link_reject_resubmit_approve(self):
        ad = S["admin"]
        c = requests.get(f"{BASE}/admin/verification/{S['case']}", headers=h(ad)).json()
        assert c["documents"][0]["id"] == S["doc"]
        link = requests.post(f"{BASE}/admin/documents/{S['doc']}/access", headers=h(ad)).json()
        assert link["expires_in"] == 300
        st = requests.get(FE["REACT_APP_BACKEND_URL"] + link["url_path"])
        assert st.status_code == 200 and st.content.startswith(b"\x89PNG")
        assert requests.get(f"{BASE}/documents/stream?token=bad").status_code == 401
        assert requests.post(f"{BASE}/admin/verification/{S['case']}/decision", json={"decision": "reject", "notes": "blurry"}, headers=h(ad)).status_code == 200
        assert mdb.astrologer_profiles.find_one({"_id": S["a"]["id"]})["identity_status"] == "rejected"
        assert requests.post(f"{BASE}/astrologer/verification/identity/submit", headers=h(S["a"]["token"])).status_code == 200
        assert requests.post(f"{BASE}/admin/verification/{S['case']}/decision", json={"decision": "approve", "notes": "ok now"}, headers=h(ad)).status_code == 200
        assert mdb.astrologer_profiles.find_one({"_id": S["a"]["id"]})["identity_status"] == "approved"
        assert mdb.verification_cases.find_one({"astrologer_id": S["a"]["id"], "kind": "credential"}) is None

    def test_listing_failure_then_success_then_extend(self):
        a = S["a"]["token"]
        r = requests.post(f"{BASE}/astrologer/subscriptions", json={"plan_id": S["plan"]["_id"]}, headers=h(a, **idem()))
        assert r.status_code == 200
        pid = r.json()["payment_id"]
        assert requests.get(f"{BASE}/astrologers/{S['a']['id']}").status_code == 404
        assert checkout(a, pid, "failure") == "failed"
        assert requests.get(f"{BASE}/astrologers/{S['a']['id']}").status_code == 404
        r = requests.post(f"{BASE}/astrologer/subscriptions", json={"plan_id": S["plan"]["_id"]}, headers=h(a, **idem()))
        pid2 = r.json()["payment_id"]
        S["listing_pid_failed_reused"] = pid2 == pid
        st = checkout(a, pid2, "success")
        assert st == "captured", f"listing payment after failure -> {st} (same pid reused: {pid2 == pid})"
        assert requests.get(f"{BASE}/astrologers/{S['a']['id']}").status_code == 200
        exp1 = mdb.astrologer_profiles.find_one({"_id": S["a"]["id"]})["listing_expires_at"]
        assert abs((exp1 - now()) - timedelta(days=S["plan"]["duration_days"])) < timedelta(minutes=5)
        r = requests.post(f"{BASE}/astrologer/subscriptions", json={"plan_id": S["plan"]["_id"]}, headers=h(a, **idem()))
        assert checkout(a, r.json()["payment_id"]) == "captured"
        exp2 = mdb.astrologer_profiles.find_one({"_id": S["a"]["id"]})["listing_expires_at"]
        assert abs((exp2 - exp1) - timedelta(days=S["plan"]["duration_days"])) < timedelta(minutes=1)


# ---------- Booking, webhook, chat, settlement ----------
class TestBookingFlow:
    def test_book_price_snapshot_and_conflicts(self):
        aid = S["a"]["id"]
        S["slot1"] = insert_slot(aid, 6)
        r = requests.post(f"{BASE}/bookings", json={"slot_id": S["slot1"], "mode": "chat", "accept_terms": True, "price": {"gross_paise": 1}, "gross_paise": 1}, headers=h(S["c1"]["token"]))
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["status"] == "requested" and b["price"]["gross_paise"] == 10000 * 30
        S["b1"] = b["id"]
        assert requests.post(f"{BASE}/bookings", json={"slot_id": S["slot1"], "mode": "chat", "accept_terms": True}, headers=h(S["c2"]["token"])).status_code == 409
        s2 = insert_slot(aid, 600)
        assert requests.post(f"{BASE}/bookings", json={"slot_id": s2, "mode": "audio", "accept_terms": True}, headers=h(S["c2"]["token"])).status_code == 400

    def test_authz_and_state_machine(self):
        b = S["b1"]
        assert requests.get(f"{BASE}/bookings/{b}", headers=h(S["c2"]["token"])).status_code == 404
        assert requests.get(f"{BASE}/bookings/{b}/messages", headers=h(S["c2"]["token"])).status_code == 404
        assert act(S["a"]["token"], b, "start").status_code == 409
        assert act(S["c1"]["token"], b, "accept").status_code == 403
        assert act(S["a"]["token"], b, "accept").status_code == 200
        p = requests.post(f"{BASE}/bookings/{b}/pay", headers=h(S["c1"]["token"], **idem()))
        assert requests.get(f"{BASE}/bookings/{b}", headers=h(S["c1"]["token"])).json()["status"] == "payment_pending"
        S["p1"] = p.json()["payment_id"]
        assert checkout(S["c1"]["token"], S["p1"]) == "captured"
        assert requests.get(f"{BASE}/bookings/{b}", headers=h(S["c1"]["token"])).json()["status"] == "confirmed"

    def test_webhook_security_replay_and_duplicate_capture(self):
        body = json.dumps({"id": "evt_x", "type": "payment.captured", "data": {}}).encode()
        assert requests.post(f"{BASE}/payments/webhook", data=body, headers={"X-Webhook-Signature": "bad", "Content-Type": "application/json"}).status_code == 401
        evt = mdb.webhook_events.find_one({"type": "payment.captured"}, sort=[("received_at", -1)])
        pay = mdb.payments.find_one({"_id": S["p1"]})
        rec = mdb.mock_provider_records.find_one({"order_id": pay["provider_order_id"]})
        before_j, before_l = mdb.journals.count_documents({}), mdb.ledger_entries.count_documents({})
        raw = json.dumps({"id": evt["_id"], "type": "payment.captured", "data": {"order_id": pay["provider_order_id"], "payment_id": rec["_id"], "amount": pay["amount_paise"], "currency": "INR", "fee": rec["fee"]}}).encode()
        r = requests.post(f"{BASE}/payments/webhook", data=raw, headers={"X-Webhook-Signature": sign(raw), "Content-Type": "application/json"})
        assert r.json()["status"] == "duplicate_ignored"
        assert (mdb.journals.count_documents({}), mdb.ledger_entries.count_documents({})) == (before_j, before_l)
        # second payment doc for same booking, captured by a new event id
        dup_id, order = "TEST_pay_" + uuid.uuid4().hex[:8], "TEST_order_" + uuid.uuid4().hex[:8]
        mdb.payments.insert_one({**{k: v for k, v in pay.items() if k not in ("_id",)}, "_id": dup_id, "status": "created", "provider_order_id": order,
                                 "provider_payment_id": None, "idempotency_key": "TEST_" + dup_id, "created_at": now()})
        raw = json.dumps({"id": "evt_TEST_" + uuid.uuid4().hex, "type": "payment.captured", "data": {"order_id": order, "payment_id": "mock_pay_TEST" + uuid.uuid4().hex[:8], "amount": pay["amount_paise"], "currency": "INR", "fee": 0}}).encode()
        assert requests.post(f"{BASE}/payments/webhook", data=raw, headers={"X-Webhook-Signature": sign(raw)}).status_code == 200
        assert mdb.payments.find_one({"_id": dup_id})["status"] == "duplicate"
        assert mdb.refunds_disputes.find_one({"_id": f"dup:{dup_id}"}) is not None
        assert mdb.payments.count_documents({"booking_id": S["b1"], "status": "captured"}) == 1

    def test_chat_and_early_complete_prorata(self):
        b, a, c = S["b1"], S["a"]["token"], S["c1"]["token"]
        assert requests.post(f"{BASE}/bookings/{b}/messages", json={"client_msg_id": "m000001", "text": "hi"}, headers=h(c)).status_code == 409
        assert act(a, b, "start").status_code == 200
        assert requests.post(f"{BASE}/bookings/{b}/messages", json={"client_msg_id": "m000001", "text": "hello"}, headers=h(c)).status_code == 200
        assert requests.post(f"{BASE}/bookings/{b}/messages", json={"client_msg_id": "m000002", "text": "namaste"}, headers=h(a)).status_code == 200
        assert len(requests.get(f"{BASE}/bookings/{b}/messages", headers=h(c)).json()) == 2
        assert requests.post(f"{BASE}/bookings/{b}/messages", json={"client_msg_id": "m000003", "text": "x"}, headers=h(S["c2"]["token"])).status_code == 404
        r = act(a, b, "complete")
        assert r.status_code == 200
        st = r.json()["settlement"]
        assert st["refund"] > 0 and st["refund_reason"] == "astrologer_ended_early_prorata"
        assert st["commission"] == st["retained"] * 2500 // 10000
        j = mdb.journals.find_one({"_id": f"settle:{b}"})
        assert j is not None
        e = mdb.ledger_entries.find_one({"journal_id": f"settle:{b}", "account": f"liability:astrologer_payable:{S['a']['id']}"})
        assert e["credit"] == st["astrologer_share"]
        assert abs((e["available_at"] - now()) - timedelta(hours=48)) < timedelta(minutes=5)
        S["b1_settle"] = st

    def test_review_rules(self):
        c = S["c1"]["token"]
        assert requests.post(f"{BASE}/bookings/{S['b1']}/review", json={"rating": 5, "comment": "TEST good"}, headers=h(c)).status_code == 200
        assert requests.post(f"{BASE}/bookings/{S['b1']}/review", json={"rating": 4}, headers=h(c)).status_code == 409

    def test_dispute_and_resolve(self):
        b, c = S["b1"], S["c1"]["token"]
        assert act(c, b, "dispute", "astrologer left early").status_code == 200
        ret = S["b1_settle"]["retained"]
        assert requests.post(f"{BASE}/admin/disputes/{b}/resolve", json={"refund_paise": ret + 1, "notes": "too much"}, headers=h(S["admin"])).status_code == 400
        assert requests.post(f"{BASE}/admin/disputes/{b}/resolve", json={"refund_paise": ret // 2, "notes": "half"}, headers=h(S["admin"])).status_code == 200
        assert mdb.journals.find_one({"_id": f"refund:dispute:{b}"}) is not None
        assert requests.get(f"{BASE}/bookings/{b}", headers=h(c)).json()["status"] == "completed"

    def test_cancel_full_and_late(self):
        aid, c, a = S["a"]["id"], S["c2"]["token"], S["a"]["token"]
        b2, _ = confirmed_booking(c, a, insert_slot(aid, 300))
        st = act(c, b2, "cancel").json()["settlement"]
        assert st["refund"] == st["gross"] and st["retained"] == 0
        b3, p3 = confirmed_booking(c, a, insert_slot(aid, 60))
        st = act(c, b3, "cancel").json()["settlement"]
        assert st["refund"] == st["gross"] // 2
        assert mdb.journals.find_one({"_id": f"cancel_retain:{b3}"}) is not None
        S["p3"] = p3


# ---------- Payouts ----------
class TestPayouts:
    def test_payout_over_eligible_rejected(self):
        r = requests.post(f"{BASE}/astrologer/payouts", json={"amount_paise": 50000}, headers=h(S["a"]["token"]))
        assert r.status_code == 400

    def test_payout_success_and_failure(self):
        a, ad, aid = S["a"]["token"], S["admin"], S["a"]["id"]
        mdb.ledger_entries.update_many({"account": f"liability:astrologer_payable:{aid}"}, {"$set": {"available_at": now() - timedelta(hours=1)}})
        for p in mdb.payments.find({"astrologer_id": aid, "status": "captured", "purpose": "consultation"}):
            assert requests.post(f"{BASE}/admin/payments/{p['_id']}/reconcile", headers=h(ad)).json()["matched"] is True
        bal = requests.get(f"{BASE}/astrologer/earnings", headers=h(a)).json()["balances"]
        assert bal["eligible_paise"] >= 100000, bal
        r = requests.post(f"{BASE}/astrologer/payouts", json={"amount_paise": 50000}, headers=h(a))
        assert r.status_code == 200
        po = r.json()["id"]
        assert requests.post(f"{BASE}/astrologer/payouts", json={"amount_paise": 50000}, headers=h(a)).status_code in (400, 409)
        assert requests.post(f"{BASE}/admin/payouts/{po}/approve", headers=h(ad)).status_code == 200
        assert mdb.payouts.find_one({"_id": po})["status"] == "processing"
        assert requests.post(f"{BASE}/admin/payouts/{po}/mock-settlement", json={"outcome": "processed"}, headers=h(ad)).status_code == 200
        d = mdb.payouts.find_one({"_id": po})
        assert d["status"] == "paid" and d["settlement_ref"].startswith("MOCKUTR")
        r = requests.post(f"{BASE}/astrologer/payouts", json={"amount_paise": 50000}, headers=h(a))
        assert r.status_code == 200, r.text
        po2 = r.json()["id"]
        requests.post(f"{BASE}/admin/payouts/{po2}/approve", headers=h(ad))
        before = requests.get(f"{BASE}/astrologer/earnings", headers=h(a)).json()["balances"]["ledger_balance_paise"]
        requests.post(f"{BASE}/admin/payouts/{po2}/mock-settlement", json={"outcome": "failed"}, headers=h(ad))
        assert mdb.payouts.find_one({"_id": po2})["status"] == "failed"
        after = requests.get(f"{BASE}/astrologer/earnings", headers=h(a)).json()["balances"]["ledger_balance_paise"]
        assert after - before == 50000
        assert requests.get(f"{BASE}/admin/finance/summary", headers=h(ad)).json()["trial_balance_ok"] is True


# ---------- Admin ----------
class TestAdmin:
    def test_lists_export(self):
        ad = h(S["admin"])
        r = requests.get(f"{BASE}/admin/list/users?q=TEST_c1_{RUN}&role=customer&page=1&limit=5", headers=ad).json()
        assert r["total"] == 1 and "password_hash" not in r["items"][0]
        assert requests.get(f"{BASE}/admin/list/nope", headers=ad).status_code == 404
        csvr = requests.get(f"{BASE}/admin/export/payments?purpose=listing", headers=ad)
        assert csvr.status_code == 200 and "text/csv" in csvr.headers["content-type"]

    def test_suspend_user_and_astrologer(self):
        ad = h(S["admin"])
        assert requests.post(f"{BASE}/admin/users/{S['c2']['id']}/status", json={"status": "suspended", "reason": "TEST"}, headers=ad).status_code == 200
        assert requests.get(f"{BASE}/auth/me", headers=h(S["c2"]["token"])).status_code == 403
        requests.post(f"{BASE}/admin/users/{S['c2']['id']}/status", json={"status": "active", "reason": "TEST"}, headers=ad)
        requests.post(f"{BASE}/admin/users/{S['a']['id']}/status", json={"status": "suspended", "reason": "TEST"}, headers=ad)
        assert requests.get(f"{BASE}/astrologers/{S['a']['id']}").status_code == 404
        requests.post(f"{BASE}/admin/users/{S['a']['id']}/status", json={"status": "active", "reason": "TEST"}, headers=ad)
        assert requests.get(f"{BASE}/astrologers/{S['a']['id']}").status_code == 200

    def test_settings_and_plan_audit(self):
        ad = h(S["admin"])
        assert requests.put(f"{BASE}/admin/settings", json={"commission_bps": 6000}, headers=ad).status_code == 422
        assert requests.put(f"{BASE}/admin/settings", json={"commission_bps": 2500}, headers=ad).status_code == 200
        pl = S["plan"]
        assert requests.patch(f"{BASE}/admin/plans/{pl['_id']}", json={"price_paise": pl["price_paise"] + 100}, headers=ad).status_code == 200
        requests.patch(f"{BASE}/admin/plans/{pl['_id']}", json={"price_paise": pl["price_paise"]}, headers=ad)
        acts = {a["action"] for a in mdb.audit_logs.find({"created_at": {"$gt": now() - timedelta(minutes=30)}})}
        for x in ("plan_updated", "settings_updated", "payout_approved", "dispute_resolved", "payment_reconciled", "verification_approved"):
            assert x in acts, x


# ---------- Privacy ----------
class TestPrivacy:
    def test_birth_profiles_privacy_export_deletion(self):
        c1, c3 = S["c1"]["token"], S["c3"]["token"]
        bp = {"label": "Me", "full_name": "TEST Person", "birth_date": "1990-05-01", "birth_time": "10:30", "birth_place": "Pune"}
        r = requests.post(f"{BASE}/me/birth-profiles", json=bp, headers=h(c1))
        assert r.status_code == 200
        bid = r.json()["id"]
        assert requests.put(f"{BASE}/me/birth-profiles/{bid}", json={**bp, "label": "Self"}, headers=h(c1)).status_code == 200
        assert all(x["id"] != bid for x in requests.get(f"{BASE}/me/birth-profiles", headers=h(c3)).json())
        assert requests.put(f"{BASE}/me/birth-profiles/{bid}", json=bp, headers=h(c3)).status_code == 404
        assert requests.delete(f"{BASE}/me/birth-profiles/{bid}", headers=h(c3)).status_code == 404
        assert requests.post(f"{BASE}/me/birth-profiles", json={**bp, "birth_date": "2999-01-01"}, headers=h(c1)).status_code == 422
        assert requests.put(f"{BASE}/me/privacy", json={"share_birth_details": False, "marketing_opt_in": False}, headers=h(c1)).status_code == 200
        ex = requests.get(f"{BASE}/me/export", headers=h(c1)).json()
        assert ex["account"]["privacy"]["share_birth_details"] is False and len(ex["bookings"]) >= 1 and "password_hash" not in ex["account"]
        assert requests.delete(f"{BASE}/me/birth-profiles/{bid}", headers=h(c1)).status_code == 200
        assert requests.post(f"{BASE}/me/deletion-request", json={"reason": "TEST"}, headers=h(c3)).status_code == 200
        did = mdb.deletion_requests.find_one({"user_id": S["c3"]["id"]})["_id"]
        assert requests.post(f"{BASE}/admin/deletion-requests/{did}/process", json={"approve": True, "notes": "TEST ok"}, headers=h(S["admin"])).status_code == 200
        u = mdb.users.find_one({"_id": S["c3"]["id"]})
        assert u["status"] == "deleted" and u["email"].endswith("@deleted.invalid")
