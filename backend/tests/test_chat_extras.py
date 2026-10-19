# Extra edge cases: chat rate limit, review requires customer joined, settings validation, live booking for UI chat test
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest, requests
from test_marketplace_e2e import BASE, mdb, register, login, insert_slot, confirmed_booking, act, h, S


@pytest.fixture(scope="module")
def astro():
    u = mdb.users.find_one({"email": {"$regex": "^test_astro_"}, "role": "astrologer", "status": "active"}, sort=[("created_at", -1)])
    if not u:
        pytest.skip("run test_marketplace_e2e first to create a TEST astrologer")
    return {"id": u["_id"], "token": login(u["email"], "TestPass@123")}


def test_review_requires_joined(astro):
    c = register("customer", "rv")
    bid, _ = confirmed_booking(c["token"], astro["token"], insert_slot(astro["id"], 6))
    assert act(astro["token"], bid, "start").status_code == 200
    assert act(c["token"], bid, "complete").status_code == 200
    assert requests.post(f"{BASE}/bookings/{bid}/review", json={"rating": 5}, headers=h(c["token"])).status_code == 403


def test_chat_rate_limit_and_live_booking_for_ui(astro):
    c = register("customer", "chat")
    bid, _ = confirmed_booking(c["token"], astro["token"], insert_slot(astro["id"], 7))
    assert act(astro["token"], bid, "start").status_code == 200
    codes = [requests.post(f"{BASE}/bookings/{bid}/messages", json={"client_msg_id": f"rl{i:06d}", "text": f"m{i}"}, headers=h(astro["token"])).status_code for i in range(22)]
    assert 429 in codes, codes
    # an admin can read history but not post
    from dotenv import dotenv_values
    BE = dotenv_values("/app/backend/.env")
    ad = login(BE["ADMIN_EMAIL"], BE["ADMIN_PASSWORD"])
    assert requests.get(f"{BASE}/bookings/{bid}/messages", headers=h(ad)).status_code == 200
    assert requests.post(f"{BASE}/bookings/{bid}/messages", json={"client_msg_id": "adm0001", "text": "x"}, headers=h(ad)).status_code == 403
    with open("/tmp/live_booking.txt", "w") as f:
        f.write(f"{bid} {c['email']}")


def test_settings_validation():
    from dotenv import dotenv_values
    BE = dotenv_values("/app/backend/.env")
    ad = login(BE["ADMIN_EMAIL"], BE["ADMIN_PASSWORD"])
    assert requests.put(f"{BASE}/admin/settings", json={"bogus": 1}, headers=h(ad)).status_code == 422
    assert requests.put(f"{BASE}/admin/settings", json={"commission_bps": -1}, headers=h(ad)).status_code == 422
    assert requests.put(f"{BASE}/admin/settings", json={"commission_bps": True}, headers=h(ad)).status_code == 422
