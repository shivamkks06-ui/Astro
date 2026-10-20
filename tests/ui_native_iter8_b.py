# Iteration 8: logged-in customer booking flow from profile (mobile sheet + desktop), back nav, mock pay, chat, cancel
import asyncio, glob, os, requests
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
SHOTS = "/app/.screenshots"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]
R = []
CREATED = []


def rec(name, ok, info=""):
    R.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""))


async def login_ui(page, email, pw):
    await page.goto(BASE + "/login", wait_until="networkidle")
    await page.fill('[data-testid="login-email-input"]', email)
    await page.fill('[data-testid="login-password-input"]', pw)
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def book(page, mobile, tag):
    await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
    btn = '[data-testid="mobile-book-bar-button"]' if mobile else '[data-testid="book-now-button"]'
    # no slot -> toast + scroll
    await page.evaluate("window.scrollTo(0,0)")
    await page.click(btn)
    await page.wait_for_timeout(1200)
    toast = await page.locator("text=Choose a time slot first").count()
    top = await page.evaluate("document.getElementById('slots').getBoundingClientRect().top")
    rec(f"{tag} no-slot: toast shown", toast > 0)
    rec(f"{tag} no-slot: scrolled to slots", top < 400, f"top={top}")
    first = page.locator('[data-testid^="slot-"]').first
    await first.click()
    summ = await page.locator('[data-testid="selected-slot-summary"]').inner_text()
    rec(f"{tag} selected-slot-summary shows total", "total" in summ and "750" in summ, summ)
    if mobile:
        rec(f"{tag} bar button says Book", (await page.locator(btn).inner_text()).strip() == "Book")
    await page.click(btn)
    dlg = page.locator('[data-testid="booking-dialog"]')
    await dlg.wait_for(timeout=5000)
    await page.wait_for_timeout(400)
    bb = await dlg.bounding_box()
    vp = page.viewport_size
    if mobile:
        rec(f"{tag} booking-dialog is bottom sheet", abs(bb["y"] + bb["height"] - vp["height"]) < 2 and bb["width"] >= vp["width"] - 1, str(bb))
        sh = await dlg.evaluate("e=>[e.scrollHeight,e.clientHeight,getComputedStyle(e).overflowY]")
        rec(f"{tag} booking sheet internal scroll", sh[2] == "auto" and bb["height"] <= vp["height"] * 0.92 + 1, str(sh))
    else:
        rec(f"{tag} booking-dialog centred", abs(bb["x"] + bb["width"] / 2 - vp["width"] / 2) < 5, str(bb))
    await page.screenshot(path=f"{SHOTS}/i8_booking_dialog_{tag}.jpg", quality=40, type="jpeg")
    rec(f"{tag} total in dialog", "750" in await page.locator('[data-testid="booking-total"]').inner_text())
    await page.click('[data-testid="booking-accept-terms"]')
    sub = page.locator('[data-testid="booking-submit"]')
    await sub.scroll_into_view_if_needed()
    await sub.click()
    await page.wait_for_url("**/bookings/**", timeout=8000)
    bid = page.url.rstrip("/").split("/")[-1]
    CREATED.append(bid)
    rec(f"{tag} navigated to /bookings/id", True, bid)
    await page.wait_for_timeout(1000)
    await page.go_back()
    await page.wait_for_timeout(1500)
    rec(f"{tag} one back returns to profile", f"/astrologers/{AID}" in page.url, page.url)
    return bid


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        # mobile
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        await login_ui(page, "demo.customer@nakshatraveda.test", "DemoPass@123")
        rec("customer header login lands /account", "/account" in page.url, page.url)
        labels = [l.strip() for l in await page.locator('[data-testid="bottom-nav"] a').all_inner_texts()]
        rec("customer bottom nav Bookings", labels == ["Home", "Discover", "Bookings"], str(labels))
        bid_m = await book(page, True, "mobile")

        # astrologer accepts via API, customer pays via mock UI, chat
        s = requests.Session()
        r = s.post(BASE + "/api/auth/login", json={"email": "demo.astro1@nakshatraveda.test", "password": "DemoPass@123"})
        tok = r.json().get("access_token")
        r = s.post(BASE + f"/api/bookings/{bid_m}/actions/accept", json={"reason": ""}, headers={"Authorization": f"Bearer {tok}"})
        rec("astrologer accept (API)", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
        await page.goto(BASE + f"/bookings/{bid_m}", wait_until="networkidle")
        try:
            await page.click('[data-testid="action-pay"]', timeout=6000)
            await page.wait_for_url("**/pay/**", timeout=8000)
            rec("pay -> /pay page; bottom nav hidden", not await page.locator('[data-testid="bottom-nav"]').is_visible())
            await page.click('[data-testid="mock-pay-success"]', timeout=6000)
            await page.wait_for_timeout(4000)
            print("  after pay url:", page.url)
            if "/pay/" in page.url:
                ok = await page.locator('[data-testid="payment-verified"]').count()
                rec("mock payment verified", ok > 0)
                await page.goto(BASE + f"/bookings/{bid_m}", wait_until="networkidle")
            st = await page.locator('[data-testid="booking-status"]').inner_text()
            rec("booking confirmed after mock pay", "onfirmed" in st, st)
        except Exception as e:
            rec("mock payment flow", False, str(e)[:150])
        if await page.locator('[data-testid="chat-input"]').count():
            await page.fill('[data-testid="chat-input"]', "TEST_ hello from iter8")
            await page.click('[data-testid="chat-send-button"]')
            await page.wait_for_timeout(2000)
            rec("chat send", await page.locator('[data-testid="chat-messages"] >> text=TEST_ hello from iter8').count() > 0)
        else:
            print("  chat-input not present on confirmed booking (may need in_progress)")
        await page.screenshot(path=f"{SHOTS}/i8_booking_page_mobile.jpg", quality=40, type="jpeg")
        # cancel via UI (dialog sheet)
        try:
            await page.click('[data-testid="action-cancel"]', timeout=5000)
            await page.locator('[data-testid="action-cancel-dialog"]').wait_for(timeout=4000)
            await page.click('[data-testid="action-cancel-confirm"]')
            await page.wait_for_timeout(2500)
            st = await page.locator('[data-testid="booking-status"]').inner_text()
            rec("cancel via UI", "ancel" in st, st)
        except Exception as e:
            rec("cancel via UI", False, str(e)[:150])
        rec("mobile no page errors", not errs, str(errs[:2]))
        await ctx.close()

        # desktop
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await login_ui(page, "demo.customer@nakshatraveda.test", "DemoPass@123")
        bid_d = await book(page, False, "desktop")
        # logout
        try:
            await page.click('[data-testid="logout-button"]', timeout=4000)
            await page.wait_for_timeout(1500)
            rec("logout shows nav-login", await page.locator('[data-testid="nav-login"]').is_visible())
        except Exception as e:
            rec("logout", False, str(e)[:120])
        await ctx.close()
        await b.close()

    # cleanup: cancel created bookings as customer via API
    s = requests.Session()
    s.post(BASE + "/api/auth/login", json={"email": "demo.customer@nakshatraveda.test", "password": "DemoPass@123"})
    for bid in CREATED:
        r = s.post(BASE + f"/api/bookings/{bid}/actions/cancel", json={"reason": "TEST cleanup"})
        print("cleanup cancel", bid, r.status_code)
    print(f"\nTOTAL {sum(1 for _, o in R if o)}/{len(R)} passed")
    print("FAILED:", [n for n, o in R if not o])

asyncio.run(main())
