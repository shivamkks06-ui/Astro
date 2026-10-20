# Iteration 11: Android Back logic (window.__nvBack), root double-press exit, Discover URL state, avatar fallback, mobile regressions
import asyncio, glob, json, re, base64
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]
SHOTS = "/app/.screenshots"
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
R = []


def rec(name, ok, info=""):
    R.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""), flush=True)


async def goto(page, path):
    await page.goto(BASE + path, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    await page.wait_for_function("typeof window.__nvBack === 'function'", timeout=15000)


async def back(page):
    r = await page.evaluate("window.__nvBack()")
    await page.wait_for_timeout(600)
    return r


def path_of(page):
    return page.url.replace(BASE, "")


async def idx(page):
    return await page.evaluate("window.history.state?.idx ?? null")


async def overflow(page):
    return await page.evaluate("document.documentElement.scrollWidth - window.innerWidth")


async def first_card(page):
    c = page.locator('[data-testid^="astrologer-card-"]:not([data-testid*="availability"])').first
    await c.wait_for(timeout=15000)
    return c


async def test_back_nested(ctx):
    page = await ctx.new_page()
    await goto(page, "/")
    await page.click('[data-testid="bottom-nav-discover"]')
    await page.wait_for_url("**/discover", timeout=10000)
    c = await first_card(page)
    await c.click()
    await page.wait_for_url("**/astrologers/**", timeout=10000)
    await page.locator('[data-testid="astrologer-name"]').wait_for(timeout=15000)
    r = await back(page)
    rec("nested: profile -> __nvBack returns 'back'", r == "back", r)
    rec("nested: URL back to /discover", path_of(page) == "/discover", path_of(page))

    # drawer overlay
    await page.click('[data-testid="mobile-menu-button"]')
    await page.locator('[data-testid="mobile-drawer"]').wait_for(timeout=5000)
    await page.wait_for_timeout(400)
    r = await back(page)
    rec("drawer: __nvBack returns 'overlay'", r == "overlay", r)
    rec("drawer: closed after overlay back", await page.locator('[data-testid="mobile-drawer"]').count() == 0)
    rec("drawer: route unchanged", path_of(page) == "/discover", path_of(page))

    # select dropdown overlay
    await page.click('[data-testid="filter-language"]')
    await page.locator('[role="listbox"]').wait_for(timeout=5000)
    await page.wait_for_timeout(300)
    r = await back(page)
    rec("select: __nvBack returns 'overlay'", r == "overlay", r)
    rec("select: listbox closed", await page.locator('[role="listbox"]').count() == 0)
    rec("select: route unchanged", path_of(page) == "/discover", path_of(page))
    await page.click('[data-testid="sort-select"]')
    await page.locator('[role="listbox"]').wait_for(timeout=5000)
    await page.wait_for_timeout(300)
    r = await back(page)
    rec("sort select: overlay closes", r == "overlay" and await page.locator('[role="listbox"]').count() == 0, r)

    # profile login sheet overlay
    c = await first_card(page)
    await c.click()
    await page.locator('[data-testid="astrologer-name"]').wait_for(timeout=15000)
    prof = path_of(page)
    await page.click('[data-testid="mobile-book-bar-button"]')
    await page.locator('[data-testid="login-sheet"]').wait_for(timeout=5000)
    await page.wait_for_timeout(400)
    # focus the email input to mimic a real user (keyboard is closed)
    r = await back(page)
    rec("login sheet: __nvBack returns 'overlay'", r == "overlay", r)
    rec("login sheet: closed", await page.locator('[data-testid="login-sheet"]').count() == 0)
    rec("login sheet: route unchanged", path_of(page) == prof, path_of(page))
    # login sheet with focus inside an input
    await page.click('[data-testid="mobile-book-bar-button"]')
    await page.locator('[data-testid="login-sheet"]').wait_for(timeout=5000)
    await page.wait_for_timeout(300)
    inp = page.locator('[data-testid="login-sheet"] input').first
    if await inp.count():
        await inp.focus()
    r = await back(page)
    rec("login sheet (input focused): overlay closes", r == "overlay" and await page.locator('[data-testid="login-sheet"]').count() == 0, r)
    r = await back(page)
    rec("profile -> back returns to /discover", r == "back" and path_of(page) == "/discover", f"{r} {path_of(page)}")
    r = await back(page)
    rec("discover -> back returns to /", r == "back" and path_of(page) == "/", f"{r} {path_of(page)}")
    await page.close()


async def test_root_exit(ctx, H):
    page = await ctx.new_page()
    await goto(page, "/")
    rec("root: history idx is 0 on direct open", (await idx(page)) == 0, str(await idx(page)))
    r = await page.evaluate("window.__nvBack()")
    rec("root: first press 'exit-armed'", r == "exit-armed", r)
    t = page.get_by_text("Press back again to exit")
    try:
        await t.wait_for(timeout=1500)
        bb = await t.bounding_box()
        rec("root: exit toast visible", True)
        rec("root: exit toast at bottom", bb and bb["y"] > H * 0.6, str(bb))
    except Exception as e:
        rec("root: exit toast visible", False, str(e)[:100])
    await page.screenshot(path=f"{SHOTS}/i11_exit_toast.jpeg", quality=40, full_page=False)
    r = await page.evaluate("window.__nvBack()")
    rec("root: second press within 2s 'exit'", r == "exit", r)
    await page.wait_for_timeout(400)
    rec("root: web stays on / after exit", path_of(page) == "/", path_of(page))
    rec("root: toast dismissed after exit", await page.get_by_text("Press back again to exit").count() == 0 or not await page.get_by_text("Press back again to exit").is_visible())
    # re-arm after timeout
    r = await page.evaluate("window.__nvBack()")
    rec("root: next press after exit re-arms", r == "exit-armed", r)
    await page.wait_for_timeout(2300)
    r = await page.evaluate("window.__nvBack()")
    rec("root: press after >2s is 'exit-armed' (not exit)", r == "exit-armed", r)
    vis = await page.get_by_text("Press back again to exit").count()
    rec("root: toast shown again", vis > 0)
    r = await page.evaluate("window.__nvBack()")
    rec("root: quick follow-up 'exit'", r == "exit", r)
    await page.close()

    # deep link to /discover
    page = await ctx.new_page()
    await goto(page, "/discover")
    hl = await page.evaluate("history.length")
    rec("deeplink: idx 0", (await idx(page)) == 0, str(await idx(page)))
    r = await back(page)
    rec("deeplink /discover: returns 'home'", r == "home", r)
    rec("deeplink: navigated to /", path_of(page) == "/", path_of(page))
    rec("deeplink: replace (history.length same, idx 0)", (await page.evaluate("history.length")) == hl and (await idx(page)) == 0, f"{hl} {await page.evaluate('history.length')} {await idx(page)}")
    r = await page.evaluate("window.__nvBack()")
    rec("deeplink: then root arms exit", r == "exit-armed", r)
    await page.wait_for_timeout(2200)
    # deep link to profile
    await goto(page, "/discover")
    c = await first_card(page)
    href = await c.get_attribute("href")
    p2 = await ctx.new_page()
    await goto(p2, href)
    r = await back(p2)
    rec("deeplink profile: 'home' -> /", r == "home" and path_of(p2) == "/", f"{r} {path_of(p2)}")
    await p2.close()

    # 5 cycles Home -> Discover -> Back
    await goto(page, "/")
    base_idx = await idx(page)
    ok_all, info = True, []
    for i in range(5):
        await page.click('[data-testid="bottom-nav-discover"]')
        await page.wait_for_url("**/discover", timeout=10000)
        await page.wait_for_timeout(300)
        r = await page.evaluate("window.__nvBack()")
        await page.wait_for_timeout(800)
        p, ix = path_of(page), await idx(page)
        info.append((r, p, ix))
        if not (r == "back" and p == "/" and ix == base_idx):
            ok_all = False
    rec("5 cycles Home->Discover->Back exactly one step each", ok_all, str(info))
    await page.close()


async def test_discover_state(ctx):
    page = await ctx.new_page()
    reqs = []
    page.on("request", lambda rq: reqs.append(rq.url) if "/api/astrologers?" in rq.url else None)
    await goto(page, "/")
    await page.click('[data-testid="bottom-nav-discover"]')
    await page.wait_for_url("**/discover", timeout=10000)
    await first_card(page)
    cnt = page.locator('[data-testid="results-count"]')
    txt = await cnt.inner_text()
    rec("results-count plural", re.fullmatch(r"\d+ astrologers", txt) is not None, txt)
    hl0 = await page.evaluate("history.length")
    await page.click('[data-testid="filter-search"]')
    await page.keyboard.type("Raman", delay=80)
    await page.wait_for_timeout(1500)
    rec("search: URL has q=Raman", "q=Raman" in page.url, page.url)
    rec("search: no extra history entries per keystroke", (await page.evaluate("history.length")) == hl0, f"{hl0} -> {await page.evaluate('history.length')}")
    txt = await cnt.inner_text()
    rec("results-count singular '1 astrologer'", txt == "1 astrologer", txt)

    async def pick(testid, label):
        await page.click(f'[data-testid="{testid}"]')
        await page.locator('[role="listbox"]').wait_for(timeout=5000)
        await page.wait_for_timeout(200)
        await page.get_by_role("option", name=label, exact=True).click(force=True)
        await page.wait_for_timeout(900)

    await pick("filter-language", "Tamil")
    await pick("filter-expertise", "Vedic")
    await page.fill('[data-testid="filter-min-exp"]', "10")
    await page.wait_for_timeout(600)
    await page.click('[data-testid="filter-credential-verified"]')
    await page.wait_for_timeout(600)
    await pick("sort-select", "Most experienced")
    url = page.url
    for k, v in [("q", "Raman"), ("language", "Tamil"), ("expertise", "Vedic"), ("min_exp", "10"), ("verified_credential", "true"), ("sort", "experience")]:
        rec(f"URL reflects {k}={v}", f"{k}={v}" in url, url)
    rec("filters: history.length unchanged", (await page.evaluate("history.length")) == hl0, f"{hl0} -> {await page.evaluate('history.length')}")
    last = reqs[-1] if reqs else ""
    rec("API request carries all filters", all(s in last for s in ["q=Raman", "language=Tamil", "expertise=Vedic", "min_exp=10", "verified_credential=true", "sort=experience"]), last)
    n_before = await cnt.inner_text()
    await page.screenshot(path=f"{SHOTS}/i11_discover_filters.jpeg", quality=40, full_page=False)
    c = await first_card(page)
    await c.click()
    await page.locator('[data-testid="astrologer-name"]').wait_for(timeout=15000)
    r = await back(page)
    await page.wait_for_timeout(800)
    rec("profile back: 'back' to same filtered URL", r == "back" and page.url == url, f"{r} {page.url}")
    rec("restored: search input", (await page.input_value('[data-testid="filter-search"]')) == "Raman")
    rec("restored: language", "Tamil" in await page.inner_text('[data-testid="filter-language"]'), await page.inner_text('[data-testid="filter-language"]'))
    rec("restored: expertise", "Vedic" in await page.inner_text('[data-testid="filter-expertise"]'))
    rec("restored: min exp", (await page.input_value('[data-testid="filter-min-exp"]')) == "10")
    rec("restored: credential switch", (await page.get_attribute('[data-testid="filter-credential-verified"]', "data-state")) == "checked")
    rec("restored: sort", "Most experienced" in await page.inner_text('[data-testid="sort-select"]'))
    rec("restored: results count", (await cnt.inner_text()) == n_before, await cnt.inner_text())
    # one more back goes home (no extra entries)
    r = await back(page)
    rec("next back goes to / (no filter history entries)", r == "back" and path_of(page) == "/", f"{r} {path_of(page)}")

    # empty + clear filters
    await goto(page, "/discover?q=zzzzqqq")
    await page.locator('[data-testid="empty-state"]').wait_for(timeout=10000)
    rec("empty: count '0 astrologers'", (await cnt.inner_text()) == "0 astrologers", await cnt.inner_text())
    await page.click('[data-testid="clear-filters"]')
    await page.wait_for_timeout(1200)
    rec("clear-filters resets URL", path_of(page) == "/discover", path_of(page))
    rec("clear-filters resets search input", (await page.input_value('[data-testid="filter-search"]')) == "")
    rec("clear-filters shows results again", await page.locator('[data-testid^="astrologer-card-"]:not([data-testid*="availability"])').count() > 0)
    # empty from min_exp only
    await goto(page, "/discover?min_exp=99&language=Tamil")
    await page.locator('[data-testid="empty-state"]').wait_for(timeout=10000)
    rec("empty via min_exp shows clear button", await page.locator('[data-testid="clear-filters"]').count() == 1)

    # pagination: page param directly
    reqs.clear()
    await goto(page, "/discover?page=2")
    await page.wait_for_timeout(500)
    rec("page param -> API page=2", any("page=2" in u for u in reqs), str(reqs[-1:]))
    # pagination UI with faked total
    async def fake_total(route):
        resp = await route.fetch()
        d = await resp.json()
        d["total"] = 30
        await route.fulfill(response=resp, body=json.dumps(d), headers={**resp.headers, "content-type": "application/json"})
    await page.route("**/api/astrologers?*", fake_total)
    await goto(page, "/discover")
    await page.locator('[data-testid="page-next"]').wait_for(timeout=10000)
    reqs.clear()
    await page.click('[data-testid="page-next"]')
    await page.wait_for_timeout(1000)
    rec("page-next sets page=2 in URL", "page=2" in page.url, page.url)
    rec("page-next requests page=2", any("page=2" in u for u in reqs), str(reqs[-1:]))
    await page.click('[data-testid="page-next"]')
    await page.wait_for_timeout(800)
    rec("page 3 / 3", "page=3" in page.url and (await page.locator('[data-testid="page-next"]').is_disabled()), page.url)
    await page.click('[data-testid="page-prev"]')
    await page.click('[data-testid="page-prev"]')
    await page.wait_for_timeout(800)
    rec("page-prev back to page 1 removes param", "page=" not in page.url, page.url)
    await page.fill('[data-testid="filter-search"]', "a")
    await page.wait_for_timeout(500)
    await page.unroute("**/api/astrologers?*")

    # error + loading states
    async def fail(route):
        await route.fulfill(status=500, body='{"detail":"boom"}', headers={"content-type": "application/json"})
    await page.route("**/api/astrologers?*", fail)
    await goto(page, "/discover")
    try:
        await page.locator('[data-testid="error-state"]').wait_for(timeout=10000)
        rec("error state shown on 500", True)
        rec("retry button present", await page.locator('[data-testid="retry-button"]').count() == 1)
    except Exception:
        rec("error state shown on 500", False)
    await page.unroute("**/api/astrologers?*")
    await page.click('[data-testid="retry-button"]')
    await page.wait_for_timeout(1500)
    rec("retry recovers list", await page.locator('[data-testid^="astrologer-card-"]:not([data-testid*="availability"])').count() > 0)

    async def slow(route):
        await asyncio.sleep(2.5)
        await route.continue_()
    await page.route("**/api/astrologers?*", slow)
    await page.goto(BASE + "/discover", wait_until="domcontentloaded")
    try:
        await page.locator('[data-testid="cards-skeleton"]').first.wait_for(timeout=4000)
        rec("loading skeleton shown", True)
    except Exception:
        rec("loading skeleton shown", False)
    await page.unroute("**/api/astrologers?*")
    await page.close()


async def test_avatar(ctx):
    page = await ctx.new_page()
    mode = {"photo": "ok"}

    async def inject(route):
        resp = await route.fetch()
        d = await resp.json()
        for a in d.get("items", []):
            a["photo_url"] = f"/api/astrologers/{a['id']}/photo?v=test"
        await route.fulfill(response=resp, body=json.dumps(d), headers={**resp.headers, "content-type": "application/json"})

    async def photo(route):
        if mode["photo"] == "ok":
            await route.fulfill(status=200, body=PNG, headers={"content-type": "image/png"})
        elif mode["photo"] == "404":
            await route.fulfill(status=404, body="nf")
        else:
            await route.abort()

    await page.route("**/api/astrologers?*", inject)
    await page.route("**/api/astrologers/*/photo*", photo)
    await goto(page, "/discover")
    await first_card(page)
    imgs = page.locator('[data-testid="astrologer-photo"]')
    await page.wait_for_timeout(800)
    n = await imgs.count()
    rec("avatar: photo img rendered when URL loads", n > 0, str(n))
    if n:
        w, h = await imgs.first.get_attribute("width"), await imgs.first.get_attribute("height")
        rec("avatar: img has width/height attrs", w and h, f"{w}x{h}")
        bb = await imgs.first.bounding_box()
        rec("avatar: rendered 56x56", bb and abs(bb["width"] - 56) < 1 and abs(bb["height"] - 56) < 1, str(bb))
        rec("avatar: loading=lazy", (await imgs.first.get_attribute("loading")) == "lazy")
    for m in ["404", "abort"]:
        mode["photo"] = m
        await goto(page, "/discover")
        await first_card(page)
        await page.wait_for_timeout(1500)
        c = await first_card(page)
        n_img = await page.locator('[data-testid="astrologer-photo"]').count()
        broken = await page.evaluate("Array.from(document.images).filter(i=>i.complete && i.naturalWidth===0 && i.src.includes('/photo')).length")
        txt = await c.inner_text()
        rec(f"avatar {m}: no broken img, initials shown", n_img == 0 and broken == 0, f"imgs={n_img} broken={broken}")
        rec(f"avatar {m}: initials text present", bool(re.search(r"^\s*[A-Z]{1,2}\s*$", txt.split("\n")[0])), repr(txt.split("\n")[0]))
    await page.screenshot(path=f"{SHOTS}/i11_avatar_fallback.jpeg", quality=40, full_page=False)
    # profile page fallback
    async def inject_one(route):
        resp = await route.fetch()
        try:
            d = await resp.json()
        except Exception:
            return await route.fulfill(response=resp)
        if isinstance(d, dict) and "id" in d and "display_name" in d:
            d["photo_url"] = f"/api/astrologers/{d['id']}/photo?v=test"
        await route.fulfill(response=resp, body=json.dumps(d), headers={**resp.headers, "content-type": "application/json"})
    await page.route(re.compile(r".*/api/astrologers/[0-9a-f]{32}$"), inject_one)
    c = await first_card(page)
    await c.click()
    await page.locator('[data-testid="astrologer-name"]').wait_for(timeout=15000)
    await page.wait_for_timeout(1500)
    broken = await page.evaluate("Array.from(document.images).filter(i=>i.complete && i.naturalWidth===0).length")
    rec("profile: no broken images on photo failure", broken == 0, str(broken))
    imgs_no_dims = await page.evaluate("Array.from(document.images).filter(i=>!i.getAttribute('width')||!i.getAttribute('height')).map(i=>i.src.slice(-60))")
    rec("profile: all imgs have width/height", len(imgs_no_dims) == 0, str(imgs_no_dims))
    await goto(page, "/")
    imgs_no_dims = await page.evaluate("Array.from(document.images).filter(i=>!i.getAttribute('width')||!i.getAttribute('height')).map(i=>i.src.slice(-60))")
    rec("home: all imgs have width/height", len(imgs_no_dims) == 0, str(imgs_no_dims))
    await page.close()


async def regression(browser, w, h):
    ctx = await browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = await ctx.new_page()
    tag = f"[{w}]"
    for p in ["/", "/discover"]:
        await goto(page, p)
        rec(f"{tag} {p} no horizontal overflow", await overflow(page) <= 0, str(await overflow(page)))
    rec(f"{tag} bottom nav visible", await page.locator('[data-testid="bottom-nav"]').is_visible())
    await page.click('[data-testid="mobile-menu-button"]')
    await page.locator('[data-testid="mobile-drawer"]').wait_for(timeout=5000)
    await page.wait_for_timeout(700)
    d = await page.locator('[data-testid="mobile-drawer"]').bounding_box()
    rec(f"{tag} drawer opens right-anchored", d and abs(d["x"] + d["width"] - w) < 2, str(d))
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(500)
    c = await first_card(page)
    await c.click()
    await page.locator('[data-testid="astrologer-name"]').wait_for(timeout=15000)
    await page.wait_for_timeout(500)
    rec(f"{tag} profile no overflow", await overflow(page) <= 0, str(await overflow(page)))
    await page.click('[data-testid="mobile-book-bar-button"]')
    s = page.locator('[data-testid="login-sheet"]')
    await s.wait_for(timeout=5000)
    await page.wait_for_timeout(500)
    sb = await s.bounding_box()
    rec(f"{tag} login sheet bottom anchored full width", sb and abs(sb["y"] + sb["height"] - h) < 2 and abs(sb["width"] - w) < 2, str(sb))
    await page.locator('[data-testid="login-sheet"] input[type="email"]').fill(CUST[0])
    await page.locator('[data-testid="login-sheet"] input[type="password"]').fill(CUST[1])
    await page.click('[data-testid="login-sheet-submit"]')
    await page.wait_for_timeout(2500)
    rec(f"{tag} login sheet login keeps profile", "/astrologers/" in page.url and await s.count() == 0, page.url)
    slot = page.locator('[data-testid^="slot-"]').first
    if await slot.count():
        await slot.click()
        await page.click('[data-testid="mobile-book-bar-button"]')
        dlg = page.locator('[data-testid="booking-dialog"]')
        try:
            await dlg.wait_for(timeout=5000)
            await page.wait_for_timeout(500)
            bb = await dlg.bounding_box()
            rec(f"{tag} booking dialog anchored, within width", bb and bb["width"] <= w + 1 and abs(bb["y"] + bb["height"] - h) < 3, str(bb))
            await page.screenshot(path=f"{SHOTS}/i11_booking_{w}.jpeg", quality=40, full_page=False)
            r = await page.evaluate("window.__nvBack()")
            await page.wait_for_timeout(500)
            rec(f"{tag} booking dialog closes on back ('overlay')", r == "overlay" and await dlg.count() == 0 and "/astrologers/" in page.url, r)
        except Exception as e:
            rec(f"{tag} booking dialog opens", False, str(e)[:120])
    else:
        rec(f"{tag} slots available for booking dialog", False, "no slots")
    # logout via API to restore
    await page.evaluate("fetch('/api/auth/logout',{method:'POST',credentials:'include'})")
    await ctx.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=EXE)
        ctx = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        for name, fn in [("nested", lambda: test_back_nested(ctx)), ("root", lambda: test_root_exit(ctx, 844)),
                         ("discover", lambda: test_discover_state(ctx)), ("avatar", lambda: test_avatar(ctx))]:
            try:
                await fn()
            except Exception as e:
                rec(f"{name} suite crashed", False, str(e)[:300])
        await ctx.close()
        for w, h in [(360, 780), (390, 844)]:
            try:
                await regression(browser, w, h)
            except Exception as e:
                rec(f"regression {w} crashed", False, str(e)[:300])
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await goto(page, "/discover")
        rec("[1920] menu button hidden", not await page.locator('[data-testid="mobile-menu-button"]').is_visible())
        rec("[1920] header login visible", await page.locator('header [data-testid="nav-login"]').first.is_visible())
        rec("[1920] bottom nav hidden", not await page.locator('[data-testid="bottom-nav"]').is_visible())
        rec("[1920] no overflow", await overflow(page) <= 0)
        await page.screenshot(path=f"{SHOTS}/i11_desktop.jpeg", quality=40, full_page=False)
        await browser.close()
    passed = sum(1 for _, ok in R if ok)
    print(f"\nTOTAL {passed}/{len(R)} passed")
    for n, ok in R:
        if not ok:
            print("FAILED:", n)


asyncio.run(main())
