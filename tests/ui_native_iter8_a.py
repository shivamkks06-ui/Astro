# Iteration 8: native-feel UI - bottom nav, sheets, profile stats, login sheet (logged-out flows)
import asyncio, os
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
SHOTS = "/app/.screenshots"
os.makedirs(SHOTS, exist_ok=True)
R = []


def rec(name, ok, info=""):
    R.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""))


async def overflow(page):
    return await page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=[x for x in __import__("glob").glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")][0])
        # ---- bottom nav visibility, mobile
        for vw, vh in [(390, 844), (360, 800)]:
            ctx = await b.new_context(viewport={"width": vw, "height": vh}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            for path, expect in [("/", True), ("/discover", True), (f"/astrologers/{AID}", False), ("/login", False), ("/register", False)]:
                await page.goto(BASE + path, wait_until="networkidle")
                vis = await page.locator('[data-testid="bottom-nav"]').is_visible()
                rec(f"{vw} bottom-nav on {path} visible={expect}", vis == expect, f"got {vis}")
            await page.goto(BASE + "/", wait_until="networkidle")
            labels = await page.locator('[data-testid="bottom-nav"] a').all_inner_texts()
            rec(f"{vw} nav labels logged out", [l.strip() for l in labels] == ["Home", "Discover", "Log in"], str(labels))
            # spacer: footer bottom not under nav when scrolled to end
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(300)
            fb = await page.evaluate("""() => { const f = document.querySelector('footer'); const n = document.querySelector('[data-testid=bottom-nav]');
                return f && n ? [f.getBoundingClientRect().bottom, n.getBoundingClientRect().top] : null }""")
            rec(f"{vw} footer not covered by bottom-nav", fb and fb[0] <= fb[1] + 1, str(fb))
            # active tab doesn't stack history
            await page.goto(BASE + "/discover", wait_until="networkidle")
            h0 = await page.evaluate("history.length")
            await page.click('[data-testid="bottom-nav-discover"]')
            await page.click('[data-testid="bottom-nav-discover"]')
            await page.wait_for_timeout(300)
            h1 = await page.evaluate("history.length")
            rec(f"{vw} tapping active tab doesn't stack history", h0 == h1, f"{h0}->{h1}")
            await page.click('[data-testid="bottom-nav-home"]')
            await page.wait_for_url(BASE + "/")
            rec(f"{vw} tap Home navigates", True)
            rec(f"{vw} no page errors", not errs, str(errs[:2]))
            await ctx.close()
        # desktop hidden
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="networkidle")
        rec("desktop bottom-nav hidden", not await page.locator('[data-testid="bottom-nav"]').is_visible())
        await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
        rec("desktop mobile-book-bar hidden", not await page.locator('[data-testid="mobile-book-bar-button"]').is_visible())
        await page.click('[data-testid="book-now-button"]')
        sheet = page.locator('[data-testid="login-sheet"]')
        await sheet.wait_for(timeout=5000)
        bb = await sheet.bounding_box()
        rec("desktop login sheet centred", abs((bb["x"] + bb["width"] / 2) - 960) < 5 and abs((bb["y"] + bb["height"] / 2) - 540) < 10, str(bb))
        await page.screenshot(path=f"{SHOTS}/i8_desktop_sheet.jpg", quality=40, type="jpeg")
        await ctx.close()

        # ---- profile, logged out, 390
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await page.goto(BASE + "/", wait_until="networkidle")
        await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
        for t in ["stat-experience", "stat-rating", "stat-next-slot", "stat-price"]:
            txt = await page.locator(f'[data-testid="{t}"]').inner_text()
            print(f"  {t}: {txt!r}")
        rec("stat-experience 18 years", "18 years" in await page.locator('[data-testid="stat-experience"]').inner_text())
        rec("stat-rating No reviews yet", "No reviews yet" in await page.locator('[data-testid="stat-rating"]').inner_text())
        rec("stat-price min rate 25", "25" in await page.locator('[data-testid="stat-price"]').inner_text())
        rec("stat-next-slot not None", "None open" not in await page.locator('[data-testid="stat-next-slot"]').inner_text())
        await page.screenshot(path=f"{SHOTS}/i8_profile_390.jpg", quality=40, type="jpeg")
        for k in ["reviews", "book", "about"]:
            await page.click(f'[data-testid="profile-tab-{k}"]')
            await page.wait_for_timeout(900)
            top = await page.evaluate(f"document.getElementById('{k}').getBoundingClientRect().top")
            rec(f"profile-tab-{k} scrolls to section", -5 < top < 200, f"top={top}")
        # overlap: book-now button not covered by sticky bar when scrolled to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(300)
        geo = await page.evaluate("""() => { const b=document.querySelector('[data-testid=book-now-button]').getBoundingClientRect();
          const bar=document.querySelector('[data-testid=mobile-book-bar-button]').parentElement.getBoundingClientRect();
          const f=document.querySelector('footer').getBoundingClientRect(); return {btnBottom:b.bottom, barTop:bar.top, footBottom:f.bottom, footTop:f.top} }""")
        print("  geo at bottom:", geo)
        rec("profile footer not covered by sticky bar at bottom", geo["footBottom"] <= geo["barTop"] + 1, str(geo))
        await page.screenshot(path=f"{SHOTS}/i8_profile_390_bottom.jpg", quality=40, type="jpeg")
        await page.evaluate("window.scrollTo(0,0)")
        # mobile book bar opens login sheet
        h0 = await page.evaluate("history.length")
        await page.click('[data-testid="mobile-book-bar-button"]')
        sheet = page.locator('[data-testid="login-sheet"]')
        await sheet.wait_for(timeout=5000)
        await page.wait_for_timeout(400)
        rec("login-sheet opens; URL stays", f"/astrologers/{AID}" in page.url, page.url)
        bb = await sheet.bounding_box()
        rec("sheet anchored bottom full width", abs(bb["y"] + bb["height"] - 844) < 2 and bb["width"] >= 389, str(bb))
        st = await sheet.evaluate("e => { const s=getComputedStyle(e); return [s.borderTopLeftRadius, s.borderBottomLeftRadius, s.maxHeight, s.overflowY] }")
        rec("sheet rounded top, max-height 92dvh, scroll", st[0] != "0px" and st[1] == "0px" and st[3] == "auto" and abs(float(st[2].replace('px','')) - 844 * .92) < 2, str(st))
        cb = await page.locator('[data-testid="login-sheet"] [data-testid="dialog-close-button"]').bounding_box()
        rec("close button 44x44", cb["width"] >= 44 and cb["height"] >= 44, str(cb))
        ov = await page.evaluate("() => { const o=[...document.querySelectorAll('[data-state=open]')].find(e=>getComputedStyle(e).position==='fixed'&&e.getAttribute('role')!=='dialog'); return o?getComputedStyle(o).backgroundColor:null }")
        rec("overlay black/55", ov and "0.55" in ov, str(ov))
        await page.screenshot(path=f"{SHOTS}/i8_login_sheet_390.jpg", quality=40, type="jpeg")
        # validation
        await page.fill('[data-testid="login-sheet-email"]', "bad")
        await page.locator('[data-testid="login-sheet-email"]').blur()
        rec("email error on blur", await page.locator('[data-testid="login-sheet-email-error"]').is_visible())
        await page.fill('[data-testid="login-sheet-password"]', "short")
        await page.click('[data-testid="login-sheet-submit"]')
        rec("password error after submit", await page.locator('[data-testid="login-sheet-password-error"]').is_visible())
        # wrong password
        await page.fill('[data-testid="login-sheet-email"]', "demo.customer@nakshatraveda.test")
        await page.fill('[data-testid="login-sheet-password"]', "WrongPass@123")
        await page.click('[data-testid="login-sheet-submit"]')
        err = page.locator('[data-testid="login-sheet-error"]')
        try:
            await err.wait_for(timeout=6000)
            rec("wrong password shows server error", True, await err.inner_text())
        except Exception as e:
            rec("wrong password shows server error", False, str(e)[:100])
        # escape closes, route unchanged
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        rec("Escape closes sheet", await sheet.count() == 0 or not await sheet.is_visible())
        rec("Escape keeps route", f"/astrologers/{AID}" in page.url, page.url)
        h1 = await page.evaluate("history.length")
        rec("sheet adds no history entry", h0 == h1, f"{h0}->{h1}")
        # mode-chat opens sheet
        await page.click('[data-testid="mode-chat"]')
        await sheet.wait_for(timeout=5000)
        rec("mode-chat logged out opens login-sheet", True)
        # closeTopOverlay path (Android back handler)
        r = await page.evaluate("""() => { const sel='[role="dialog"][data-state="open"]'; if(!document.querySelector(sel)) return 'none';
            (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true,cancelable:true})); return 'sent' }""")
        await page.wait_for_timeout(500)
        rec("Back-handler Escape dispatch closes sheet", r == "sent" and (await sheet.count() == 0), r)
        # correct login
        await page.click('[data-testid="mobile-book-bar-button"]')
        await sheet.wait_for(timeout=5000)
        await page.fill('[data-testid="login-sheet-email"]', "demo.customer@nakshatraveda.test")
        await page.fill('[data-testid="login-sheet-password"]', "DemoPass@123")
        await page.click('[data-testid="login-sheet-submit"]')
        await page.wait_for_timeout(2500)
        rec("login closes sheet", await sheet.count() == 0)
        rec("stays on profile after login", f"/astrologers/{AID}" in page.url, page.url)
        bt = await page.locator('[data-testid="mobile-book-bar-button"]').inner_text()
        rec("bar button becomes Choose slot", bt.strip() == "Choose slot", bt)
        await ctx.close()
        await b.close()
    print(f"\nTOTAL {sum(1 for _, o in R if o)}/{len(R)} passed")
    print("FAILED:", [n for n, o in R if not o])

asyncio.run(main())
