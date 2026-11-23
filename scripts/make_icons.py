"""Home-screen icons from the crest: the crest centered on white.

  python3 scripts/make_icons.py      # writes docs/app/icon-180.png, icon-192.png, icon-512.png

CREST_H is the crest's height as a share of the icon (0.71 = about 5% bigger than the first set).
If you change the icons, bump ?v= on the icon links in app/template.html and ICON_V in
scripts/build_app.py so phones fetch the new ones.
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREST = os.path.join(ROOT, "docs", "img", "crest-shield.png")
OUT = os.path.join(ROOT, "docs", "app")
CREST_H = 0.71
BG = (255, 255, 255)

crest = Image.open(CREST).convert("RGBA")
crest = crest.crop(crest.getbbox())
for size in (180, 192, 512):
    h = round(size * CREST_H)
    w = round(crest.width * h / crest.height)
    c = crest.resize((w, h), Image.LANCZOS)
    icon = Image.new("RGB", (size, size), BG)
    icon.paste(c, ((size - w) // 2, (size - h) // 2), c)
    icon.save(os.path.join(OUT, f"icon-{size}.png"), optimize=True)
    print(f"icon-{size}.png  crest {w}x{h}")
