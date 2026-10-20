"""Builds icon, splash and feature graphic from the generated artwork. Run: python3 build_assets.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent
SRC, OUT = ROOT / "src", ROOT / "output"
APP_ASSETS = ROOT.parent / "frontend" / "assets"
NAVY, GOLD, MUTED = (11, 15, 25), (230, 179, 37), (203, 213, 225)
for d in (OUT / "store", APP_ASSETS):
    d.mkdir(parents=True, exist_ok=True)


def font(name, size, weight=None):
    f = ImageFont.truetype(str(ROOT / "fonts" / f"{name}.ttf"), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def radial_bg(w, h, inner=(22, 34, 66)):
    bg = Image.new("RGB", (w, h), NAVY)
    glow = Image.new("L", (w, h), 0)
    r = int(min(w, h) * 0.42)
    ImageDraw.Draw(glow).ellipse((w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r), fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(r // 2))
    return Image.composite(Image.new("RGB", (w, h), inner), bg, glow)


def mandala():
    """Circular mandala cut from the generated icon (drops its white rounded corners)."""
    im = Image.open(SRC / "icon_full.jpg").convert("RGB").resize((1024, 1024))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse((52, 52, 972, 972), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(6))
    out = im.copy()
    out.putalpha(mask)
    return out


def place(canvas, art, size, center):
    a = art.resize((size, size), Image.LANCZOS)
    canvas.paste(a, (center[0] - size // 2, center[1] - size // 2), a)


def centered(draw, text, y, f, fill, width):
    w = draw.textlength(text, font=f)
    draw.text(((width - w) / 2, y), text, font=f, fill=fill)


m = mandala()

# app icon (full-bleed square; Android/Play apply their own mask)
icon = radial_bg(1024, 1024)
place(icon, m, 980, (512, 512))
icon.save(APP_ASSETS / "icon-only.png")
icon.resize((512, 512), Image.LANCZOS).save(OUT / "store" / "play-icon-512.png")

# adaptive icon layers: foreground kept inside the 66% safe zone
fg = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
place(fg, m, 700, (512, 512))
fg.save(APP_ASSETS / "icon-foreground.png")
radial_bg(1024, 1024).save(APP_ASSETS / "icon-background.png")

# splash (2732 square; Capacitor crops it per screen, so content stays central)
for name in ("splash.png", "splash-dark.png"):
    s = radial_bg(2732, 2732)
    place(s, m, 820, (1366, 1220))
    d = ImageDraw.Draw(s)
    centered(d, "NAKSHATRAVEDA", 1700, font("Cinzel", 120, 600), GOLD, 2732)
    centered(d, "Verified Vedic astrologers", 1860, font("Jakarta", 56, 400), MUTED, 2732)
    s.save(APP_ASSETS / name)

# feature graphic 1024x500
art = Image.open(SRC / "feature_art.jpg").convert("RGB")
w, h = art.size
ch = int(w * 500 / 1024)
art = art.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch)).resize((1024, 500), Image.LANCZOS)
shade = Image.linear_gradient("L").rotate(90).resize((1024, 500))
art = Image.composite(art, Image.new("RGB", (1024, 500), NAVY), shade.point(lambda v: min(255, v + 60)))
d = ImageDraw.Draw(art)
d.text((56, 150), "NAKSHATRAVEDA", font=font("Cinzel", 58, 700), fill=GOLD)
d.text((58, 240), "Consult verified Vedic astrologers", font=font("Playfair", 34, 500), fill=(248, 250, 252))
d.text((58, 296), "Clear per-minute prices  ·  Identity-checked  ·  Private", font=font("Jakarta", 22, 400), fill=MUTED)
art.save(OUT / "store" / "feature-graphic-1024x500.png")
print("assets built")
