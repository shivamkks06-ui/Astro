"""Captures real app screens and frames them for Play Store. Run: python3 screenshots.py <base_url>"""
import asyncio
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
RAW, OUT = ROOT / "output" / "raw", ROOT / "output" / "store"
BASE = sys.argv[1].rstrip("/")
ASTRO = "9406cb50672f439488f811596dcd39d7"
NAVY, GOLD, WHITE, MUTED = (11, 15, 25), (230, 179, 37), (248, 250, 252), (148, 163, 184)
CUSTOMER = ("demo.customer@nakshatraveda.test", "DemoPass@123")
ASTROLOGER = ("demo.astro1@nakshatraveda.test", "DemoPass@123")

# canvas size, viewport (css px), device scale
DEVICES = {
    "phone": ((1080, 1920), (360, 600), 3),
    "tablet7": ((1200, 1920), (600, 900), 2),
    "tablet10": ((1600, 2560), (800, 1200), 2),
}

SHOTS = [
    ("01_home", "Consult verified Vedic astrologers", "Interpretive guidance, never guaranteed outcomes", None, "/", None),
    ("02_discover", "Find the right astrologer", "Filter by language, expertise, experience and price", None, "/discover", None),
    ("03_profile", "Identity checks you can see", "Separate badges for identity and credentials", None, f"/astrologers/{ASTRO}", None),
    ("04_booking", "Clear price before you book", "Price, duration and refund terms shown upfront", CUSTOMER, f"/astrologers/{ASTRO}", "book"),
    ("05_account", "Your bookings, payments and privacy", "Receipts, birth profiles, data export and deletion", CUSTOMER, "/account", None),
    ("06_studio", "Astrologers: a studio to grow", "Verification, listing plans, slots and earnings", ASTROLOGER, "/studio", None),
]

CLEAN_JS = """() => {
  document.querySelectorAll('a[href*="emergent"], #emergent-badge').forEach(e => e.remove());
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) walk.currentNode.nodeValue = walk.currentNode.nodeValue.replace('[DEMO] ', '');
}"""


async def login(page, creds):
    await page.goto(f"{BASE}/login", wait_until="networkidle")
    await page.fill("[data-testid=login-email-input]", creds[0])
    await page.fill("[data-testid=login-password-input]", creds[1])
    await page.click("[data-testid=login-submit-button]")
    await page.wait_for_timeout(2500)


async def capture(pw):
    browser = await pw.chromium.launch()
    for dev, (_, vp, scale) in DEVICES.items():
        for key, _, _, creds, path, extra in SHOTS:
            ctx = await browser.new_context(viewport={"width": vp[0], "height": vp[1]}, device_scale_factor=scale)
            page = await ctx.new_page()
            if creds:
                await login(page, creds)
            await page.goto(f"{BASE}{path}", wait_until="networkidle")
            await page.wait_for_timeout(1800)
            if extra == "book":
                await page.locator("[data-testid^=slot-]").first.click()
                await page.wait_for_timeout(400)
                await page.locator("[data-testid=book-now-button]").first.click()
                await page.wait_for_timeout(1200)
            await page.evaluate(CLEAN_JS)
            await page.screenshot(path=str(RAW / f"{dev}_{key}.png"))
            await ctx.close()
            print("captured", dev, key)
    await browser.close()


def font(name, size, weight):
    f = ImageFont.truetype(str(ROOT / "fonts" / f"{name}.ttf"), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def frame(dev, key, title, sub):
    (W, H), _, _ = DEVICES[dev]
    canvas = Image.new("RGB", (W, H), NAVY)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((-W // 3, -H // 6, W + W // 3, H // 2), fill=90)
    canvas = Image.composite(Image.new("RGB", (W, H), (30, 41, 74)), canvas, glow.filter(ImageFilter.GaussianBlur(W // 5)))
    d = ImageDraw.Draw(canvas)
    pad = int(W * 0.08)
    tf, sf = font("Playfair", int(W * 0.068), 600), font("Jakarta", int(W * 0.034), 400)
    y = int(H * 0.05)
    d.text((pad, y), "NAKSHATRAVEDA", font=font("Cinzel", int(W * 0.03), 600), fill=GOLD)
    y += int(W * 0.07)
    for line in wrap(d, title, tf, W - 2 * pad):
        d.text((pad, y), line, font=tf, fill=WHITE)
        y += int(tf.size * 1.2)
    y += int(W * 0.01)
    for line in wrap(d, sub, sf, W - 2 * pad):
        d.text((pad, y), line, font=sf, fill=MUTED)
        y += int(sf.size * 1.4)
    top = y + int(H * 0.03)
    shot = Image.open(RAW / f"{dev}_{key}.png").convert("RGB")
    sw = W - 2 * pad
    sh = int(shot.height * sw / shot.width)
    avail = H - top - int(H * 0.04)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    if sh > avail:
        shot = shot.crop((0, 0, sw, avail))
        sh = avail
    r = int(W * 0.04)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw, sh), r, fill=255)
    border = Image.new("RGB", (sw + 6, sh + 6), GOLD)
    bmask = Image.new("L", border.size, 0)
    ImageDraw.Draw(bmask).rounded_rectangle((0, 0, sw + 5, sh + 5), r + 3, fill=110)
    canvas.paste(border, (pad - 3, top - 3), bmask)
    canvas.paste(shot, (pad, top), mask)
    (OUT / dev).mkdir(parents=True, exist_ok=True)
    canvas.save(OUT / dev / f"{key}.png")


async def main():
    RAW.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        await capture(pw)
    for dev in DEVICES:
        for key, title, sub, *_ in SHOTS:
            frame(dev, key, title, sub)
    print("framed")


asyncio.run(main())
