# Iteration 6: logout landing from protected routes + 44px touch targets + overflow/tab regression
import asyncio, requests
from playwright.async_api import async_playwright

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
ASTRO = ("demo.astro1@nakshatraveda.test", "DemoPass@123")
FAILS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


async def login(page, cred):
    await page.goto(f"{BASE}/login")
    await page.fill('[data-testid="login-email-input"]', cred[0])
    await page.fill('[data-testid="login-password-input"]', cred[1])
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def heights(page, sel):
    return await page.evaluate("""(s) => Array.from(document.querySelectorAll(s)).filter(e=>e.getBoundingClientRect().height>0)
      .map(e => [e.getAttribute('data-testid') || e.textContent.trim().slice(0,20), Math.round(e.getBoundingClientRect().height), Math.round(e.getBoundingClientRect().width)])""", sel)


async def logout_test(b, w, cred, start):
    ctx = await b.new_context(viewport={"width": w, "height": 844 if w < 768 else 800})
    page = await ctx.new_page()
    await login(page, cred)
    await page.goto(BASE + start)
    await page.wait_for_timeout(1500)
    if w < 768:
        await page.click('[data-testid="mobile-menu-button"]')
        await page.wait_for_timeout(500)
        await page.click('[role=dialog] [data-testid="logout-button"]')
    else:
        await page.click('[data-testid="logout-button"]')
    await page.wait_for_timeout(2500)
    url = page.url.replace(BASE, "")
    me = await page.evaluate("fetch('/api/auth/me',{credentials:'include'}).then(r=>r.status)")
    check(url in ("/", ""), f"logout {w} {start} -> {url}")
    check(me == 401, f"logout {w} {start} /auth/me={me}")
    await ctx.close()


OVERFLOW_JS = "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"


async def tab_switch(page, prefix):
    tabs = await page.evaluate(f"""() => Array.from(document.querySelectorAll('[data-testid^="{prefix}"][role=tab]')).map(e=>e.getAttribute('data-testid'))""")
    ok = True
    for t in tabs[:7]:
        await page.click(f'[data-testid="{t}"]')
        await page.wait_for_timeout(400)
        st = await page.get_attribute(f'[data-testid="{t}"]', "data-state")
        panel = await page.evaluate("() => { const p=document.querySelector('[role=tabpanel][data-state=active]'); return p ? p.textContent.length : 0 }")
        if st != "active" or panel == 0:
            ok = False
            print("  tab fail", t, st, panel)
    return tabs, ok


async def main():
    aid = requests.get(f"{BASE}/api/astrologers").json()["items"][0]["id"]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # 1. logout
        for w in (1920, 390):
            await logout_test(b, w, CUST, "/account")
            await logout_test(b, w, ASTRO, "/studio")

        # 2+3. touch targets / overflow / tabs
        for w in (390, 1920):
            mob = w < 768
            ctx = await b.new_context(viewport={"width": w, "height": 844 if mob else 800})
            page = await ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            for path in ["/", "/discover", f"/astrologers/{aid}", "/legal/terms"]:
                await page.goto(BASE + path)
                await page.wait_for_timeout(1800)
                sw, vw = await page.evaluate(OVERFLOW_JS)
                check(sw <= vw, f"{w} {path} overflow sw={sw} vw={vw}")
                if mob and path == "/":
                    h = await heights(page, '[data-testid="brand-logo"]')
                    check(all(x[1] >= 44 for x in h), f"brand-logo {h}")
                    await page.click('[data-testid="mobile-menu-button"]')
                    await page.wait_for_timeout(500)
                    h = await heights(page, '[role=dialog] button:has(> .sr-only)')
                    check(h and all(x[1] >= 44 and x[2] >= 44 for x in h), f"sheet close {h}")
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(300)
                if mob and path.startswith("/astrologers"):
                    h = await heights(page, '[data-testid^="slot-"]')
                    check(h and all(x[1] >= 44 for x in h), f"slot chips n={len(h)} min={min([x[1] for x in h] or [0])}")
                if mob and path.startswith("/legal"):
                    h = await heights(page, 'main a[href^="/legal/"], a[href^="/legal/"]:not(footer a)')
                    h = [x for x in h]
                    check(h and all(x[1] >= 44 for x in h), f"legal links {h}")
            await login(page, CUST)
            await page.goto(BASE + "/account")
            await page.wait_for_timeout(1800)
            sw, vw = await page.evaluate(OVERFLOW_JS)
            check(sw <= vw, f"{w} /account overflow sw={sw} vw={vw}")
            if mob:
                h = await heights(page, '[data-testid^="tab-"][role=tab]')
                check(h and all(x[1] >= 44 for x in h), f"account tabs {h}")
                await page.click('[data-testid="mobile-menu-button"]')
                await page.wait_for_timeout(500)
                h = await heights(page, '[role=dialog] [data-testid="logout-button"]')
                check(h and all(x[1] >= 44 for x in h), f"sheet logout {h}")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
            tabs, ok = await tab_switch(page, "tab-")
            check(ok and tabs, f"{w} account tabs switch {tabs}")
            await ctx.close()

            ctx = await b.new_context(viewport={"width": w, "height": 844 if mob else 800})
            page = await ctx.new_page()
            await login(page, ASTRO)
            await page.goto(BASE + "/studio")
            await page.wait_for_timeout(2000)
            sw, vw = await page.evaluate(OVERFLOW_JS)
            check(sw <= vw, f"{w} /studio overflow sw={sw} vw={vw}")
            if mob:
                h = await heights(page, '[data-testid^="studio-tab-"]')
                check(h and all(x[1] >= 44 for x in h), f"studio tabs {h}")
            tabs, ok = await tab_switch(page, "studio-tab-")
            check(ok and tabs, f"{w} studio tabs switch {tabs}")
            if mob:
                # find profile tab with chips
                for t in tabs:
                    await page.click(f'[data-testid="{t}"]')
                    await page.wait_for_timeout(500)
                    if await page.locator('[data-testid^="astro-lang-"]').count():
                        break
                for pre in ("astro-lang-", "astro-exp-"):
                    h = await heights(page, f'[data-testid^="{pre}"]')
                    check(h and all(x[1] >= 44 for x in h), f"{pre} n={len(h)} min={min([x[1] for x in h] or [0])}")
                await page.screenshot(path="/app/tests/shots/iter6_studio_390.jpg", quality=40, type="jpeg")
            if errs:
                print("PAGE ERRORS", errs[:3])
            await ctx.close()
        await b.close()
    print("FAILS:", FAILS)

asyncio.run(main())
