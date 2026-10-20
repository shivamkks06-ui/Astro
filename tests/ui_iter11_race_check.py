# Iteration 11: Discover stale-response race (out-of-order API responses while typing)
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        ctx = await b.new_context(viewport={"width": 390, "height": 844})
        page = await ctx.new_page()

        async def slow_first(route):
            if route.request.url.endswith("q=A") or "q=A&" in route.request.url:
                await asyncio.sleep(3)
            await route.continue_()
        await page.goto(BASE + "/discover", wait_until="networkidle")
        await page.route("**/api/astrologers?*", slow_first)
        await page.click('[data-testid="filter-search"]')
        await page.keyboard.type("Ac", delay=300)  # "P" matches 2 (Pandita + Iyer? ), "Pa" matches Pandita only
        await page.wait_for_timeout(4500)
        print("input:", await page.input_value('[data-testid="filter-search"]'), "url:", page.url)
        print("count:", await page.inner_text('[data-testid="results-count"]'))
        api = await page.evaluate("fetch('/api/astrologers?q=Ac').then(r=>r.json()).then(d=>d.total)")
        api_p = await page.evaluate("fetch('/api/astrologers?q=A').then(r=>r.json()).then(d=>d.total)")
        print("server total q=Ac:", api, "q=A:", api_p)
        await b.close()

asyncio.run(main())
