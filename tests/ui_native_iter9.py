# Iteration 9: retest of iter-8 fixes - profile spacer/footer, sm+ dialog scroll, register->back history, LoginSheet reset
import asyncio, glob, time, requests
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]
SHOTS = "/app/.screenshots"
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
R = []


def rec(name, ok, info=""):
    R.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""))


async def goto(page, path):
    await page.goto(BASE + path, wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=20000)


async def footer_check(page, tag):
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(500)
    info = await page.evaluate("""() => { const bar=document.querySelector('[data-testid=mobile-book-bar-button]').parentElement.getBoundingClientRect();
      const sp=document.querySelector('[data-testid=profile-bar-spacer]'); const f=document.querySelector('footer').getBoundingClientRect();
      const grid=f.previousElementSibling ? null : null;
      const main=document.querySelector('footer').previousElementSibling;
      let contentBottom=null; if(main){ const kids=[...main.querySelectorAll('*')].filter(e=>e.getBoundingClientRect().height>0); contentBottom=Math.max(...kids.map(e=>e.getBoundingClientRect().bottom)); }
      return {barTop: bar.top, spacer: sp ? sp.getBoundingClientRect().height : null, spacerVisible: sp ? getComputedStyle(sp).display!=='none' : false,
        footTop: f.top, footBottom: f.bottom, gap: contentBottom ? f.top - contentBottom : null} }""")
    rec(f"{tag} profile-bar-spacer present", info["spacer"] and info["spacerVisible"], str(info))
    rec(f"{tag} footer bottom above sticky bar", info["footBottom"] <= info["barTop"] + 1, str(info))
    rec(f"{tag} no big empty gap above footer (<60px)", info["gap"] is not None and info["gap"] < 60, f"gap={info['gap']}")
    for k in ["terms", "privacy", "guidelines", "refunds"]:
        loc = page.locator(f'[data-testid="footer-link-{k}"]')
        bb = await loc.bounding_box()
        # element at center must be the link itself (not covered)
        hit = await page.evaluate("""([x,y]) => { const e=document.elementFromPoint(x,y); return e ? (e.closest('[data-testid^=footer-link]')||{}).getAttribute?.('data-testid') : null }""", [bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2])
        rec(f"{tag} footer-link-{k} tappable (hit-test)", hit == f"footer-link-{k}" and bb["y"] + bb["height"] <= info["barTop"], f"hit={hit} bb={bb}")
    await page.screenshot(path=f"{SHOTS}/i9_profile_bottom_{tag}.jpg", quality=40, type="jpeg")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        # 1. footer/spacer at 390x844 and 844x390 + tap terms
        for vw, vh in [(390, 844), (844, 390)]:
            ctx = await b.new_context(viewport={"width": vw, "height": vh}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            await goto(page, f"/astrologers/{AID}")
            await footer_check(page, f"{vw}x{vh}")
            await page.locator('[data-testid="footer-link-terms"]').tap()
            await page.wait_for_timeout(1000)
            rec(f"{vw}x{vh} tap footer-link-terms navigates", "/legal/" in page.url, page.url)
            await ctx.close()
        # desktop spacer hidden
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await goto(page, f"/astrologers/{AID}")
        sp = await page.locator('[data-testid="profile-bar-spacer"]').is_visible()
        rec("desktop profile-bar-spacer hidden", not sp)
        await ctx.close()
        # bottom nav spacer 65px at 360x800
        ctx = await b.new_context(viewport={"width": 360, "height": 800}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await goto(page, "/")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(400)
        g = await page.evaluate("""() => { const n=document.querySelector('[data-testid=bottom-nav]'); const s=n.previousElementSibling; const f=document.querySelector('footer');
           return {spacer: s.getBoundingClientRect().height, nav: n.getBoundingClientRect().height, navTop: n.getBoundingClientRect().top, footBottom: f.getBoundingClientRect().bottom} }""")
        rec("360 bottom-nav spacer 65px", abs(g["spacer"] - 65) < 0.5, str(g))
        rec("360 footer not overlapped by nav", g["footBottom"] <= g["navTop"] + 0.5, str(g))
        await ctx.close()

        # 2. landscape login sheet: wrong pw -> scroll reaches title/error/register; reopen resets
        ctx = await b.new_context(viewport={"width": 844, "height": 390}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await goto(page, f"/astrologers/{AID}")
        await page.click('[data-testid="mobile-book-bar-button"]')
        sh = page.locator('[data-testid="login-sheet"]')
        await sh.wait_for()
        await page.wait_for_timeout(400)
        await page.fill('[data-testid="login-sheet-email"]', "bad")
        await page.locator('[data-testid="login-sheet-email"]').blur()
        await page.fill('[data-testid="login-sheet-email"]', CUST[0])
        await page.fill('[data-testid="login-sheet-password"]', "WrongPass@1")
        await page.click('[data-testid="login-sheet-submit"]')
        await page.locator('[data-testid="login-sheet-error"]').wait_for(timeout=8000)
        await page.wait_for_timeout(300)
        bb = await sh.bounding_box()
        st = await sh.evaluate("e=>[getComputedStyle(e).maxHeight,getComputedStyle(e).overflowY,e.scrollHeight,e.clientHeight]")
        rec("landscape sheet within viewport", bb["y"] >= 0 and bb["y"] + bb["height"] <= 390, str(bb))
        rec("landscape sheet max-h 90dvh + overflow auto", abs(float(st[0][:-2]) - 351) < 1 and st[1] == "auto", str(st))
        await sh.evaluate("e=>e.scrollTo(0,0)")
        t = await page.locator('[data-testid="login-sheet"] h2').bounding_box()
        rec("landscape title visible at scrollTop 0", t["y"] >= 0, str(t))
        await page.locator('[data-testid="login-sheet-register"]').scroll_into_view_if_needed()
        await page.wait_for_timeout(200)
        r = await page.locator('[data-testid="login-sheet-register"]').bounding_box()
        rec("landscape 'Create an account' reachable by scroll", r["y"] >= 0 and r["y"] + r["height"] <= 390, str(r))
        await sh.evaluate("e=>e.scrollTo(0,e.scrollHeight)")
        await page.wait_for_timeout(200)
        r2 = await page.locator('[data-testid="login-sheet-register"]').bounding_box()
        rec("landscape register visible at max scroll", r2["y"] + r2["height"] <= 390, str(r2))
        await page.screenshot(path=f"{SHOTS}/i9_landscape_sheet_scrolled.jpg", quality=40, type="jpeg")
        # close + reopen
        await page.locator('[data-testid="login-sheet"] [data-testid="dialog-close-button"]').click()
        await page.wait_for_timeout(500)
        await page.click('[data-testid="mobile-book-bar-button"]')
        await sh.wait_for()
        await page.wait_for_timeout(400)
        stale = await page.locator('[data-testid="login-sheet-error"]').count()
        verr = await page.locator('[data-testid="login-sheet-email-error"], [data-testid="login-sheet-password-error"]').count()
        pw = await page.input_value('[data-testid="login-sheet-password"]')
        em = await page.input_value('[data-testid="login-sheet-email"]')
        rec("reopen: no stale server error", stale == 0)
        rec("reopen: no stale validation errors", verr == 0, str(verr))
        rec("reopen: password cleared", pw == "", repr(pw))
        print("  reopen email kept:", repr(em))
        # Escape-close also resets
        await page.fill('[data-testid="login-sheet-password"]', "WrongPass@1")
        await page.click('[data-testid="login-sheet-submit"]')
        await page.locator('[data-testid="login-sheet-error"]').wait_for(timeout=8000)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        await page.click('[data-testid="mobile-book-bar-button"]')
        await sh.wait_for()
        rec("reopen after Escape: error cleared + pw cleared", await page.locator('[data-testid="login-sheet-error"]').count() == 0 and await page.input_value('[data-testid="login-sheet-password"]') == "")
        # correct login in landscape
        await page.fill('[data-testid="login-sheet-email"]', CUST[0])
        await page.fill('[data-testid="login-sheet-password"]', CUST[1])
        await page.click('[data-testid="login-sheet-submit"]')
        await page.wait_for_timeout(2500)
        rec("landscape login success closes sheet, stays on profile", await sh.count() == 0 and f"/astrologers/{AID}" in page.url, page.url)
        # ActionDialog (report-astrologer) landscape
        await page.locator('[data-testid="report-astrologer"]').scroll_into_view_if_needed()
        await page.click('[data-testid="report-astrologer"]')
        d = page.locator('[data-testid="report-user-dialog"]')
        await d.wait_for(timeout=5000)
        await page.wait_for_timeout(400)
        dbb = await d.bounding_box()
        dst = await d.evaluate("e=>[getComputedStyle(e).maxHeight,getComputedStyle(e).overflowY,e.scrollHeight,e.clientHeight]")
        rec("landscape ActionDialog within viewport, max-h 90dvh, overflow auto", dbb["y"] >= -0.5 and dbb["y"] + dbb["height"] <= 390.5 and dst[1] == "auto" and abs(float(dst[0][:-2]) - 351) < 1, f"{dbb} {dst}")
        c = page.locator('[data-testid="report-user-confirm"]')
        await c.scroll_into_view_if_needed()
        cb = await c.bounding_box()
        rec("landscape ActionDialog confirm reachable", cb and cb["y"] + cb["height"] <= 390.5 and cb["y"] >= 0, str(cb))
        await page.screenshot(path=f"{SHOTS}/i9_landscape_actiondialog.jpg", quality=40, type="jpeg")
        await page.keyboard.press("Escape")
        await ctx.close()

        # 3. register from login sheet -> back once leaves profile
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await goto(page, "/discover")
        await goto(page, f"/astrologers/{AID}")
        h0 = await page.evaluate("history.length")
        await page.click('[data-testid="mobile-book-bar-button"]')
        await page.locator('[data-testid="login-sheet"]').wait_for()
        await page.wait_for_timeout(300)
        await page.click('[data-testid="login-sheet-register"]')
        await page.wait_for_url("**/register**", timeout=8000)
        rec("sheet register link -> /register?next=", "next=" in page.url, page.url)
        email = f"TEST_iter9_{int(time.time())}@example.com"
        await page.fill('[data-testid="register-name-input"]', "TEST Iter9")
        await page.fill('[data-testid="register-email-input"]', email)
        await page.fill('[data-testid="register-password-input"]', "TestPass@123")
        await page.click('[data-testid="register-role-customer"]')
        await page.click('[data-testid="register-accept-terms"]')
        await page.click('[data-testid="register-submit-button"]')
        await page.wait_for_timeout(3000)
        rec("register returns to profile", f"/astrologers/{AID}" in page.url, page.url)
        h1 = await page.evaluate("history.length")
        print(f"  history length {h0} -> {h1}")
        bt = (await page.locator('[data-testid="mobile-book-bar-button"]').inner_text()).strip()
        rec("logged in after register (bar says Choose slot)", bt == "Choose slot", bt)
        await page.go_back()
        await page.wait_for_timeout(1500)
        rec("ONE back leaves profile (to /discover)", page.url.rstrip("/").endswith("/discover"), page.url)
        await page.go_forward()
        await page.wait_for_timeout(1500)
        rec("forward goes to profile (no /register stuck)", f"/astrologers/{AID}" in page.url, page.url)
        await ctx.close()
        await b.close()
    print(f"\nTOTAL {sum(1 for _, o in R if o)}/{len(R)} passed")
    print("FAILED:", [n for n, o in R if not o])
    print("CREATED_USER:", email)

asyncio.run(main())
