# Iteration 7: astrologer profile photo upload / serve / delete / admin removal / suspension tests
import io
import os
import uuid

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = ("shivamkks9088@outlook.com", "Nakshatra@Admin2026")
ASTRO1 = ("demo.astro1@nakshatraveda.test", "DemoPass@123")
ASTRO2 = ("demo.astro2@nakshatraveda.test", "DemoPass@123")
CUSTOMER = ("demo.customer@nakshatraveda.test", "DemoPass@123")


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    s.uid = r.json().get("user", {}).get("id")
    return s


def img_bytes(w, h, fmt="JPEG", exif=False, color=(200, 120, 40)):
    im = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    kw = {}
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "TESTCAM"  # Make
        ex[0x0110] = "TESTMODEL"
        kw["exif"] = ex.tobytes()
    im.save(buf, fmt, **kw)
    return buf.getvalue()


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def astro1():
    s = login(*ASTRO1)
    s.uid = s.get(f"{BASE_URL}/api/auth/me").json().get("id") or s.uid
    yield s
    s.delete(f"{BASE_URL}/api/astrologer/photo")


@pytest.fixture(scope="module")
def customer():
    return login(*CUSTOMER)


@pytest.fixture(scope="module")
def test_astro(admin):
    email = f"test_photo_{uuid.uuid4().hex[:8]}@testmail.in"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={"name": "TEST_ Photo Astro", "email": email, "password": "TestPass@123", "role": "astrologer", "accept_terms": True})
    assert r.status_code in (200, 201), r.text
    s = login(email, "TestPass@123")
    s.uid = s.get(f"{BASE_URL}/api/auth/me").json()["id"]
    return s


def up(s, data, name="p.jpg", ctype="image/jpeg"):
    return s.post(f"{BASE_URL}/api/astrologer/photo", files={"file": (name, data, ctype)})


class TestUploadAndServe:
    def test_upload_valid_jpeg_with_exif(self, astro1):
        r = up(astro1, img_bytes(800, 600, exif=True))
        assert r.status_code == 200, r.text
        url = r.json()["photo_url"]
        assert url.startswith(f"/api/astrologers/{astro1.uid}/photo?v=")
        astro1.photo_url = url

    def test_get_photo_webp_512_immutable_no_exif(self, astro1):
        r = requests.get(BASE_URL + astro1.photo_url)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/webp")
        # preview ingress rewrites Cache-Control to no-store; backend itself sends immutable (verified on :8001)
        cc = r.headers.get("cache-control", "")
        assert "immutable" in cc or "no-store" in cc
        im = Image.open(io.BytesIO(r.content))
        assert im.format == "WEBP"
        assert im.size == (512, 512)
        assert len(im.getexif()) == 0
        assert b"TESTCAM" not in r.content

    def test_profile_and_public_include_photo_url(self, astro1):
        p = astro1.get(f"{BASE_URL}/api/astrologer/profile").json()["profile"]
        assert p["photo_url"] == astro1.photo_url
        assert "photo_path" not in p
        d = requests.get(f"{BASE_URL}/api/astrologers/{astro1.uid}").json()
        assert d["photo_url"] == astro1.photo_url
        assert "photo_path" not in d
        lst = requests.get(f"{BASE_URL}/api/astrologers").json()
        items = lst if isinstance(lst, list) else lst.get("items", lst.get("astrologers", []))
        mine = [a for a in items if a["id"] == astro1.uid]
        assert mine and mine[0]["photo_url"] == astro1.photo_url
        assert all("photo_path" not in a for a in items)

    def test_change_photo_png_new_version(self, astro1):
        r = up(astro1, img_bytes(300, 900, "PNG"), "p.png", "image/png")
        assert r.status_code == 200, r.text
        assert r.json()["photo_url"] != astro1.photo_url
        astro1.photo_url = r.json()["photo_url"]
        im = Image.open(io.BytesIO(requests.get(BASE_URL + astro1.photo_url).content))
        assert im.size == (512, 512)


class TestRejections:
    def test_pdf_415(self, test_astro):
        assert up(test_astro, b"%PDF-1.4 fake", "a.pdf", "application/pdf").status_code == 415

    def test_text_415(self, test_astro):
        assert up(test_astro, b"hello", "a.txt", "text/plain").status_code == 415

    def test_renamed_non_image_415(self, test_astro):
        assert up(test_astro, b"not an image at all" * 50, "fake.jpg", "image/jpeg").status_code == 415

    def test_small_image_422(self, test_astro):
        assert up(test_astro, img_bytes(100, 100)).status_code == 422

    def test_over_5mb_413(self, test_astro):
        assert up(test_astro, b"\xff\xd8" + os.urandom(5 * 1024 * 1024 + 10)).status_code == 413

    def test_customer_403(self, customer):
        assert up(customer, img_bytes(300, 300)).status_code == 403

    def test_logged_out_401(self):
        r = requests.post(f"{BASE_URL}/api/astrologer/photo", files={"file": ("p.jpg", img_bytes(300, 300), "image/jpeg")})
        assert r.status_code == 401


class TestSuspendAndAdmin:
    def test_suspended_photo_404(self, test_astro, admin):
        r = up(test_astro, img_bytes(400, 400))
        assert r.status_code == 200, r.text
        url = r.json()["photo_url"]
        assert requests.get(BASE_URL + url).status_code == 200
        assert admin.post(f"{BASE_URL}/api/admin/users/{test_astro.uid}/status", json={"status": "suspended", "reason": "TEST suspend"}).status_code == 200
        assert requests.get(BASE_URL + url + "&x=1").status_code == 404
        assert admin.post(f"{BASE_URL}/api/admin/users/{test_astro.uid}/status", json={"status": "active", "reason": "TEST restore"}).status_code == 200
        assert requests.get(BASE_URL + url + "&x=2").status_code == 200

    def test_non_admin_remove_403(self, customer, astro1):
        r = customer.post(f"{BASE_URL}/api/admin/astrologers/{astro1.uid}/photo/remove", json={"reason": "nope nope"})
        assert r.status_code == 403
        r = astro1.post(f"{BASE_URL}/api/admin/astrologers/{astro1.uid}/photo/remove", json={"reason": "nope nope"})
        assert r.status_code == 403

    def test_admin_list_has_photo_version(self, admin, test_astro):
        r = admin.get(f"{BASE_URL}/api/admin/list/astrologer_profiles", params={"q": test_astro.uid})
        assert r.status_code == 200
        it = r.json()["items"][0]
        assert it.get("photo_version")

    def test_admin_remove_photo_and_audit(self, admin, test_astro):
        r = admin.post(f"{BASE_URL}/api/admin/astrologers/{test_astro.uid}/photo/remove", json={"reason": "TEST inappropriate"})
        assert r.status_code == 200, r.text
        assert requests.get(f"{BASE_URL}/api/astrologers/{test_astro.uid}/photo?v=after").status_code == 404
        p = test_astro.get(f"{BASE_URL}/api/astrologer/profile").json()["profile"]
        assert p["photo_url"] is None
        logs = admin.get(f"{BASE_URL}/api/admin/list/audit_logs", params={"q": "profile_photo_removed_by_admin", "limit": 20}).json()["items"]
        assert any(l.get("target_id") == test_astro.uid for l in logs), logs[:2]
        # second removal -> 404
        r = admin.post(f"{BASE_URL}/api/admin/astrologers/{test_astro.uid}/photo/remove", json={"reason": "TEST again"})
        assert r.status_code == 404


class TestDelete:
    def test_delete_photo_then_404(self, astro1):
        r = astro1.delete(f"{BASE_URL}/api/astrologer/photo")
        assert r.status_code == 200
        assert requests.get(f"{BASE_URL}/api/astrologers/{astro1.uid}/photo?v=gone").status_code == 404
        assert requests.get(f"{BASE_URL}/api/astrologers/{astro1.uid}").json()["photo_url"] is None

    def test_profile_save_regression(self, astro1):
        p = astro1.get(f"{BASE_URL}/api/astrologer/profile").json()["profile"]
        body = {k: p.get(k) for k in ("display_name", "bio", "languages", "expertise", "experience_years", "credential_summary", "rates", "modes_enabled", "payout_account")}
        body["credential_summary"] = body["credential_summary"] or ""
        r = astro1.put(f"{BASE_URL}/api/astrologer/profile", json=body)
        assert r.status_code == 200, r.text
