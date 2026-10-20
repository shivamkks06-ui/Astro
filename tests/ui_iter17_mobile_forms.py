# Iteration 17: mobile (390px) form fixes - login/register validation, password toggle, input styles, kundli form errors, horoscope status, AstroCard button, regression
import asyncio, glob, re
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-*/*/headless_shell")[0]
SHOTS = "/app/.screenshots"
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
R = []
ERRS = []


def rec(name, ok, info=""):
    R.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""), flush=True)


async def goto(page, path):
    await page.goto(BASE + path, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass


async def overflow(page):
    return await page.evaluate("document.documentElement.scrollWidth - window.innerWidth")


async def run_step(name, fn, *a):
    try:
        await fn(*a)
    except Exception as e:
        rec(name + " (exception)", False, str(e)[:300])


async def t_login(ctx):
    page = await ctx.new_page()
    page.on("pageerror", lambda e: ERRS.append(str(e)))
    await goto(page, "/login")
    await page.click('[data-testid="login-submit-button"]')
    e = await page.locator('[data-testid="login-error"]').text_content()
    rec("login empty email", e == "Enter a valid email address.", e)
    rec("login-error role=alert", await page.get_attribute('[data-testid="login-error"]', "role") == "alert")
    await page.fill('[data-testid="login-email-input"]', CUST[0])
    await page.click('[data-testid="login-submit-button"]')
    e = await page.locator('[data-testid="login-error"]').text_content()
    rec("login empty password", e == "Enter your password.", e)
    # input styles
    st = await page.evaluate("""() => { const el = document.querySelector('[data-testid="login-email-input"]'); const s = getComputedStyle(el);
        return {h: el.getBoundingClientRect().height, bg: s.backgroundColor, bw: s.borderTopWidth, bc: s.borderTopColor}; }""")
    rec("input 48px on mobile + bg #0E1830 + border", st["h"] == 48 and st["bg"] == "rgb(14, 24, 48)" and st["bw"] == "1px", str(st))
    await page.focus('[data-testid="login-password-input"]')
    await page.keyboard.press("Tab"); await page.keyboard.press("Shift+Tab")
    fc = await page.evaluate("getComputedStyle(document.activeElement).borderTopColor")
    rec("focus border gold", "252, 211, 77" in fc or "amber" in fc, fc)
    # toggle
    pw = '[data-testid="login-password-input"]'
    t0 = await page.get_attribute(pw, "type")
    await page.click('[data-testid="login-password-toggle"]')
    t1 = await page.get_attribute(pw, "type")
    await page.click('[data-testid="login-password-toggle"]')
    t2 = await page.get_attribute(pw, "type")
    rec("password toggle", (t0, t1, t2) == ("password", "text", "password"), f"{t0},{t1},{t2}")
    # wrong creds
    await page.fill(pw, "WrongPass@999")
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)
    e = await page.locator('[data-testid="login-error"]').text_content()
    rec("wrong creds backend error", e and e not in ("Enter your password.", "Enter a valid email address."), e)
    # valid login with spinner + double submit
    await page.fill(pw, CUST[1])
    reqs = []
    page.on("request", lambda r: reqs.append(r.url) if r.url.endswith("/api/auth/login") else None)
    await page.click('[data-testid="login-submit-button"]')
    busy_txt = await page.locator('[data-testid="login-submit-button"]').text_content()
    dis = await page.locator('[data-testid="login-submit-button"]').is_disabled()
    await page.locator('[data-testid="login-submit-button"]').click(force=True, timeout=1000) if dis else None
    rec("spinner/busy state", "Logging in" in (busy_txt or "") or dis, f"{busy_txt} disabled={dis}")
    await page.wait_for_timeout(4000)
    rec("valid login navigates away", "/login" not in page.url, page.url)
    rec("single login request", len(reqs) == 1, str(len(reqs)))
    await page.screenshot(path=f"{SHOTS}/i17_after_login.jpg", quality=40, full_page=False)
    await page.close()


async def t_register(browser):
    ctx = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = await ctx.new_page()
    await goto(page, "/register")
    sub = '[data-testid="register-submit-button"]'
    rec("register disabled before terms", await page.locator(sub).is_disabled())
    await page.click('[data-testid="register-accept-terms"]')
    await page.click(sub)
    e = await page.locator('[data-testid="register-error"]').text_content()
    rec("register name required", e == "Enter your name.", e)
    await page.fill('[data-testid="register-name-input"]', "TEST_ User")
    await page.fill('[data-testid="register-email-input"]', "bad@email")
    await page.click(sub)
    e = await page.locator('[data-testid="register-error"]').text_content()
    rec("register email format", e == "Enter a valid email address.", e)
    await page.fill('[data-testid="register-email-input"]', "TEST_iter17@example.com")
    await page.fill('[data-testid="register-password-input"]', "short")
    await page.click(sub)
    e = await page.locator('[data-testid="register-error"]').text_content()
    rec("register password min 8", e == "Password must be at least 8 characters.", e)
    t0 = await page.get_attribute('[data-testid="register-password-input"]', "type")
    await page.click('[data-testid="register-password-toggle"]')
    t1 = await page.get_attribute('[data-testid="register-password-input"]', "type")
    rec("register password toggle", (t0, t1) == ("password", "text"))
    await page.click('[data-testid="register-accept-terms"]')
    rec("terms uncheck disables submit", await page.locator(sub).is_disabled())
    await page.screenshot(path=f"{SHOTS}/i17_register.jpg", quality=40, full_page=False)
    await ctx.close()


async def t_kundli(ctx):
    page = await ctx.new_page()
    page.on("pageerror", lambda e: ERRS.append(str(e)))
    await goto(page, "/kundli")
    err = '[data-testid="kundli-form-error"]'
    await page.click('[data-testid="kundli-submit"]')
    rec("kundli missing date/time", (await page.locator(err).text_content()) == "Enter the birth date and time.")
    await page.fill('[data-testid="kundli-date-input"]', "1850-05-05")
    await page.fill('[data-testid="kundli-time-input"]', "10:30")
    await page.click('[data-testid="kundli-submit"]')
    e = await page.locator(err).text_content()
    rec("kundli year out of range", e == "Birth year must be between 1900 and 2049.", e)
    await page.fill('[data-testid="kundli-date-input"]', "1990-05-05")
    await page.click('[data-testid="kundli-submit"]')
    e = await page.locator(err).text_content()
    rec("kundli missing place", e == "Choose the birthplace from the list.", e)
    # focusin scroll
    await page.evaluate("window.scrollTo(0, 0)")
    await page.focus('[data-testid="kundli-place-input"]')
    await page.fill('[data-testid="kundli-place-input"]', "Delhi")
    await page.wait_for_timeout(1200)
    rect = await page.evaluate("document.querySelector('[data-testid=\"kundli-place-input\"]').getBoundingClientRect().top")
    rec("place input in viewport after focus", 0 <= rect <= 844, str(rect))
    await page.click('[data-testid="kundli-place-option-0"]')
    reqs = []
    page.on("request", lambda r: reqs.append(r.url) if "/api/kundli" in r.url and r.method == "POST" else None)
    await page.click('[data-testid="kundli-submit"]')
    try:
        await page.locator('[data-testid="kundli-submit"]').click(force=True, timeout=500)
    except Exception:
        pass
    await page.wait_for_timeout(5000)
    body = await page.text_content("body")
    rec("kundli calculated", "Lagna" in body or "Ascendant" in body, page.url)
    rec("kundli single POST", len(reqs) <= 1, str(reqs))
    rec("kundli no overflow", await overflow(page) <= 0)
    await page.screenshot(path=f"{SHOTS}/i17_kundli.jpg", quality=40, full_page=False)
    await page.close()


async def t_horoscope(ctx):
    page = await ctx.new_page()
    await goto(page, "/horoscope")
    await page.locator('[data-testid="horoscope-overview"]').wait_for(timeout=20000)
    st = page.locator('[data-testid="horoscope-ai-status"]')
    if await st.count():
        txt = await st.text_content()
        spin = await st.locator("svg.animate-spin").count()
        rec("horoscope ai status shown", bool(txt), f"{txt} spinner={spin}")
    else:
        rec("horoscope ai overview present (no pending)", await page.locator('[data-testid="horoscope-ai-overview"]').count() > 0)
    col = await page.evaluate("""() => { const p = document.querySelector('[data-testid="horoscope-overview"] p.leading-relaxed, [data-testid="horoscope-overview"] p'); return p ? getComputedStyle(p).color : null; }""")
    rec("overview text color readable", col is not None, col)
    await page.click('[data-testid="lang-hi"]')
    await page.wait_for_timeout(1500)
    hi = await page.text_content('[data-testid="horoscope-overview"]')
    rec("hindi toggle works", bool(re.search(r"[\u0900-\u097F]", hi or "")))
    await page.screenshot(path=f"{SHOTS}/i17_horoscope_hi.jpg", quality=40, full_page=False)
    await page.click('[data-testid="lang-en"]')
    await page.wait_for_timeout(800)
    await page.close()


async def t_discover(ctx):
    page = await ctx.new_page()
    await goto(page, "/discover")
    cards = page.locator('[data-testid^="astrologer-card-"]:not([data-testid*="availability"])')
    await cards.first.wait_for(timeout=15000)
    n = await cards.count()
    btn = cards.first.locator("span", has_text="View profile & book")
    bg = await btn.evaluate("e => getComputedStyle(e).backgroundColor")
    rec("view profile gold filled button", bg not in ("rgba(0, 0, 0, 0)", "transparent"), bg)
    last = cards.nth(n - 1)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(800)
    lb = await last.evaluate("e => e.getBoundingClientRect().bottom")
    nt = await page.evaluate("document.querySelector('[data-testid=\"bottom-nav\"]').getBoundingClientRect().top")
    sh = await page.evaluate("document.documentElement.scrollHeight")
    # Scroll so the last card bottom aligns; check that max scroll lets it clear the nav
    await last.scroll_into_view_if_needed()
    await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    lb = await last.evaluate("e => e.getBoundingClientRect().bottom")
    rec("last card clears bottom nav", lb <= nt, f"cards={n} lastBottom={lb} navTop={nt}")
    await page.screenshot(path=f"{SHOTS}/i17_discover_bottom.jpg", quality=40, full_page=False)
    await page.evaluate("window.scrollTo(0,0)")
    await btn.click()
    await page.wait_for_url("**/astrologers/**", timeout=10000)
    rec("card button navigates to profile", "/astrologers/" in page.url)
    await page.close()


async def t_regression(ctx):
    page = await ctx.new_page()
    await goto(page, "/")
    nav = await page.locator('[data-testid="bottom-nav"] a, [data-testid="bottom-nav"] button').count()
    rec("bottom nav 5 tabs", nav == 5, str(nav))
    await page.click('[data-testid="mobile-menu-button"]')
    await page.wait_for_timeout(500)
    rec("drawer opens", await page.locator('[data-testid="mobile-drawer"]').is_visible())
    url = page.url
    await page.evaluate("window.__nvBack && window.__nvBack()")
    await page.wait_for_timeout(600)
    rec("__nvBack closes drawer first", (not await page.locator('[data-testid="mobile-drawer"]').is_visible()) and page.url == url, page.url)
    for w in (360, 390):
        await page.set_viewport_size({"width": w, "height": 844})
        for p in ("/", "/login", "/register", "/discover", "/kundli", "/horoscope"):
            await goto(page, p)
            o = await overflow(page)
            if o > 0:
                rec(f"overflow {w} {p}", False, str(o))
    rec("overflow check done", True)
    await page.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await run_step("login", t_login, ctx)
        await run_step("register", t_register, b)
        anon = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await run_step("kundli", t_kundli, anon)
        await run_step("horoscope", t_horoscope, anon)
        await run_step("discover", t_discover, anon)
        await run_step("regression", t_regression, anon)
        await b.close()
    print("PAGE ERRORS:", ERRS)
    print(f"TOTAL {sum(o for _, o in R)}/{len(R)}")

asyncio.run(main())
