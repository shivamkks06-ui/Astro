# Iteration 14: Places search, Kundli calculation, saved kundlis, daily horoscope
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
OTHER = ("demo.astro1@nakshatraveda.test", "DemoPass@123")
BIRTH = {"date": "1990-08-15", "time": "10:30", "place": "Varanasi", "lat": 25.3176, "lon": 82.9739, "tz": "Asia/Kolkata"}
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code} {r.text[:120]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


@pytest.fixture(scope="module")
def cust():
    return _login(*CUST)


@pytest.fixture(scope="module")
def other():
    return _login(*OTHER)


# ---- Places
class TestPlaces:
    def test_offline_varanasi_first(self):
        r = requests.get(f"{API}/places", params={"q": "varan"})
        assert r.status_code == 200
        d = r.json()
        assert d["source"] == "offline"
        assert d["items"][0]["name"] == "Varanasi"
        assert d["items"][0]["tz"] == "Asia/Kolkata"
        assert d["items"][0]["source"] == "offline"

    def test_min_length(self):
        assert requests.get(f"{API}/places", params={"q": "v"}).status_code == 422

    def test_online_osm(self):
        r = requests.get(f"{API}/places", params={"q": "Reykjavik", "online": "true"}, timeout=20)
        assert r.status_code in (200, 502, 429), r.text
        if r.status_code == 200:
            d = r.json()
            assert d["source"] == "openstreetmap"
            assert d["items"] and d["items"][0]["tz"] == "Atlantic/Reykjavik"
        elif r.status_code == 502:
            assert "unavailable" in r.json()["detail"]
        print("OSM status", r.status_code, r.text[:200])


# ---- Kundli calculation
class TestKundliCalc:
    def test_reference_chart(self):
        r = requests.post(f"{API}/kundli/calculate", json=BIRTH)
        assert r.status_code == 200, r.text
        c = r.json()["chart"]
        assert c["ascendant"]["sign"] == "Libra"
        assert c["moon_sign"] == "Taurus"
        assert c["janma_nakshatra"] == "Rohini"
        names = [p["name"] for p in c["planets"]]
        assert names == PLANETS
        for p in c["planets"]:
            assert p["sign"] in SIGNS
            assert 0 <= p["degree"] < 30
            assert 1 <= p["house"] <= 12
            assert 1 <= p["pada"] <= 4
            assert isinstance(p["retrograde"], bool)
            assert p["nakshatra"]
        assert len(c["houses"]) == 12
        assert c["dasha"]["current"]["mahadasha"]
        assert c["system"]["ayanamsa"] == "Lahiri" and c["system"]["houses"] == "Whole sign" and c["system"]["ephemeris"] == "JPL DE421"
        # rahu/ketu opposite
        rk = {p["name"]: p["lon"] for p in c["planets"]}
        assert abs(((rk["Rahu"] - rk["Ketu"]) % 360) - 180) < 0.01
        print("planets", [(p["name"], p["sign"], round(p["degree"], 2), p["house"], p["retrograde"]) for p in c["planets"]], c["dasha"]["current"])

    @pytest.mark.parametrize("patch", [
        {"tz": "Mars/Olympus"}, {"date": "1899-12-31"}, {"date": "2050-01-01"}, {"lat": 70.0}, {"lat": -67},
        {"date": "1990/08/15"}, {"time": "10:3"}, {"date": "1990-13-40"}, {"time": "25:61"},
    ])
    def test_validation(self, patch):
        r = requests.post(f"{API}/kundli/calculate", json={**BIRTH, **patch})
        assert r.status_code == 422, (patch, r.status_code, r.text)


# ---- Saved kundlis
class TestSavedKundlis:
    def test_unauth(self):
        assert requests.get(f"{API}/kundlis").status_code == 401
        assert requests.post(f"{API}/kundlis", json=BIRTH).status_code == 401

    def test_crud_and_isolation(self, cust, other):
        body = {**BIRTH, "name": "TEST_Kundli"}
        r = cust.post(f"{API}/kundlis", json=body)
        assert r.status_code == 200, r.text
        kid = r.json()["id"]
        assert r.json()["duplicate"] is False
        try:
            r2 = cust.post(f"{API}/kundlis", json=body)
            assert r2.json() == {"id": kid, "duplicate": True}
            lst = cust.get(f"{API}/kundlis").json()["items"]
            it = next(x for x in lst if x["id"] == kid)
            assert it["moon_sign"] == "Taurus" and it["ascendant"] == "Libra" and it["name"] == "TEST_Kundli"
            g = cust.get(f"{API}/kundlis/{kid}")
            assert g.status_code == 200 and g.json()["chart"]["janma_nakshatra"] == "Rohini"
            assert kid not in [x["id"] for x in other.get(f"{API}/kundlis").json()["items"]]
            assert other.get(f"{API}/kundlis/{kid}").status_code == 404
            assert other.delete(f"{API}/kundlis/{kid}").status_code == 404
        finally:
            d = cust.delete(f"{API}/kundlis/{kid}")
        assert d.status_code == 200
        assert cust.get(f"{API}/kundlis/{kid}").status_code == 404


# ---- Daily horoscope
class TestHoroscope:
    def test_today(self):
        r = requests.get(f"{API}/horoscope/daily")
        assert r.status_code == 200
        d = r.json()
        assert d["date"] == datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        assert [t["name"] for t in d["transits"]] == PLANETS
        assert [s["sign"] for s in d["signs"]] == SIGNS
        for s in d["signs"]:
            assert s["tone"] in ("favourable", "mixed", "take care")
            assert s["overview"] and 1 <= s["moon_house"] <= 12
            for c in ("career", "relationships", "health", "finance"):
                cat = s["categories"][c]
                assert cat["tone"] in ("favourable", "mixed", "take care") and cat["text"] and cat["basis"]
        print("ai_status today", d["ai_status"])
        if d["ai_status"] == "ready":
            for s in d["signs"]:
                assert set(s["ai"]) >= {"overview", "career", "relationships", "health", "finance"}

    def test_date_bounds(self):
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        for k in (-1, 1):
            r = requests.get(f"{API}/horoscope/daily", params={"date": (today + timedelta(days=k)).isoformat()})
            assert r.status_code == 200, r.text
            print("date", k, r.json()["ai_status"])
        for bad in ((today + timedelta(days=2)).isoformat(), (today - timedelta(days=2)).isoformat(), "garbage"):
            assert requests.get(f"{API}/horoscope/daily", params={"date": bad}).status_code == 422, bad


# ---- Iteration 15: Navamsa, Panchang, Manglik, Ashtakoota match
GIRL = {"date": "1992-03-02", "time": "05:10", "place": "Delhi", "lat": 28.6139, "lon": 77.209, "tz": "Asia/Kolkata"}
KOOTAS = [("Varna", 1), ("Vashya", 2), ("Tara", 3), ("Yoni", 4), ("Graha Maitri", 5), ("Gana", 6), ("Bhakoot", 7), ("Nadi", 8)]


def _calc(b):
    r = requests.post(f"{API}/kundli/calculate", json=b)
    assert r.status_code == 200, r.text
    return r.json()["chart"]


class TestKundliExtras:
    def test_navamsa(self):
        c = _calc(BIRTH)
        n = c["navamsa"]
        assert n["ascendant"]["sign"] == "Scorpio" and n["ascendant"]["sign_index"] == 7
        assert [p["name"] for p in n["planets"]] == PLANETS
        for p in n["planets"]:
            assert 0 <= p["sign_index"] < 12 and p["sign"] == SIGNS[p["sign_index"]]
            assert p["house"] == (p["sign_index"] - 7) % 12 + 1
        assert [h["house"] for h in n["houses"]] == list(range(1, 13))
        assert n["houses"][0]["sign_index"] == 7

    def test_panchang(self):
        p = _calc(BIRTH)["panchang"]
        print("panchang", p)
        assert p["paksha"] == "Krishna" and p["tithi"] == "Dashami" and 1 <= p["tithi_number"] <= 30
        assert p["tithi_number"] == 25
        assert p["vara"] == "Budhavara (Wednesday)"
        assert p["yoga"] == "Vyaghata" and p["karana"] == "Vanija"
        assert p["sunrise"] == "05:31"
        assert p["nakshatra"] == "Rohini"

    def test_pre_sunrise_previous_weekday(self):
        # 1990-08-15 is Wednesday; 04:00 is before sunrise -> Tuesday
        p = _calc({**BIRTH, "time": "04:00"})["panchang"]
        assert p["vara"] == "Mangalavara (Tuesday)", p
        p2 = _calc({**BIRTH, "time": "05:45"})["panchang"]
        assert p2["vara"] == "Budhavara (Wednesday)", p2

    def test_manglik(self):
        m = _calc(BIRTH)["manglik"]
        print("manglik", m)
        for k in ("mars_house_from_lagna", "mars_house_from_moon", "from_lagna", "from_moon", "manglik", "cancellations"):
            assert k in m
        assert m["manglik"] is True
        assert "Mars is in its own sign" in m["cancellations"]
        assert m["manglik"] == (m["from_lagna"] or m["from_moon"])

    def test_saved_includes_extras(self, cust):
        r = cust.post(f"{API}/kundlis", json={**BIRTH, "name": "TEST_Iter15"})
        assert r.status_code in (200, 201), r.text
        kid = r.json().get("id") or r.json().get("kundli", {}).get("id")
        try:
            g = cust.get(f"{API}/kundlis/{kid}")
            assert g.status_code == 200, g.text
            c = g.json()["chart"]
            assert c["navamsa"]["ascendant"]["sign"] == "Scorpio"
            assert c["panchang"]["tithi"] == "Dashami"
            assert c["manglik"]["manglik"] is True
        finally:
            assert cust.delete(f"{API}/kundlis/{kid}").status_code in (200, 204)


class TestMatch:
    def test_reference_match(self):
        r = requests.post(f"{API}/kundli/match", json={"boy": BIRTH, "girl": GIRL})
        assert r.status_code == 200, r.text
        d = r.json()
        res = d["result"]
        print("match", res)
        assert [(k["name"], k["max"]) for k in res["kootas"]] == KOOTAS
        for k in res["kootas"]:
            assert 0 <= k["score"] <= k["max"]
        assert res["total"] == sum(k["score"] for k in res["kootas"]) <= 36
        assert res["total"] == 18 and res["band"] == "Average"
        assert isinstance(res["nadi_dosha"], bool) and isinstance(res["bhakoot_dosha"], bool)
        for s in ("boy", "girl"):
            assert res[s]["moon_sign"] in SIGNS and res[s]["nakshatra"] and "manglik" in res[s]["manglik"]
        assert res["boy"]["moon_sign"] == "Taurus"
        assert d["boy"]["place"] == "Varanasi" and d["girl"]["place"] == "Delhi"

    def test_same_person_nadi_zero(self):
        r = requests.post(f"{API}/kundli/match", json={"boy": BIRTH, "girl": BIRTH})
        assert r.status_code == 200
        res = r.json()["result"]
        nadi = next(k for k in res["kootas"] if k["name"] == "Nadi")
        assert nadi["score"] == 0 and res["nadi_dosha"] is True
        assert res["bhakoot_dosha"] is False

    @pytest.mark.parametrize("patch", [{"boy": {**BIRTH, "tz": "Mars/Base"}}, {"girl": {**GIRL, "lat": 80}},
                                       {"girl": {**GIRL, "date": "1899-01-01"}}, {"boy": {**BIRTH, "time": "25:00"}}, {"girl": None}])
    def test_match_validation(self, patch):
        body = {"boy": BIRTH, "girl": GIRL, **patch}
        r = requests.post(f"{API}/kundli/match", json=body)
        assert r.status_code == 422, (patch, r.status_code, r.text[:200])
