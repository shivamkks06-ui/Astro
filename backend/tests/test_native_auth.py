# Iteration 3: native (Android/Capacitor) auth path - X-Client: native refresh_token in body, body-based refresh,
# origin guard allows https://localhost, web cookie flow unchanged, call-token 503 for in_progress audio booking
import os, sys, uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
import pytest, requests
from test_marketplace_e2e import BASE, mdb

CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
ASTRO = "demo.astro1@nakshatraveda.test"


def _login(headers=None, session=None):
    s = session or requests
    return s.post(f"{BASE}/auth/login", json={"email": CUST[0], "password": CUST[1]}, headers=headers or {})


class TestNativeAuth:
    def test_native_login_returns_refresh_token(self):
        r = _login({"X-Client": "native"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("refresh_token"), str) and len(d["refresh_token"]) > 20
        assert d["access_token"] and d["user"]["email"] == CUST[0]

    def test_web_login_has_no_refresh_token_in_body(self):
        r = _login()
        assert r.status_code == 200
        assert "refresh_token" not in r.json()
        assert "refresh_token" in r.cookies and "access_token" in r.cookies

    def test_body_refresh_without_cookie(self):
        rt = _login({"X-Client": "native"}).json()["refresh_token"]
        r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": rt})
        assert r.status_code == 200, r.text
        at = r.json()["access_token"]
        me = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {at}"})
        assert me.status_code == 200 and me.json()["email"] == CUST[0]

    def test_invalid_refresh_401(self):
        assert requests.post(f"{BASE}/auth/refresh", json={"refresh_token": "garbage.token.x"}).status_code == 401
        assert requests.post(f"{BASE}/auth/refresh", json={}).status_code == 401
        assert requests.post(f"{BASE}/auth/refresh").status_code == 401

    def test_access_token_cannot_be_used_as_refresh(self):
        at = _login({"X-Client": "native"}).json()["access_token"]
        assert requests.post(f"{BASE}/auth/refresh", json={"refresh_token": at}).status_code == 401

    def test_origin_https_localhost_allowed(self):
        r = _login({"X-Client": "native", "Origin": "https://localhost"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "https://localhost"
        bad = _login({"Origin": "https://evil.example"})
        assert bad.status_code == 403

    def test_web_cookie_session_and_refresh(self):
        s = requests.Session()
        assert _login(session=s).status_code == 200
        assert s.get(f"{BASE}/auth/me").status_code == 200
        s.cookies.set("access_token", "expired", domain=s.cookies.list_domains()[0])
        assert s.get(f"{BASE}/auth/me").status_code == 401
        assert s.post(f"{BASE}/auth/refresh").status_code == 200
        assert s.get(f"{BASE}/auth/me").status_code == 200
        assert s.post(f"{BASE}/auth/logout").status_code == 200


@pytest.fixture(scope="class")
def audio_booking():
    cust = mdb.users.find_one({"email": CUST[0]})
    astro = mdb.users.find_one({"email": ASTRO})
    tpl = mdb.bookings.find_one({"customer_id": cust["_id"]}) or mdb.bookings.find_one({})
    if not (cust and astro and tpl):
        pytest.skip("demo data missing")
    doc = dict(tpl)
    bid = "TEST_call_" + uuid.uuid4().hex[:10]
    doc.update({"_id": bid, "customer_id": cust["_id"], "astrologer_id": astro["_id"], "mode": "audio", "status": "in_progress",
                "started_at": datetime.now(timezone.utc), "active": True, "slot_id": "TEST_slot_" + uuid.uuid4().hex})
    mdb.bookings.insert_one(doc)
    yield bid
    mdb.bookings.delete_one({"_id": bid})
    mdb.call_sessions.delete_many({"booking_id": bid})


class TestCallToken:
    def test_call_token_503(self, audio_booking):
        at = _login().json()["access_token"]
        r = requests.post(f"{BASE}/bookings/{audio_booking}/call-token", headers={"Authorization": f"Bearer {at}"})
        assert r.status_code == 503, r.text
        assert "operational" in r.json()["detail"].lower()
