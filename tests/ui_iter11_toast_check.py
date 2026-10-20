# Iteration 11: exit-hint toast placement vs bottom nav after animation settles
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        for w, h in [(360, 780), (390, 844)]:
            ctx = await b.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
            page = await ctx.new_page()
            await page.goto(BASE + "/", wait_until="networkidle")
            await page.wait_for_function("typeof window.__nvBack === 'function'")
            print(w, await page.evaluate("window.__nvBack()"))
            await page.wait_for_timeout(600)
            info = await page.evaluate("""() => {
              const t = document.querySelector('[data-sonner-toast]');
              const nav = document.querySelector('[data-testid="bottom-nav"]');
              const r = t && t.getBoundingClientRect(); const n = nav.getBoundingClientRect();
              const top = t && document.elementFromPoint(r.x + r.width/2, r.y + r.height/2);
              return {toast: r && {y: r.y, bottom: r.bottom, h: r.height, x: r.x, w: r.width}, nav: {y: n.y, bottom: n.bottom},
                      ol: t && t.closest('[data-sonner-toaster]')?.getAttribute('data-y-position'),
                      topEl: top && (top.closest('[data-sonner-toast]') ? 'toast' : top.outerHTML.slice(0, 80))};
            }""")
            print(w, info)
            await page.screenshot(path=f"/app/.screenshots/i11_toast_{w}.jpeg", quality=40)
            await ctx.close()
        await b.close()

asyncio.run(main())
