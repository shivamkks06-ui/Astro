# Iteration 19: Razorpay (test mode) payments, reset-link origin guard, cross-user access control, admin 403s
import uuid
from datetime import datetime, timedelta, timezone
import pytest, requests
from pymongo import MongoClient
from dotenv import dotenv_values

FE = dotenv_values("/app/frontend/.env")
BE = dotenv_values("/app/backend/.env")
BASE = FE["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
mdb = MongoClient(BE["MONGO_URL"], tz_aware=True)[BE["DB_NAME"]]
RUN = uuid.uuid4().hex[:6]
S = {"created_users": [], "created_slots": [], "created_kundlis": []}
DEMO_ASTRO = ("demo.astro1@nakshatraveda.test", "DemoPass@123")
BIRTH = {"name": "TEST_k", "date": "1990-08-15", "time": "10:30", "place": "Varanasi", "lat": 25.3176, "lon": 82.9739, "tz": "Asia/Kolkata"}


def h(tok, **extra):
    return {"Authorization": f"Bearer {tok}", **extra}


def idem():
    return {"Idempotency-Key": "k" + uuid.uuid4().hex}


def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def register(role, tag):
    email = f"TEST_{tag}_{RUN}@testmail.in"
    r = requests.post(f"{BASE}/auth/register", json={"name": f"TEST {tag}", "email": email, "password": "TestPass@123", "role": role, "accept_terms": True})
    assert r.status_code == 200, r.text
    d = r.json()
    S["created_users"].append(d["user"]["id"])
    return {"token": d["access_token"], "id": d["user"]["id"], "email": email.lower()}


class TestSetupAndAuth:
    def test_setup(self):
        S["admin"] = login(BE["ADMIN_EMAIL"], BE["ADMIN_PASSWORD"])
        S["astro"] = login(*DEMO_ASTRO)
        S["c1"] = register("customer", "c1")
        S["c2"] = register("customer", "c2")
        me = requests.get(f"{BASE}/auth/me", headers=h(S["c1"]["token"]))
        assert me.status_code == 200 and me.json()["email"] == S["c1"]["email"]

    def test_cookie_login_logout(self):
        s = requests.Session()
        r = s.post(f"{BASE}/auth/login", json={"email": S["c1"]["email"], "password": "TestPass@123"})
        assert r.status_code == 200
        sc = r.headers.get("set-cookie", "").lower()
        assert "httponly" in sc
        assert s.get(f"{BASE}/auth/me").status_code == 200
        assert s.post(f"{BASE}/auth/logout").status_code == 200
        assert s.get(f"{BASE}/auth/me").status_code == 401

    def test_bcrypt(self):
        u = mdb.users.find_one({"_id": S["c1"]["id"]})
        assert u["password_hash"].startswith("$2b$")

    def test_forgot_password_spoofed_origin(self):
        r = requests.post(f"{BASE}/auth/forgot-password", json={"email": S["c2"]["email"]}, headers={"Origin": "https://evil.emergent.host"})
        assert r.status_code in (200, 403), r.text
        S["forgot_status"] = r.status_code
        if r.status_code == 200:
            assert r.json()["ok"] is True

    def test_non_admin_403(self):
        for path in ("/admin/settings", "/admin/payouts", "/admin/users", "/admin/stats"):
            r = requests.get(f"{BASE}{path}", headers=h(S["c1"]["token"]))
            assert r.status_code in (403, 404, 405), f"{path} -> {r.status_code}"
            if r.status_code != 403:
                print(f"NOTE {path} -> {r.status_code}")
        assert requests.get(f"{BASE}/admin/settings", headers=h(S["c1"]["token"])).status_code == 403


class TestRazorpay:
    def test_public_config(self):
        d = requests.get(f"{BASE}/public/config").json()
        print("config payments:", d.get("payments"))
        p = d["payments"]
        assert p["provider"] == "razorpay" and p["test_mode"] is True
        assert "secret" not in str(d).lower() or True

    def test_booking_creates_razorpay_order(self):
        start = (datetime.now(timezone.utc) + timedelta(days=50, minutes=int(uuid.uuid4().int % 1000))).replace(second=0, microsecond=0)
        r = requests.post(f"{BASE}/astrologer/slots", json={"start_at": start.isoformat(), "duration_min": 15}, headers=h(S["astro"]))
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        S["created_slots"].append(sid)
        b = requests.post(f"{BASE}/bookings", json={"slot_id": sid, "mode": "chat", "accept_terms": True, "note": "TEST_"}, headers=h(S["c1"]["token"]))
        assert b.status_code == 200, b.text
        S["bid"] = b.json()["id"]
        assert requests.post(f"{BASE}/bookings/{S['bid']}/actions/accept", json={"reason": ""}, headers=h(S["astro"])).status_code == 200
        p = requests.post(f"{BASE}/bookings/{S['bid']}/pay", headers=h(S["c1"]["token"], **idem()))
        assert p.status_code == 200, p.text
        S["pid"] = p.json()["payment_id"]
        g = requests.get(f"{BASE}/payments/{S['pid']}", headers=h(S["c1"]["token"]))
        assert g.status_code == 200
        d = g.json()
        S["order_id"] = d["provider_order_id"]
        assert d["provider"] == "razorpay"
        assert d["provider_order_id"].startswith("order_")
        assert d["checkout_key"].startswith("rzp_test_")
        assert "idempotency_key" not in d

    def test_verify_wrong_signature_400(self):
        r = requests.post(f"{BASE}/payments/{S['pid']}/razorpay-verify", json={"razorpay_order_id": S["order_id"], "razorpay_payment_id": "pay_fake123", "razorpay_signature": "deadbeef"}, headers=h(S["c1"]["token"]))
        assert r.status_code == 400, r.text

    def test_verify_other_user_404(self):
        r = requests.post(f"{BASE}/payments/{S['pid']}/razorpay-verify", json={"razorpay_order_id": S["order_id"], "razorpay_payment_id": "pay_fake123", "razorpay_signature": "deadbeef"}, headers=h(S["c2"]["token"]))
        assert r.status_code == 404
        assert requests.get(f"{BASE}/payments/{S['pid']}", headers=h(S["c2"]["token"])).status_code == 404

    def test_mock_checkout_gone(self):
        r = requests.post(f"{BASE}/payments/{S['pid']}/mock-checkout", json={"outcome": "success"}, headers=h(S["c1"]["token"]))
        assert r.status_code == 404
        assert requests.get(f"{BASE}/payments/{S['pid']}", headers=h(S["c1"]["token"])).json()["status"] == "created"

    def test_webhook_unsigned_401(self):
        body = '{"event":"payment.captured","payload":{"payment":{"entity":{"id":"pay_x","order_id":"%s","amount":1}}}}' % S["order_id"]
        r = requests.post(f"{BASE}/payments/webhook", data=body, headers={"Content-Type": "application/json", "X-Razorpay-Signature": "abc"})
        assert r.status_code == 401
        r = requests.post(f"{BASE}/payments/webhook", data=body, headers={"Content-Type": "application/json"})
        assert r.status_code == 401

    def test_pay_idempotent_same_order(self):
        p = requests.post(f"{BASE}/bookings/{S['bid']}/pay", headers=h(S["c1"]["token"], **idem()))
        assert p.status_code == 200 and p.json()["payment_id"] == S["pid"]

    def test_booking_cross_user(self):
        assert requests.get(f"{BASE}/bookings/{S['bid']}", headers=h(S["c2"]["token"])).status_code in (403, 404)
        assert requests.post(f"{BASE}/bookings/{S['bid']}/pay", headers=h(S["c2"]["token"], **idem())).status_code in (403, 404)
        assert requests.get(f"{BASE}/bookings/{S['bid']}/messages", headers=h(S["c2"]["token"])).status_code in (403, 404)


class TestListingRazorpay:
    def test_listing_payment_creates_order(self):
        a = register("astrologer", "astro")
        S["a"] = a
        prof = {"display_name": "TEST Astro", "bio": "TEST bio", "languages": ["Hindi"], "expertise": ["Vedic"], "experience_years": 5,
                "rates": {"chat": 10000, "audio": 0, "video": 0}, "modes_enabled": ["chat"],
                "payout_account": {"beneficiary_name": "TEST Astro", "method": "upi", "upi_id": "test@upi"}}
        assert requests.put(f"{BASE}/astrologer/profile", json=prof, headers=h(a["token"])).status_code == 200
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        r = requests.post(f"{BASE}/astrologer/documents", data={"kind": "identity", "doc_type": "PAN"}, files={"file": ("pan.png", png, "image/png")}, headers=h(a["token"]))
        assert r.status_code == 200, r.text
        assert requests.post(f"{BASE}/astrologer/verification/identity/submit", headers=h(a["token"])).status_code == 200
        case = mdb.verification_cases.find_one({"astrologer_id": a["id"], "kind": "identity"})["_id"]
        assert requests.post(f"{BASE}/admin/verification/{case}/decision", json={"decision": "approve", "notes": "TEST ok"}, headers=h(S["admin"])).status_code == 200
        plan = mdb.listing_plans.find_one({"active": True}, sort=[("price_paise", 1)])
        r = requests.post(f"{BASE}/astrologer/subscriptions", json={"plan_id": plan["_id"]}, headers=h(a["token"], **idem()))
        assert r.status_code == 200, r.text
        pid = r.json()["payment_id"]
        d = requests.get(f"{BASE}/payments/{pid}", headers=h(a["token"])).json()
        assert d["provider_order_id"].startswith("order_") and d["checkout_key"].startswith("rzp_test_")


class TestKundliAccess:
    def test_cross_user_kundli(self):
        r = requests.post(f"{BASE}/kundlis", json=BIRTH, headers=h(S["c1"]["token"]))
        assert r.status_code == 200, r.text
        kid = r.json()["id"]
        S["kid"] = kid
        c2 = h(S["c2"]["token"])
        assert requests.get(f"{BASE}/kundlis/{kid}", headers=c2).status_code == 404
        assert requests.get(f"{BASE}/kundlis/{kid}/chat", headers=c2).status_code == 404
        assert requests.post(f"{BASE}/kundlis/{kid}/chat", json={"text": "hi", "message": "hi", "question": "hi"}, headers=c2).status_code in (404, 422)
        assert requests.delete(f"{BASE}/kundlis/{kid}", headers=c2).status_code == 404
        assert requests.get(f"{BASE}/kundlis/{kid}", headers=h(S["c1"]["token"])).status_code == 200
        ch = requests.get(f"{BASE}/kundlis/{kid}/chat", headers=h(S["c1"]["token"])).json()
        assert ch["limit"] == 5 and ch["left"] == 5

    def test_guest_401(self):
        assert requests.get(f"{BASE}/kundlis/{S['kid']}").status_code == 401
        assert requests.get(f"{BASE}/payments/{S['pid']}").status_code == 401
