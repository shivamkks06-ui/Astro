# Iteration 8: confirm landscape login dialog clipping + profile footer hidden under sticky bar
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
AID = "9406cb50672f439488f811596dcd39d7"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        ctx = await b.new_context(viewport={"width": 844, "height": 390}, has_touch=True, is_mobile=True)
        page = await ctx.new_page()
        await page.goto(BASE + f"/astrologers/{AID}", wait_until="networkidle")
        await page.click('[data-testid="mobile-book-bar-button"]')
        sh = page.locator('[data-testid="login-sheet"]')
        await sh.wait_for()
        await page.fill('[data-testid="login-sheet-email"]', "demo.customer@nakshatraveda.test")
        await page.fill('[data-testid="login-sheet-password"]', "WrongPass@1")
        await page.click('[data-testid="login-sheet-submit"]')
        await page.locator('[data-testid="login-sheet-error"]').wait_for(timeout=6000)
        await page.wait_for_timeout(300)
        bb = await sh.bounding_box()
        st = await sh.evaluate("e=>[getComputedStyle(e).maxHeight,getComputedStyle(e).overflowY,e.scrollHeight,e.clientHeight]")
        print("landscape login with server error:", bb, st)
        reg = await page.locator('[data-testid="login-sheet-register"]').bounding_box()
        print("register link box:", reg, "visible-in-viewport:", reg["y"] + reg["height"] <= 390 and reg["y"] >= 0)
        await page.screenshot(path="/app/.screenshots/i8_landscape_login_err.jpg", quality=40, type="jpeg")
        await page.keyboard.press("Escape")
        # footer last line vs sticky bar (portrait 390)
        for vp in [(390, 844), (844, 390)]:
            await page.set_viewport_size({"width": vp[0], "height": vp[1]})
            await page.wait_for_timeout(300)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(400)
            info = await page.evaluate("""() => { const bar=document.querySelector('[data-testid=mobile-book-bar-button]').parentElement.getBoundingClientRect();
              const els=[...document.querySelectorAll('footer *')].filter(e=>e.children.length===0 && e.textContent.trim());
              return {barTop: bar.top, hidden: els.filter(e=>e.getBoundingClientRect().bottom>bar.top).map(e=>e.textContent.trim().slice(0,40))} }""")
            print(vp, "footer elements under sticky bar:", info)
        await b.close()

asyncio.run(main())
