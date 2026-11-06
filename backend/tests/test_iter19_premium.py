# Iteration 19: time_accuracy, new report sections, planet rows, forgot/reset password, legal-related API
import os
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
BIRTH = {"date": "1990-08-15", "time": "10:30", "place": "Varanasi", "lat": 25.3176, "lon": 82.9739, "tz": "Asia/Kolkata"}


def _env():
    vals = {}
    for line in open("/app/backend/.env"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            vals[k] = v.strip('"')
    return vals


ENV = _env()
DB = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]


# NOTE: run with -n 0 (fixture clears rate_limits; parallel workers interfere)
@pytest.fixture(autouse=True)
def _clear_rl():
    DB.rate_limits.delete_many({"_id": {"$regex": "^(forgot|reset|kundli)"}})
    yield


def _calc(**kw):
    r = requests.post(f"{API}/kundli/calculate", json={**BIRTH, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _sec(d, sid):
    return [s for s in d["chart"]["report"]["sections"] if s["id"] == sid][0]


# Time accuracy
class TestAccuracy:
    def test_unknown_forces_noon(self):
        d = _calc(time_accuracy="unknown", time="07:45")
        assert d["input"]["time"] == "12:00" and d["input"]["time_unknown"] is True
        assert d["chart"]["report"]["time_unknown"] is True

    def test_approximate_notes(self):
        d = _calc(time_accuracy="approximate")
        b = _sec(d, "birth")
        assert any("approximate" in f for f in b["facts"])
        assert any("Lagna" in t and "edge" in t for t in b["text"])

    def test_exact_no_approx_note(self):
        d = _calc(time_accuracy="exact")
        b = _sec(d, "birth")
        assert not any("approximate" in f for f in b["facts"])

    def test_invalid_accuracy_422(self):
        r = requests.post(f"{API}/kundli/calculate", json={**BIRTH, "time_accuracy": "maybe"})
        assert r.status_code == 422

    def test_legacy_no_accuracy(self):
        d = _calc()
        assert d["input"]["time_accuracy"] is None


# Report sections and planet rows
class TestReport:
    def test_new_sections_order(self):
        ids = [s["id"] for s in _calc()["chart"]["report"]["sections"]]
        for s in ["personality", "mind", "emotions", "behaviour", "spirituality"]:
            assert s in ids
        assert ids.index("core") < ids.index("personality") < ids.index("mind") < ids.index("emotions") < ids.index("behaviour") < ids.index("charts")
        for s in ["personality", "mind", "emotions", "behaviour", "spirituality"]:
            sec = _sec(_calc(), s)
            assert sec["text"] or sec["facts"]

    def test_planet_rows(self):
        p = _sec(_calc(), "planets")
        assert len(p["items"]) == 9
        for it in p["items"]:
            labels = [r[0] for r in it["rows"]]
            for lab in ["Dispositor", "D9 sign", "Dasha link"]:
                assert lab in labels, (it["title"], labels)

    def test_d9_interpretation(self):
        c = _sec(_calc(), "charts")
        assert any("D9" in t and ("vargottama" in t.lower()) for t in c["text"])


# Forgot / reset password
class TestForgotReset:
    def test_forgot_generic_unknown(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": f"nouser_{uuid.uuid4().hex[:6]}@example.com"})
        assert r.status_code == 200 and r.json()["ok"] is True
        msg = r.json()["message"]
        r2 = requests.post(f"{API}/auth/forgot-password", json={"email": "delivered@resend.dev"})
        assert r2.status_code == 200 and r2.json()["message"] == msg

    def test_forgot_invalid_email_422(self):
        assert requests.post(f"{API}/auth/forgot-password", json={"email": "notanemail"}).status_code == 422

    def test_forgot_rate_limit_email(self):
        e = f"rl_{uuid.uuid4().hex[:6]}@example.com"
        codes = [requests.post(f"{API}/auth/forgot-password", json={"email": e}).status_code for _ in range(4)]
        assert codes[:3] == [200, 200, 200] and codes[3] == 429

    def test_forgot_rate_limit_ip(self):
        codes = [requests.post(f"{API}/auth/forgot-password", json={"email": f"ip_{uuid.uuid4().hex[:6]}@example.com"}).status_code for _ in range(6)]
        assert codes[:5] == [200] * 5 and codes[5] == 429

    def test_reset_bad_token_400(self):
        r = requests.post(f"{API}/auth/reset-password", json={"token": "x" * 40, "password": "NewPass@1234"})
        assert r.status_code == 400 and "invalid" in r.json()["detail"].lower()

    def test_reset_short_password_422(self):
        assert requests.post(f"{API}/auth/reset-password", json={"token": "x" * 40, "password": "short"}).status_code == 422


# Save kundli with accuracy -> list
class TestSaved:
    def test_save_list_delete(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": "demo.customer@nakshatraveda.test", "password": "DemoPass@123"})
        if r.status_code != 200:
            pytest.skip("login failed")
        s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        r = s.post(f"{API}/kundlis", json={**BIRTH, "name": "TEST_iter19", "time_accuracy": "approximate"})
        assert r.status_code == 200, r.text
        kid = r.json()["id"]
        try:
            items = s.get(f"{API}/kundlis").json()["items"]
            it = [i for i in items if i["id"] == kid][0]
            assert it["time_accuracy"] == "approximate" and it["name"] == "TEST_iter19"
            g = s.get(f"{API}/kundlis/{kid}").json()
            assert any("approximate" in f for f in _sec(g, "birth")["facts"])
        finally:
            assert s.delete(f"{API}/kundlis/{kid}").status_code in (200, 204)
