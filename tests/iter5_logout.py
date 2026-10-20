# Iteration 5: logout landing route desktop vs mobile, from /account and /
import asyncio
from playwright.async_api import async_playwright

BASE = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()


async def run(b, w, start, mobile):
    ctx = await b.new_context(viewport={"width": w, "height": 844})
    page = await ctx.new_page()
    await page.goto(f"{BASE}/login")
    await page.fill('[data-testid="login-email-input"]', "demo.customer@nakshatraveda.test")
    await page.fill('[data-testid="login-password-input"]', "DemoPass@123")
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_timeout(2500)
    await page.goto(BASE + start)
    await page.wait_for_timeout(1500)
    if mobile:
        await page.click('[data-testid="mobile-menu-button"]')
        await page.wait_for_timeout(500)
        await page.click('[role=dialog] [data-testid="logout-button"]')
    else:
        await page.click('[data-testid="logout-button"]')
    await page.wait_for_timeout(2000)
    print(w, start, "->", page.url.replace(BASE, ""), "history len", await page.evaluate("history.length"))
    await ctx.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await run(b, 1920, "/account", False)
        await run(b, 390, "/account", True)
        await run(b, 390, "/discover", True)
        await b.close()

asyncio.run(main())
