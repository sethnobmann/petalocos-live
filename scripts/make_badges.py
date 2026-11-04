"""Render rank badge + move arrow PNGs for the Home standings list.

docs/img/rk/{place}-{code}.png, place 1-10, code s | u1..u9 | d1..d9.
96x140 transparent: 84px rounded square (orange for 1st) with the place
in Share Tech Mono, arrow line under it in green/red. Needs the font at
scripts/fonts/ShareTechMono.ttf.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "img", "rk")
FONT = os.path.join(ROOT, "scripts", "fonts", "ShareTechMono.ttf")
os.makedirs(OUT, exist_ok=True)
big = ImageFont.truetype(FONT, 46)
small = ImageFont.truetype(FONT, 24)
W, H, S = 96, 140, 84


def badge(place, code):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = (W - S) // 2
    if place == 1:
        bg, fg = (242, 92, 42, 255), (10, 10, 10, 255)
    else:
        bg, fg = (27, 43, 72, 255), (174, 184, 204, 255)
    d.rounded_rectangle([x0, 0, x0 + S, S], radius=18, fill=bg)
    t = str(place)
    bb = d.textbbox((0, 0), t, font=big)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], (S - (bb[3] - bb[1])) / 2 - bb[1]), t, font=big, fill=fg)
    y = S + 14
    if code == "s":
        d.rectangle([W / 2 - 9, y + 9, W / 2 + 9, y + 12], fill=(107, 113, 122, 255))
        im.save(os.path.join(OUT, f"{place}-{code}.png"))
        return
    up = code[0] == "u"
    col = (76, 211, 123, 255) if up else (255, 92, 92, 255)
    n = code[1:]
    bb = d.textbbox((0, 0), n, font=small)
    tw = bb[2] - bb[0]
    total = 16 + 4 + tw
    x = (W - total) / 2
    if up:
        d.polygon([(x, y + 18), (x + 16, y + 18), (x + 8, y + 3)], fill=col)
    else:
        d.polygon([(x, y + 3), (x + 16, y + 3), (x + 8, y + 18)], fill=col)
    d.text((x + 20 - bb[0], y + 10 - (bb[3] - bb[1]) / 2 - bb[1]), n, font=small, fill=col)
    im.save(os.path.join(OUT, f"{place}-{code}.png"))


codes = ["s"] + [f"u{i}" for i in range(1, 10)] + [f"d{i}" for i in range(1, 10)]
for p in range(1, 11):
    for c in codes:
        badge(p, c)
print("wrote", 10 * len(codes), "badges to", OUT)
