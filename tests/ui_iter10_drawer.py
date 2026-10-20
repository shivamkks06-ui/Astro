# Iteration 10: mobile drawer layout/behaviour, scroll lock, back/Escape, homepage hero containment, regressions
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]
SHOTS = "/app/.screenshots"
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
R = []


def rec(name, ok, info=""):
    R.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {info}" if info else ""))


async def goto(page, path):
    await page.goto(BASE + path, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass


async def open_drawer(page):
    await page.click('[data-testid="mobile-menu-button"]')
    await page.locator('[data-testid="mobile-drawer"]').wait_for(timeout=5000)
    await page.wait_for_timeout(500)


async def drawer_geometry(page, w, h, tag, logged_in=False):
    d = await page.locator('[data-testid="mobile-drawer"]').bounding_box()
    exp = min(0.84 * w, 320)
    rec(f"{tag} drawer width=min(84vw,320)", abs(d["width"] - exp) < 1.5, f"{d['width']} vs {exp}")
    rec(f"{tag} drawer anchored right, full height", abs(d["x"] + d["width"] - w) < 1.5 and d["y"] >= -0.5 and abs(d["height"] - h) < 1.5, str(d))
    c = await page.locator('[data-testid="sheet-close-button"]').bounding_box()
    rec(f"{tag} close btn 44x44 top-right", abs(c["width"] - 44) < 1 and abs(c["height"] - 44) < 1 and (w - (c["x"] + c["width"])) < 16 and c["y"] < 20, str(c))
    title = await page.locator('[data-testid="mobile-drawer"] h2').bounding_box()
    rec(f"{tag} title row at top", title and title["y"] < 10 and title["height"] >= 60, str(title))
    links = ["nav-discover", "nav-legal-guidelines"] + (["nav-account"] if logged_in else [])
    boxes = []
    for t in links:
        loc = page.locator(f'[data-testid="mobile-drawer"] [data-testid="{t}"]')
        if await loc.count() == 0:
            rec(f"{tag} {t} present", False)
            continue
        boxes.append(await loc.bounding_box())
    if boxes:
        rec(f"{tag} nav links >=48px tall", all(b["height"] >= 47.5 for b in boxes), str([b["height"] for b in boxes]))
        rec(f"{tag} nav links left-aligned one column", len({round(b["x"]) for b in boxes}) == 1 and all(boxes[i]["y"] < boxes[i + 1]["y"] for i in range(len(boxes) - 1)), str([(b["x"], b["y"]) for b in boxes]))
        rec(f"{tag} nav links inside drawer", all(b["x"] >= d["x"] and b["x"] + b["width"] <= d["x"] + d["width"] + 0.5 for b in boxes))
    if logged_in:
        lo = await page.locator('[data-testid="mobile-drawer"] [data-testid="logout-button"]').bounding_box()
        rec(f"{tag} logout full-width 48px", lo and lo["height"] >= 47.5 and lo["width"] >= d["width"] - 42, str(lo))
        last_bottom = lo["y"] + lo["height"]
    else:
        lg = await page.locator('[data-testid="mobile-drawer"] [data-testid="nav-login"]').bounding_box()
        rg = await page.locator('[data-testid="mobile-drawer"] [data-testid="nav-register"]').bounding_box()
        rec(f"{tag} login/join 48px full-width stacked", lg["height"] >= 47.5 and rg["height"] >= 47.5 and abs(lg["width"] - rg["width"]) < 1 and lg["width"] >= d["width"] - 42 and rg["y"] > lg["y"] + lg["height"] - 1 and abs(lg["x"] - rg["x"]) < 1, f"{lg} {rg}")
        last_bottom = rg["y"] + rg["height"]
    tc = await page.locator('[data-testid="drawer-trust-card"]').bounding_box()
    rec(f"{tag} trust card at bottom, inside, below links", tc["y"] > last_bottom and abs(tc["y"] + tc["height"] + 16 - h) < 3 and tc["x"] >= d["x"] and tc["x"] + tc["width"] <= d["x"] + d["width"] + 0.5, f"tc={tc} last={last_bottom}")
    ov = await page.evaluate("""() => { const d=document.querySelector('[data-testid=mobile-drawer]'); const r=d.getBoundingClientRect();
      const bad=[...d.querySelectorAll('*')].filter(e=>{const b=e.getBoundingClientRect(); return b.width>0 && (b.right>r.right+0.5 || b.left<r.left-0.5)}).map(e=>e.tagName+':'+(e.textContent||'').slice(0,20));
      return {sw:d.scrollWidth, cw:d.clientWidth, bad, docSW: document.documentElement.scrollWidth} }""")
    rec(f"{tag} no overflow inside drawer", ov["sw"] <= ov["cw"] and not ov["bad"], str(ov))
    bd = await page.evaluate("""() => { const o=[...document.querySelectorAll('[data-state=open]')].find(e=>e.getAttribute('data-aria-hidden')==='true' || (e.className||'').toString().includes('bg-black')); 
      if(!o) return null; const s=getComputedStyle(o); const b=o.getBoundingClientRect(); return {bg:s.backgroundColor, pos:s.position, top:s.top, left:s.left, right:s.right, bottom:s.bottom, w:b.width, h:b.height} }""")
    rec(f"{tag} backdrop black/50 full-screen", bd and bd["bg"] in ("rgba(0, 0, 0, 0.5)",) and bd["pos"] == "fixed" and abs(bd["w"] - w) < 1 and abs(bd["h"] - h) < 1, str(bd))


async def login(page):
    await goto(page, "/login")
    await page.fill('[data-testid="login-email-input"]', CUST[0])
    await page.fill('[data-testid="login-password-input"]', CUST[1])
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        # 1. drawer geometry at widths (logged out)
        for w, h in [(320, 800), (360, 800), (390, 844), (430, 844)]:
            ctx = await b.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            await goto(page, "/")
            await open_drawer(page)
            await drawer_geometry(page, w, h, f"[{w}]")
            if w in (320, 390):
                await page.screenshot(path=f"{SHOTS}/i10_drawer_{w}.jpg", quality=40, type="jpeg")
            await ctx.close()

        # 2. scroll lock + restore, Escape / close button, back behaviour (390)
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await goto(page, "/")
        await page.evaluate("window.scrollTo(0,400)")
        await page.wait_for_timeout(300)
        y0 = await page.evaluate("window.scrollY")
        rec("home scrolled to 400", abs(y0 - 400) < 2, str(y0))
        await open_drawer(page)
        lock = await page.evaluate("() => ({ov: getComputedStyle(document.body).overflow, attr: document.body.getAttribute('data-scroll-locked')})")
        rec("body scroll locked while open", lock["ov"] == "hidden" or lock["attr"] is not None, str(lock))
        await page.mouse.wheel(0, 600)
        await page.wait_for_timeout(400)
        y1 = await page.evaluate("window.scrollY")
        rec("page under drawer doesn't scroll on wheel", abs(y1 - 400) < 2, str(y1))
        url_before = page.url
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        rec("Escape closes drawer", await page.locator('[data-testid="mobile-drawer"]').count() == 0)
        rec("Escape doesn't change URL", page.url == url_before, page.url)
        y2 = await page.evaluate("window.scrollY")
        rec("scrollY restored to 400 after Escape", abs(y2 - 400) < 2, str(y2))
        await open_drawer(page)
        await page.click('[data-testid="sheet-close-button"]')
        await page.wait_for_timeout(500)
        y3 = await page.evaluate("window.scrollY")
        rec("close button closes drawer + scroll restored", await page.locator('[data-testid="mobile-drawer"]').count() == 0 and abs(y3 - 400) < 2, str(y3))
        unl = await page.evaluate("getComputedStyle(document.body).overflow")
        rec("body unlocked after close", unl != "hidden", unl)

        # back behaviour: / -> /discover (via hero), open drawer on /discover, Escape closes only drawer, then back -> /
        await page.evaluate("window.scrollTo(0,0)")
        await page.click('[data-testid="hero-discover-button"]')
        await page.wait_for_url("**/discover", timeout=8000)
        await page.wait_for_timeout(800)
        await open_drawer(page)
        # emulate native closeTopOverlay
        res = await page.evaluate("""() => { const has=!!document.querySelector('[role=dialog][data-state=open]'); (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:27,bubbles:true,cancelable:true})); return has }""")
        await page.wait_for_timeout(500)
        rec("closeTopOverlay emulation: dialog was detected", res)
        rec("first back(Escape) closes only drawer, URL on /discover", await page.locator('[data-testid="mobile-drawer"]').count() == 0 and page.url.endswith("/discover"), page.url)
        await page.go_back()
        await page.wait_for_timeout(1000)
        rec("second back navigates to previous route (/)", page.url.rstrip("/") == BASE, page.url)
        # drawer link navigates + closes; one back returns
        await open_drawer(page)
        await page.click('[data-testid="mobile-drawer"] [data-testid="nav-legal-guidelines"]')
        await page.wait_for_timeout(1000)
        rec("drawer link navigates to /legal/guidelines", "/legal/guidelines" in page.url, page.url)
        rec("drawer closed after link tap", await page.locator('[data-testid="mobile-drawer"]').count() == 0)
        await page.wait_for_timeout(300)
        rec("body unlocked after link nav", await page.evaluate("getComputedStyle(document.body).overflow") != "hidden")
        await page.go_back()
        await page.wait_for_timeout(1000)
        rec("one back from drawer-link page returns to /", page.url.rstrip("/") == BASE, page.url)
        await ctx.close()

        # 3. logged in drawer + logout
        ctx = await b.new_context(viewport={"width": 360, "height": 800}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await login(page)
        rec("customer logged in", "/login" not in page.url, page.url)
        await goto(page, "/discover")
        await open_drawer(page)
        acc = page.locator('[data-testid="mobile-drawer"] [data-testid="nav-account"]')
        rec("My Account link in drawer", await acc.count() == 1 and (await acc.inner_text()).strip() == "My Account")
        await drawer_geometry(page, 360, 800, "[360 auth]", logged_in=True)
        await page.screenshot(path=f"{SHOTS}/i10_drawer_auth_360.jpg", quality=40, type="jpeg")
        await page.click('[data-testid="mobile-drawer"] [data-testid="logout-button"]')
        await page.wait_for_timeout(2000)
        rec("logout lands on /", page.url.rstrip("/") == BASE, page.url)
        rec("drawer closed after logout", await page.locator('[data-testid="mobile-drawer"]').count() == 0)
        await open_drawer(page)
        rec("after logout drawer shows Log in", await page.locator('[data-testid="mobile-drawer"] [data-testid="nav-login"]').count() == 1)
        await ctx.close()

        # 4. homepage at narrow widths
        for w in [320, 360, 390, 412]:
            ctx = await b.new_context(viewport={"width": w, "height": 844}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            await goto(page, "/")
            await page.wait_for_timeout(1200)
            g = await page.evaluate("""() => { const img=document.querySelector('section img[src="/hero.jpg"]'); const sec=img.closest('section');
              const ib=img.getBoundingClientRect(), sb=sec.getBoundingClientRect(); const s=getComputedStyle(img);
              const p=[0,1,2].map(i=>document.querySelector(`[data-testid=trust-pillar-${i}]`).getBoundingClientRect().top);
              const cards=[...document.querySelectorAll('[data-testid^=astrologer-card-]')].filter(e=>!e.dataset.testid.includes('availability')).map(e=>{const r=e.getBoundingClientRect(); return [r.left,r.right]});
              return {img:[ib.top,ib.bottom,ib.left,ib.right], sec:[sb.top,sb.bottom], pillarTops:p, pos:s.position, top:s.top, left:s.left,
                sw:document.documentElement.scrollWidth, cw:document.documentElement.clientWidth, cards} }""")
            rec(f"[home {w}] hero img inside hero section", abs(g["img"][0] - g["sec"][0]) < 1 and abs(g["img"][1] - g["sec"][1]) < 1, str(g["img"]) + str(g["sec"]))
            rec(f"[home {w}] hero img doesn't overlap trust pillars", g["img"][1] <= min(g["pillarTops"]) + 0.5, f"{g['img'][1]} vs {g['pillarTops']}")
            rec(f"[home {w}] img computed top/left are 0px", g["top"] == "0px" and g["left"] == "0px", f"{g['top']} {g['left']}")
            rec(f"[home {w}] no horizontal overflow", g["sw"] <= g["cw"], f"{g['sw']}/{g['cw']}")
            rec(f"[home {w}] astrologer cards fit", len(g["cards"]) > 0 and all(l >= 0 and r <= w + 0.5 for l, r in g["cards"]), str(g["cards"]))
            pad = 20
            for t in ["hero-discover-button", "hero-join-astrologer-button"]:
                bb = await page.locator(f'[data-testid="{t}"]').bounding_box()
                rec(f"[home {w}] {t} full-width", abs(bb["width"] - (w - 2 * pad)) < 1.5, str(bb["width"]))
            if w == 320:
                await page.screenshot(path=f"{SHOTS}/i10_home_320.jpg", quality=40, type="jpeg")
            await ctx.close()

        # 5. regressions: login sheet on profile (mobile), booking dialog (logged in, mobile), desktop header
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await goto(page, f"/astrologers/{AID}")
        await page.click('[data-testid="mobile-book-bar-button"]')
        sheet = page.locator('[data-testid="login-sheet"]')
        await sheet.wait_for(timeout=5000)
        await page.wait_for_timeout(500)
        bb = await sheet.bounding_box()
        rec("[reg] login sheet anchored bottom full width", abs(bb["y"] + bb["height"] - 844) < 2 and bb["width"] >= 389 and bb["x"] < 1, str(bb))
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)
        rec("[reg] login sheet closes on Escape, URL kept", await sheet.count() == 0 and AID in page.url)
        await login(page)
        await goto(page, f"/astrologers/{AID}")
        await page.locator('[data-testid^="slot-"]').first.click()
        await page.wait_for_timeout(300)
        await page.click('[data-testid="mobile-book-bar-button"]')
        dlg = page.locator('[data-testid="booking-dialog"]')
        try:
            await dlg.wait_for(timeout=6000)
            await page.wait_for_timeout(500)
            bb = await dlg.bounding_box()
            rec("[reg] booking dialog bottom sheet anchored", abs(bb["y"] + bb["height"] - 844) < 2 and bb["width"] >= 389 and bb["x"] < 1, str(bb))
            await page.screenshot(path=f"{SHOTS}/i10_booking_390.jpg", quality=40, type="jpeg")
        except Exception as e:
            rec("[reg] booking dialog opens", False, str(e)[:120])
        await ctx.close()

        ctx = await b.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await goto(page, "/")
        rec("[desk] menu button hidden", not await page.locator('[data-testid="mobile-menu-button"]').is_visible())
        for t in ["nav-discover", "nav-legal-guidelines", "nav-login", "nav-register"]:
            rec(f"[desk] header {t} visible", await page.locator(f'header [data-testid="{t}"]').is_visible())
        await page.screenshot(path=f"{SHOTS}/i10_desktop.jpg", quality=40, type="jpeg")
        await ctx.close()
        await b.close()
    passed = sum(1 for _, ok in R if ok)
    print(f"\nRESULT {passed}/{len(R)} passed")
    for n, ok in R:
        if not ok:
            print("  FAILED:", n)


asyncio.run(main())
