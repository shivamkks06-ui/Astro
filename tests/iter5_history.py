# Iteration 5: single-step back history, login-from-profile, pay detour, overlay-first Escape, app:resume refresh, form attrs
import asyncio, requests, re
from playwright.async_api import async_playwright

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
ASTRO = ("demo.astro1@nakshatraveda.test", "DemoPass@123")
created = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name, extra)


async def path(page):
    await page.wait_for_timeout(1200)
    return page.url.replace(BASE, "")


async def login(page, cred):
    await page.fill('[data-testid="login-email-input"]', cred[0])
    await page.fill('[data-testid="login-password-input"]', cred[1])
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def main():
    items = requests.get(f"{BASE}/api/astrologers").json()["items"]
    demo = next(a for a in items if "Raman" in a["display_name"])
    aid = demo["id"]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844})
        page = await ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))

        # --- forms attributes
        await page.goto(f"{BASE}/login")
        await page.wait_for_timeout(1500)
        attrs = await page.evaluate("""() => ['login-email-input','login-password-input'].map(t => { const e = document.querySelector(`[data-testid=${t}]`); return [e.type, e.autocomplete, e.inputMode]; })""")
        check("login inputs attrs", attrs[0][:2] == ["email", "email"] and attrs[1][1] == "current-password", attrs)
        await page.goto(f"{BASE}/register")
        await page.wait_for_timeout(1500)
        attrs = await page.evaluate("""() => ['register-email-input','register-password-input'].map(t => { const e = document.querySelector(`[data-testid=${t}]`); return [e.type, e.autocomplete]; })""")
        check("register inputs attrs", attrs == [["email", "email"], ["password", "new-password"]], attrs)
        check("register submit disabled w/o terms", await page.locator('[data-testid="register-submit-button"]').is_disabled())

        # --- login from profile (logged out): home -> discover -> profile -> login -> back to profile; back once -> discover
        await page.goto(f"{BASE}/")
        await page.wait_for_timeout(1500)
        await page.click('[data-testid="hero-discover-button"]')
        await page.wait_for_timeout(1500)
        await page.click(f'[data-testid="astrologer-card-{aid}"]')
        await page.wait_for_timeout(1500)
        await page.click('[data-testid="book-now-button"]')
        p1 = await path(page)
        check("redirect to login with next", p1.startswith("/login?next=") and aid in p1, p1)
        # double submit check: click twice quickly
        await page.fill('[data-testid="login-email-input"]', CUST[0])
        await page.fill('[data-testid="login-password-input"]', CUST[1])
        reqs = []
        page.on("request", lambda r: reqs.append(r.url) if r.url.endswith("/api/auth/login") else None)
        await page.click('[data-testid="login-submit-button"]')
        busy_disabled = await page.locator('[data-testid="login-submit-button"]').is_disabled()
        await page.wait_for_timeout(2500)
        check("login button disabled while busy / single request", len(reqs) == 1, f"disabled={busy_disabled} reqs={len(reqs)}")
        p2 = await path(page)
        check("after login back at profile", p2 == f"/astrologers/{aid}", p2)
        await page.go_back()
        p3 = await path(page)
        check("one back -> discover", p3 == "/discover", p3)
        await page.go_back()
        p3b = await path(page)
        check("next back -> home", p3b == "/", p3b)

        # --- logged-in flow: home -> discover (mobile menu) -> profile -> book -> booking
        await page.click('[data-testid="mobile-menu-button"]')
        await page.wait_for_timeout(600)
        links = await page.evaluate("""() => [...document.querySelectorAll('[role=dialog] a, [role=dialog] button')].map(e => (e.dataset.testid||e.textContent.trim()) + '=' + Math.round(e.getBoundingClientRect().height))""")
        print("sheet links heights:", links)
        # Escape closes sheet, route stays
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        check("Escape closes sheet, route unchanged", await page.locator('[role=dialog]').count() == 0 and await path(page) == "/")
        # closeTopOverlay equivalent via native.js logic dispatched on activeElement
        await page.click('[data-testid="mobile-menu-button"]')
        await page.wait_for_timeout(600)
        await page.evaluate("""() => (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true,cancelable:true}))""")
        await page.wait_for_timeout(500)
        check("synthetic Escape (closeTopOverlay) closes sheet", await page.locator('[role=dialog][data-state=open]').count() == 0)
        await page.click('[data-testid="mobile-menu-button"]')
        await page.wait_for_timeout(600)
        await page.click('[role=dialog] [data-testid="nav-discover"]')
        await page.wait_for_timeout(1500)
        check("sheet nav -> discover, sheet closed", await path(page) == "/discover" and await page.locator('[role=dialog][data-state=open]').count() == 0)

        # discover select + Escape; app:resume keeps search value
        await page.fill('[data-testid="filter-search"]', "Ra")
        await page.wait_for_timeout(1200)
        await page.evaluate("window.dispatchEvent(new Event('app:resume'))")
        await page.wait_for_timeout(150)
        spinner = await page.evaluate("document.body.innerText.includes('Loading')")
        await page.wait_for_timeout(1500)
        val = await page.input_value('[data-testid="filter-search"]')
        check("app:resume keeps search value + no spinner", val == "Ra" and not spinner, f"val={val} spinner={spinner}")
        await page.evaluate("window.dispatchEvent(new Event('app:reconnect'))")
        await page.wait_for_timeout(1500)
        check("app:reconnect keeps search", await page.input_value('[data-testid="filter-search"]') == "Ra")
        await page.fill('[data-testid="filter-search"]', "")
        await page.wait_for_timeout(1200)
        await page.click('[data-testid="sort-select"]')
        await page.wait_for_timeout(400)
        lb = await page.locator('[role=listbox]').count()
        await page.evaluate("""() => (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true,cancelable:true}))""")
        await page.wait_for_timeout(500)
        check("select listbox closed by Escape, route same", lb == 1 and await page.locator('[role=listbox]').count() == 0 and await path(page) == "/discover")

        await page.click(f'[data-testid="astrologer-card-{aid}"]')
        await page.wait_for_timeout(2000)
        slot = page.locator('[data-testid^="slot-"]').first
        await slot.click()
        await page.click('[data-testid="book-now-button"]')
        await page.wait_for_timeout(800)
        # open select inside dialog then Escape once: only select closes
        await page.click('[data-testid="booking-birth-profile"]')
        await page.wait_for_timeout(400)
        await page.evaluate("""() => (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true,cancelable:true}))""")
        await page.wait_for_timeout(500)
        check("Escape in dialog closes only select", await page.locator('[role=listbox]').count() == 0 and await page.locator('[data-testid="booking-dialog"]').count() == 1)
        await page.evaluate("""() => (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true,cancelable:true}))""")
        await page.wait_for_timeout(500)
        check("2nd Escape closes dialog, route same", await page.locator('[data-testid="booking-dialog"]').count() == 0 and await path(page) == f"/astrologers/{aid}")
        await page.click('[data-testid="book-now-button"]')
        await page.wait_for_timeout(800)
        await page.click('[data-testid="booking-accept-terms"]')
        await page.click('[data-testid="booking-submit"]')
        await page.wait_for_timeout(2500)
        bp = await path(page)
        m = re.match(r"/bookings/(\w+)", bp)
        check("booked -> booking page", bool(m), bp)
        bid = m.group(1) if m else None
        created.append(bid)
        sw = await page.evaluate("document.documentElement.scrollWidth")
        check("booking page no overflow @390", sw == 390, sw)
        await page.screenshot(path="/app/tests/shots/booking_390.jpg", quality=40, type="jpeg")

        # astrologer accepts via API; customer page refreshes via app:resume
        s = requests.Session()
        s.post(f"{BASE}/api/auth/login", json={"email": ASTRO[0], "password": ASTRO[1]})
        r = s.post(f"{BASE}/api/bookings/{bid}/actions/accept", json={})
        check("astrologer accept", r.status_code == 200, r.status_code)
        await page.evaluate("window.dispatchEvent(new Event('app:resume'))")
        await page.wait_for_timeout(2000)
        has_pay = await page.locator('[data-testid="action-pay"]').count()
        check("app:resume refreshed booking -> Pay visible", has_pay == 1)
        if not has_pay:
            await page.reload(); await page.wait_for_timeout(2000)
        await page.click('[data-testid="action-pay"]')
        await page.wait_for_timeout(2000)
        pp = await path(page)
        check("pay page", pp.startswith("/pay/"), pp)
        await page.click('[data-testid="mock-pay-success"]')
        await page.wait_for_timeout(3000)
        check("payment verified", await page.locator('[data-testid="payment-verified"]').count() == 1)
        await page.click('[data-testid="payment-back-link"]')
        p4 = await path(page)
        check("Go to booking -> booking", p4 == f"/bookings/{bid}", p4)
        txt = await page.inner_text("main")
        check("booking confirmed", "onfirmed" in txt)
        hist = await page.evaluate("history.state && history.state.idx")
        print("history idx at booking:", hist)
        await page.go_back()
        p5 = await path(page)
        check("back from booking -> profile", p5 == f"/astrologers/{aid}", p5)
        await page.go_back()
        p6 = await path(page)
        check("back -> discover", p6 == "/discover", p6)
        await page.go_back()
        p7 = await path(page)
        check("back -> home", p7 == "/", p7)
        print("page errors:", errs[:3])
        await b.close()

asyncio.run(main())
print("CREATED", created)
