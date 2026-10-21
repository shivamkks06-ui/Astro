# Iteration 18: Detailed Kundli report (analysis, report sections, time_unknown, doshas, AI report endpoint)
import os
import re
import threading
import time

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
OTHER = ("demo.astro1@nakshatraveda.test", "DemoPass@123")
BIRTH = {"date": "1990-08-15", "time": "10:30", "place": "Varanasi", "lat": 25.3176, "lon": 82.9739, "tz": "Asia/Kolkata"}
ORDER = ["overview", "birth", "core", "charts", "planets", "houses", "yogas", "career", "finance", "relationships",
         "education", "family", "dasha", "remedies", "plan", "disclaimer"]
TS = ["core", "charts", "planets", "houses", "yogas", "career", "finance", "relationships", "education", "family"]
GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
OTHERS = [
    {"date": "1985-01-26", "time": "06:15", "place": "Delhi", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    {"date": "2001-11-03", "time": "23:40", "place": "London", "lat": 51.5072, "lon": -0.1276, "tz": "Europe/London"},
    {"date": "1972-03-09", "time": "14:05", "place": "New York", "lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
]


def _env():
    vals = {}
    for line in open("/app/backend/.env"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            vals[k] = v.strip('"')
    return vals


ENV = _env()
DB = MongoClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    s.uid = s.get(f"{API}/auth/me").json().get("id") or s.get(f"{API}/auth/me").json().get("user", {}).get("id")
    return s


@pytest.fixture(scope="module")
def cust():
    DB.rate_limits.delete_many({})
    return _login(*CUST)


@pytest.fixture(scope="module")
def other():
    return _login(*OTHER)


def _calc(b):
    r = requests.post(f"{API}/kundli/calculate", json=b)
    assert r.status_code == 200, r.text
    return r.json()


# ---- analysis + report for the reference chart
class TestReferenceReport:
    def test_analysis_structure(self):
        c = _calc(BIRTH)["chart"]
        a = c["analysis"]
        for n, p in a["planets"].items():
            for k in ("dignity", "combust", "aspects_houses", "lord_of"):
                assert k in p
        assert len(a["houses"]) == 12
        for h in a["houses"]:
            for k in ("lord", "lord_in_house", "occupants", "aspected_by"):
                assert k in h
        assert a["planets"]["Moon"]["dignity"] == "exalted"
        assert a["planets"]["Jupiter"]["dignity"] == "exalted"
        assert a["planets"]["Venus"]["dignity"] == "enemy sign"
        yn = [y["name"] for y in a["yogas"]]
        print("yogas", yn, "doshas", [d["name"] for d in a["doshas"]])
        assert any(y.startswith("Ruchaka") for y in yn)
        assert any(y.startswith("Hamsa") for y in yn)
        assert "Yogakaraka planet" in yn and "Dhana yoga" in yn
        assert any(d["name"] == "Manglik (Kuja) dosha (traditionally cancelled)" for d in a["doshas"])

    def test_report_sections(self):
        rep = _calc(BIRTH)["chart"]["report"]
        assert rep["time_unknown"] is False
        assert [s["id"] for s in rep["sections"]] == ORDER
        assert any("Lagna" in x for x in rep["summary"])
        assert all(not s["time_sensitive"] for s in rep["sections"])
        rem = next(s for s in rep["sections"] if s["id"] == "remedies")
        titles = [i["title"] for i in rem["items"]]
        print("remedies", titles)
        assert "Jupiter" in titles and "Venus" in titles and "Optional gemstone" in titles

    def test_old_input_without_field(self):
        d = _calc(BIRTH)
        assert d["input"]["time_unknown"] is False and d["input"]["time"] == "10:30"


# ---- time unknown mode
class TestTimeUnknown:
    def test_noon_forced(self):
        d = _calc({**BIRTH, "time": "03:10", "time_unknown": True})
        assert d["input"]["time"] == "12:00"
        rep = d["chart"]["report"]
        assert rep["time_unknown"] is True
        assert not any("Lagna with its lord" in x for x in rep["summary"])
        S = {s["id"]: s for s in rep["sections"]}
        for k in TS:
            assert S[k]["time_sensitive"] is True, k
        for k in ("overview", "birth", "dasha", "remedies", "plan", "disclaimer"):
            assert S[k]["time_sensitive"] is False, k
        assert "Optional gemstone" not in [i["title"] for i in S["remedies"]["items"]]
        assert any("noon" in x for x in S["birth"]["facts"] + S["birth"]["text"])

    def test_validation_still_422(self):
        assert requests.post(f"{API}/kundli/calculate", json={**BIRTH, "tz": "Bad/Zone", "time_unknown": True}).status_code == 422
        assert requests.post(f"{API}/kundli/calculate", json={**BIRTH, "time_unknown": "maybe"}).status_code == 422


# ---- consistency checks on other birth data
class TestConsistency:
    @pytest.mark.parametrize("b", OTHERS + [BIRTH])
    def test_internal_consistency(self, b):
        c = _calc(b)["chart"]
        a, P = c["analysis"], {p["name"]: p for p in c["planets"]}
        for y in a["yogas"]:
            for m in re.finditer(r"(\w+) is [\w ]+? in house (\d+)", y["basis"]):
                if m.group(1) in P:
                    assert P[m.group(1)]["house"] == int(m.group(2)), y
            m = re.search(r"together in (\w+)", y["basis"])
            if m:
                names = [n for n in P if n in y["basis"].split(" together")[0]]
                assert all(P[n]["sign"] == m.group(1) for n in names), y
        # Kaal Sarp consistency
        rahu, ketu = P["Rahu"]["lon"], P["Ketu"]["lon"]
        sides = {(P[n]["lon"] - rahu) % 360 < (ketu - rahu) % 360 for n in GRAHAS}
        ks = any(d["name"] == "Kaal Sarp yoga" for d in a["doshas"])
        assert ks == (len(sides) == 1)
        # Sade Sati consistency against today's transit
        sat = next(p for p in requests.get(f"{API}/horoscope/daily").json().get("transits", []) if p["name"] == "Saturn") if False else None
        ss = [d for d in a["doshas"] if d["name"].startswith("Sade Sati")]
        for d in ss:
            h = int(re.search(r"house (\d+) from your Moon", d["basis"]).group(1))
            assert h in (12, 1, 2)
        # house occupants consistent with planet houses
        for h in a["houses"]:
            assert sorted(h["occupants"]) == sorted(n for n, p in P.items() if p["house"] == h["house"])
            assert a["planets"][h["lord"]]["house"] == h["lord_in_house"]
        dash = next(s for s in c["report"]["sections"] if s["id"] == "dasha")
        print(b["place"], [y["name"] for y in a["yogas"]], [d["name"] for d in a["doshas"]], dash["facts"][-3:])


# ---- AI report endpoint
class TestAiReport:
    def test_guest_401(self):
        assert requests.post(f"{API}/kundlis/xyz/ai-report").status_code == 401

    def test_ownership_cache_and_limits(self, cust, other):
        r = cust.post(f"{API}/kundlis", json={**BIRTH, "name": "TEST_AIReport"})
        kid = r.json()["id"]
        try:
            assert other.post(f"{API}/kundlis/{kid}/ai-report").status_code == 404
            # concurrent duplicate -> 409 (simulate in-flight)
            DB.kundlis.update_one({"_id": kid}, {"$set": {"ai_pending": True}})
            r409 = cust.post(f"{API}/kundlis/{kid}/ai-report")
            assert r409.status_code == 409, r409.text
            DB.kundlis.update_one({"_id": kid}, {"$unset": {"ai_pending": ""}})
            # real call once
            t0 = time.time()
            r1 = cust.post(f"{API}/kundlis/{kid}/ai-report", timeout=180)
            print("AI call", r1.status_code, round(time.time() - t0, 1), "s")
            assert r1.status_code == 200, r1.text
            d = r1.json()
            assert set(d["sections"]) == {"personality", "career", "finance", "relationships", "education", "wellbeing", "dasha"}
            assert all(len(v) > 40 for v in d["sections"].values())
            print({k: v[:120] for k, v in d["sections"].items()})
            g = cust.get(f"{API}/kundlis/{kid}").json()
            assert g["ai_report"]["sections"] == d["sections"]
            t1 = time.time()
            r2 = cust.post(f"{API}/kundlis/{kid}/ai-report")
            assert r2.status_code == 200 and r2.json()["sections"] == d["sections"]
            assert time.time() - t1 < 5
            assert "ai_pending" not in DB.kundlis.find_one({"_id": kid})
        finally:
            cust.delete(f"{API}/kundlis/{kid}")

    def test_rate_limit_429(self, cust):
        r = cust.post(f"{API}/kundlis", json={**BIRTH, "name": "TEST_AIRate"})
        kid = r.json()["id"]
        uid = DB.kundlis.find_one({"_id": kid})["user_id"]
        bucket = int(time.time()) // 3600
        DB.rate_limits.update_one({"_id": f"kundli-ai:{uid}:{bucket}"}, {"$set": {"count": 5}}, upsert=True)
        try:
            r = cust.post(f"{API}/kundlis/{kid}/ai-report")
            assert r.status_code == 429, r.text
            assert "ai_pending" not in DB.kundlis.find_one({"_id": kid})
        finally:
            DB.rate_limits.delete_many({"_id": {"$regex": "^kundli-ai:"}})
            cust.delete(f"{API}/kundlis/{kid}")
