# Iteration 10: dev server CSS - inset longhand fallback present + Tailwind utilities still applied
import asyncio, glob
from playwright.async_api import async_playwright

BASE = "https://guru-astro-hub.preview.emergentagent.com"
EXE = glob.glob("/pw-browsers/chromium_headless_shell-1208/*/headless_shell")[0]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=EXE)
        page = await b.new_page(viewport={"width": 390, "height": 844})
        await page.goto(BASE + "/", wait_until="networkidle")
        r = await page.evaluate("""() => { const out={}; for (const ss of document.styleSheets) { let rules; try { rules=ss.cssRules } catch(e) { continue }
          for (const ru of rules) { if (['.inset-0','.inset-y-0','.inset-x-0','.flex'].includes(ru.selectorText)) out[ru.selectorText]=ru.cssText } }
          const raw=[...document.querySelectorAll('style')].map(s=>s.textContent).join('\\n'); const m=raw.match(/\\.inset-0\\s*\\{[^}]*\\}/);
          return {rules: out, raw: m ? m[0] : null, sheets: document.styleSheets.length} }""")
        print(r)
        ok = r["raw"] and "top" in r["raw"] and "left" in r["raw"] and ".flex" in r["rules"]
        print("PASS dev CSS fallback + tailwind" if ok else "FAIL dev CSS")
        await b.close()


asyncio.run(main())
