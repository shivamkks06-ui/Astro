# Iteration 5: register/logout regression, studio tabs, card availability
import asyncio, requests, uuid
from playwright.async_api import async_playwright

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()


async def main():
    items = requests.get(f"{BASE}/api/astrologers").json()["items"]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 360, "height": 844})
        page = await ctx.new_page()
        await page.goto(f"{BASE}/discover")
        await page.wait_for_timeout(2500)
        for a in items:
            t = await page.inner_text(f'[data-testid="astrologer-card-availability-{a["id"]}"]')
            card = await page.inner_text(f'[data-testid="astrologer-card-{a["id"]}"]')
            print("card", a["display_name"], "|", t, "| next_slot_at", a["next_slot_at"], "| CTA", "View profile & book" in card, "| rating", "New" in card or str(a.get("rating_avg")) in card)
        # register customer
        email = f"test_{uuid.uuid4().hex[:8]}@testmail.in"
        await page.goto(f"{BASE}/register")
        await page.wait_for_timeout(1200)
        await page.fill('[data-testid="register-name-input"]', "TEST Mobile")
        await page.fill('[data-testid="register-email-input"]', email)
        await page.fill('[data-testid="register-password-input"]', "TestPass@123")
        await page.click('[data-testid="register-accept-terms"]')
        await page.click('[data-testid="register-submit-button"]')
        await page.wait_for_timeout(2500)
        print("register ->", page.url.replace(BASE, ""))
        await page.click('[data-testid="mobile-menu-button"]')
        await page.wait_for_timeout(500)
        await page.click('[role=dialog] [data-testid="logout-button"]')
        await page.wait_for_timeout(1500)
        print("logout ->", page.url.replace(BASE, ""), "me:", (await page.evaluate("fetch('/api/auth/me',{credentials:'include'}).then(r=>r.status)")))
        # studio tabs
        await page.goto(f"{BASE}/login")
        await page.fill('[data-testid="login-email-input"]', "demo.astro1@nakshatraveda.test")
        await page.fill('[data-testid="login-password-input"]', "DemoPass@123")
        await page.click('[data-testid="login-submit-button"]')
        await page.wait_for_timeout(2500)
        print("astro login ->", page.url.replace(BASE, ""))
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        for t in ["profile", "verification", "listing", "slots", "bookings", "earnings", "privacy"]:
            await page.click(f'[data-testid="studio-tab-{t}"]')
            await page.wait_for_timeout(900)
            sw = await page.evaluate("document.documentElement.scrollWidth")
            st = await page.get_attribute(f'[data-testid="studio-tab-{t}"]', "data-state")
            print("tab", t, st, "sw", sw)
            if t in ("slots", "earnings"):
                await page.screenshot(path=f"/app/tests/shots/studio_{t}_360.jpg", quality=40, type="jpeg")
        print("errors", errs)
        await b.close()

asyncio.run(main())
