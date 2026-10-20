# Iteration 8: skeletons, error/retry, overflow across widths, landscape, register via login sheet ?next, role tabs, studio/admin regression
import asyncio, glob, time, requests
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
SHOTS = "/app/.screenshots"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]
R = []


def rec(name, ok, info=""):
    R.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""))


async def login_ui(page, email, pw):
    await page.goto(BASE + "/login", wait_until="networkidle")
    await page.fill('[data-testid="login-email-input"]', email)
    await page.fill('[data-testid="login-password-input"]', pw)
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()

        # ---- skeletons via delayed /api/astrologers
        async def slow(route):
            await asyncio.sleep(2.5)
            await route.continue_()
        await page.route("**/api/astrologers**", slow)
        for path, sk in [("/", "cards-skeleton"), ("/discover", "cards-skeleton"), (f"/astrologers/{AID}", "profile-skeleton")]:
            await page.goto(BASE + path, wait_until="domcontentloaded")
            try:
                await page.locator(f'[data-testid="{sk}"]').wait_for(timeout=4000)
                rec(f"{sk} on {path}", True)
                if path == "/":
                    await page.screenshot(path=f"{SHOTS}/i8_skeleton_home.jpg", quality=40, type="jpeg")
            except Exception as e:
                rec(f"{sk} on {path}", False, str(e)[:80])
            await page.wait_for_timeout(2800)
        await page.unroute("**/api/astrologers**")

        # ---- error + retry
        state = {"block": True}
        async def blocker(route):
            if state["block"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/api/astrologers**", blocker)
        for path, ok_sel in [("/discover", '[data-testid="results-count"]'), (f"/astrologers/{AID}", '[data-testid="astrologer-name"]'), ("/", '[data-testid="landing-view-all"]')]:
            state["block"] = True
            await page.goto(BASE + path, wait_until="domcontentloaded")
            try:
                await page.locator('[data-testid="error-state"]').first.wait_for(timeout=12000)
                rec(f"error-state on {path}", True)
                state["block"] = False
                await page.locator('[data-testid="retry-button"]').first.click()
                await page.locator(ok_sel).first.wait_for(timeout=8000)
                rec(f"retry recovers on {path}", await page.locator('[data-testid="error-state"]').count() == 0)
            except Exception as e:
                rec(f"error/retry on {path}", False, str(e)[:100])
        await page.unroute("**/api/astrologers**")

        # ---- press feedback classes
        cls = await page.locator('[data-testid="landing-view-all"]').first.get_attribute("class") if await page.locator('[data-testid="landing-view-all"]').count() else ""
        await page.goto(BASE + "/", wait_until="networkidle")
        btn_cls = await page.locator("button").evaluate_all("els => els.filter(e=>e.className.includes('active:scale')).length + '/' + els.length")
        print("  buttons with active:scale on /:", btn_cls)
        await ctx.close()

        # ---- overflow across widths (logged out pages + /account logged in)
        for w in [320, 360, 390, 412]:
            ctx = await b.new_context(viewport={"width": w, "height": 800}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            for path in ["/", "/discover", f"/astrologers/{AID}"]:
                await page.goto(BASE + path, wait_until="networkidle")
                sw = await page.evaluate("document.documentElement.scrollWidth")
                rec(f"no h-overflow {w} {path}", sw <= w, f"sw={sw}")
            await login_ui(page, "demo.customer@nakshatraveda.test", "DemoPass@123")
            sw = await page.evaluate("document.documentElement.scrollWidth")
            rec(f"no h-overflow {w} /account", sw <= w and "/account" in page.url, f"sw={sw} {page.url}")
            if w == 320:
                await page.screenshot(path=f"{SHOTS}/i8_account_320.jpg", quality=40, type="jpeg")
                rec("bottom nav on /account", await page.locator('[data-testid="bottom-nav"]').is_visible())
            await ctx.close()

        # ---- landscape 844x390
        ctx = await b.new_context(viewport={"width": 844, "height": 390}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await page.goto(BASE + "/discover", wait_until="networkidle")
        sw = await page.evaluate("document.documentElement.scrollWidth")
        rec("landscape discover no overflow; bottom-nav hidden (>=768)", sw <= 844 and not await page.locator('[data-testid="bottom-nav"]').is_visible(), f"sw={sw}")
        await page.screenshot(path=f"{SHOTS}/i8_landscape_discover.jpg", quality=40, type="jpeg")
        await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
        await page.locator('[data-testid="book-now-button"]').scroll_into_view_if_needed()
        await page.wait_for_timeout(400)
        g = await page.evaluate("""() => { const b=document.querySelector('[data-testid=book-now-button]').getBoundingClientRect();
          const bar=document.querySelector('[data-testid=mobile-book-bar-button]').parentElement.getBoundingClientRect(); return {bTop:b.top,bBottom:b.bottom,barTop:bar.top,barH:bar.height} }""")
        rec("landscape profile: book-now not under sticky bar", g["bBottom"] <= g["barTop"], str(g))
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{SHOTS}/i8_landscape_profile_bottom.jpg", quality=40, type="jpeg")
        # login sheet in landscape (>=640 -> centred dialog); fits?
        await page.evaluate("window.scrollTo(0,0)")
        await page.click('[data-testid="mobile-book-bar-button"]')
        sh = page.locator('[data-testid="login-sheet"]')
        await sh.wait_for(timeout=5000)
        await page.wait_for_timeout(400)
        bb = await sh.bounding_box()
        rec("landscape login dialog fits viewport height", bb["y"] >= 0 and bb["y"] + bb["height"] <= 390, str(bb))
        await page.screenshot(path=f"{SHOTS}/i8_landscape_login.jpg", quality=40, type="jpeg")
        await ctx.close()

        # ---- register from login sheet keeps ?next
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
        await page.click('[data-testid="mobile-book-bar-button"]')
        await page.locator('[data-testid="login-sheet"]').wait_for(timeout=5000)
        await page.click('[data-testid="login-sheet-register"]')
        await page.wait_for_url("**/register**", timeout=5000)
        rec("register link keeps ?next", f"next=%2Fastrologers%2F{AID}" in page.url, page.url)
        email = f"TEST_iter8_{int(time.time())}@example.com"
        await page.fill('[data-testid="register-name-input"]', "TEST Iter8 User")
        await page.fill('[data-testid="register-email-input"]', email)
        await page.fill('[data-testid="register-password-input"]', "TestPass@123")
        await page.click('[data-testid="register-accept-terms"]')
        await page.click('[data-testid="register-submit-button"]')
        await page.wait_for_timeout(3000)
        rec("register as customer returns to profile", f"/astrologers/{AID}" in page.url, page.url)
        bt = await page.locator('[data-testid="mobile-book-bar-button"]').inner_text() if await page.locator('[data-testid="mobile-book-bar-button"]').count() else ""
        rec("after register bar says Choose slot", bt.strip() == "Choose slot", bt)
        await page.go_back()
        await page.wait_for_timeout(1200)
        print("  back after register ->", page.url)
        await ctx.close()

        # ---- studio + admin tabs regression (mobile)
        for email, pw, path, label, tabsel in [("demo.astro1@nakshatraveda.test", "DemoPass@123", "/studio", "Studio", "studio-tab-"),
                                                ("shivamkks9088@outlook.com", "Nakshatra@Admin2026", "/admin", "Admin", "admin-tab-")]:
            ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            await login_ui(page, email, pw)
            rec(f"{label} login lands {path}", path in page.url, page.url)
            labels = [l.strip() for l in await page.locator('[data-testid="bottom-nav"] a').all_inner_texts()]
            rec(f"{label} bottom nav", labels == ["Home", "Discover", label], str(labels))
            tabs = page.locator(f'[data-testid^="{tabsel}"]')
            n = await tabs.count()
            okc = 0
            for i in range(n):
                try:
                    await tabs.nth(i).click(timeout=3000)
                    await page.wait_for_timeout(500)
                    okc += 1
                except Exception as e:
                    print("  tab click fail", await tabs.nth(i).get_attribute("data-testid"), str(e)[:80])
            rec(f"{label} tabs clickable", n > 0 and okc == n, f"{okc}/{n}")
            sw = await page.evaluate("document.documentElement.scrollWidth")
            rec(f"{label} no overflow at 390", sw <= 390, f"sw={sw}")
            await page.screenshot(path=f"{SHOTS}/i8_{label.lower()}_390.jpg", quality=40, type="jpeg")
            rec(f"{label} no page errors", not errs, str(errs[:2]))
            await ctx.close()
        await b.close()
    print(f"\nTOTAL {sum(1 for _, o in R if o)}/{len(R)} passed")
    print("FAILED:", [n for n, o in R if not o])

asyncio.run(main())
