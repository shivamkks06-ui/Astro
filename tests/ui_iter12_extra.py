# Iteration 12: verify race scenario actually issues q=A request, hero img attrs, top-center toast position
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        ctx = await b.new_context(viewport={"width": 390, "height": 844})
        page = await ctx.new_page()
        reqs = []
        page.on("request", lambda r: reqs.append(r.url) if "/api/astrologers?" in r.url else None)

        async def slow_first(route):
            if route.request.url.endswith("q=A") or "q=A&" in route.request.url:
                await asyncio.sleep(3)
            await route.continue_()
        await page.goto(BASE + "/discover", wait_until="networkidle")
        await page.route("**/api/astrologers?*", slow_first)
        reqs.clear()
        await page.click('[data-testid="filter-search"]')
        await page.keyboard.type("Ac", delay=300)
        await page.wait_for_timeout(4500)
        print("requests:", reqs)
        print("q=A fired:", any("q=A&" in u or u.endswith("q=A") for u in reqs))
        print("count:", await page.inner_text('[data-testid="results-count"]'))

        await page.goto(BASE + "/", wait_until="networkidle")
        attrs = await page.evaluate("""() => { const i=document.querySelector('img[src="/hero.jpg"]'); return i ? [i.getAttribute('width'), i.getAttribute('height'), i.naturalWidth] : null }""")
        print("hero img attrs:", attrs)

        # top-center toast via sonner: trigger by evaluating a failing login on login page
        await page.goto(BASE + "/login", wait_until="networkidle")
        try:
            await page.fill('[data-testid="login-email"]', "nobody@nakshatraveda.test")
            await page.fill('[data-testid="login-password"]', "wrongpass1")
            await page.click('[data-testid="login-submit"]')
            await page.wait_for_selector('[data-sonner-toast]', timeout=6000)
            box = await page.evaluate("""() => { const t=document.querySelector('[data-sonner-toast]').getBoundingClientRect(); const ol=document.querySelector('[data-sonner-toaster]'); return {y:t.y, bottom:t.bottom, yPos: ol.getAttribute('data-y-position')} }""")
            print("top toast:", box)
        except Exception as e:
            print("top toast check skipped:", e)
        await b.close()

asyncio.run(main())
