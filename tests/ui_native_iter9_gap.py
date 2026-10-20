# Iteration 9: measure empty gap between profile content and footer on mobile
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        for vw, vh in [(390, 844), (844, 390)]:
            ctx = await b.new_context(viewport={"width": vw, "height": vh}, has_touch=True, is_mobile=True)
            page = await ctx.new_page()
            await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
            g = await page.evaluate("""() => { const f=document.querySelector('footer');
              const grid=[...document.querySelectorAll('div')].find(d=>d.className.includes('lg:grid-cols-[1.4fr_1fr]'));
              const gr=grid.getBoundingClientRect(); const cs=getComputedStyle(grid);
              const last=Math.max(...[...grid.children].map(c=>c.getBoundingClientRect().bottom));
              return {gridPB: cs.paddingBottom, lastContentToFooter: f.getBoundingClientRect().top - last, gridBottomToFooter: f.getBoundingClientRect().top - gr.bottom,
                 afterFooter: [...document.querySelectorAll('footer ~ *')].map(e=>e.getAttribute('data-testid')||e.tagName)} }""")
            print(vw, vh, g)
            await ctx.close()
        await b.close()

asyncio.run(main())
