# Iteration 5: responsive overflow / touch target audit across mobile widths + desktop
import asyncio, os, json, requests
from playwright.async_api import async_playwright

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
WIDTHS = [(320, 844), (360, 844), (375, 844), (390, 844), (412, 844), (430, 844), (1920, 800)]
CUST = ("demo.customer@nakshatraveda.test", "DemoPass@123")
ASTRO = ("demo.astro1@nakshatraveda.test", "DemoPass@123")

OVERFLOW_JS = """() => {
  const vw = document.documentElement.clientWidth;
  const bad = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed') return;
    if (r.right > vw + 1 || r.left < -1) {
      let p = el.parentElement, clipped = false;
      while (p) { const s = getComputedStyle(p); if (/(hidden|auto|scroll|clip)/.test(s.overflowX)) { const pr = p.getBoundingClientRect(); if (pr.right <= vw + 1) { clipped = true; break; } } p = p.parentElement; }
      if (!clipped) bad.push((el.getAttribute('data-testid') || el.tagName) + ':' + Math.round(r.left) + '-' + Math.round(r.right));
    }
  });
  return {sw: document.documentElement.scrollWidth, vw, bad: bad.slice(0, 6)};
}"""

SMALL_JS = """() => {
  const out = [];
  document.querySelectorAll('button, a, input, [role=combobox]').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    if (el.closest('footer') || el.closest('p') || el.closest('label')) return;
    if (r.height < 40) out.push((el.getAttribute('data-testid') || el.tagName + ':' + (el.textContent||'').trim().slice(0,20)) + '=' + Math.round(r.height));
  });
  return [...new Set(out)].slice(0, 12);
}"""


def booking_id():
    s = requests.Session()
    s.post(f"{BASE}/api/auth/login", json={"email": CUST[0], "password": CUST[1]})
    r = s.get(f"{BASE}/api/me/bookings").json() if s.get(f"{BASE}/api/me/bookings").ok else None
    items = r.get("items", r) if isinstance(r, dict) else (r or [])
    return items[0]["id"] if items else None


async def login(page, cred):
    await page.goto(f"{BASE}/login")
    await page.fill('[data-testid="login-email-input"]', cred[0])
    await page.fill('[data-testid="login-password-input"]', cred[1])
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)


async def main():
    astros = requests.get(f"{BASE}/api/astrologers").json()["items"]
    aid = astros[0]["id"]
    print("next_slot_at present:", all("next_slot_at" in a for a in astros), [a["next_slot_at"] for a in astros][:4])
    bid = booking_id()
    print("booking id", bid)
    pub = ["/", "/discover", f"/astrologers/{aid}", "/login", "/register", "/legal/terms"]
    results = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, h in WIDTHS:
            for role, cred, paths in [("anon", None, pub), ("cust", CUST, ["/account"] + ([f"/bookings/{bid}"] if bid else [])), ("astro", ASTRO, ["/studio"])]:
                ctx = await b.new_context(viewport={"width": w, "height": h})
                page = await ctx.new_page()
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                if cred:
                    await login(page, cred)
                for path in paths:
                    await page.goto(BASE + path)
                    await page.wait_for_timeout(1800)
                    o = await page.evaluate(OVERFLOW_JS)
                    key = f"{w} {path}"
                    small = await page.evaluate(SMALL_JS) if w < 768 else []
                    extra = {}
                    if path == "/" and w < 768:
                        extra["h1"] = await page.evaluate("getComputedStyle(document.querySelector('h1')).fontSize")
                        for t in ["hero-discover-button", "hero-join-astrologer-button", "mobile-menu-button"]:
                            bb = await page.locator(f'[data-testid="{t}"]').bounding_box()
                            extra[t] = (round(bb["width"]), round(bb["height"]))
                        for i in range(3):
                            bb = await page.locator(f'[data-testid="trust-pillar-{i}"]').bounding_box()
                            extra[f"pillar{i}"] = (round(bb["x"]), round(bb["x"] + bb["width"]))
                    if path == "/" and w in (320, 390, 1920):
                        await page.screenshot(path=f"/app/tests/shots/home_{w}.jpg", quality=40, type="jpeg")
                    if path.startswith("/astrologers") and w in (320,):
                        await page.screenshot(path=f"/app/tests/shots/profile_{w}.jpg", quality=40, type="jpeg", full_page=True)
                    if path == "/discover" and w in (320,):
                        await page.screenshot(path=f"/app/tests/shots/discover_{w}.jpg", quality=40, type="jpeg")
                    if path.startswith("/bookings") and w == 320:
                        await page.screenshot(path=f"/app/tests/shots/booking_{w}.jpg", quality=40, type="jpeg", full_page=True)
                    if path == "/studio" and w == 320:
                        await page.screenshot(path=f"/app/tests/shots/studio_{w}.jpg", quality=40, type="jpeg")
                    flag = "OK" if o["sw"] == w and not o["bad"] else "OVERFLOW"
                    print(key, flag, o, "small:", small, extra)
                if errs:
                    print("PAGE ERRORS", w, role, errs[:3])
                await ctx.close()
        await b.close()

os.makedirs("/app/tests/shots", exist_ok=True)
asyncio.run(main())
