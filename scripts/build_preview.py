"""Build the review copy of the app for the Petalocos artifact on claude.ai.

The artifact is where Seth comments on the app. It is made from the same page as the
GitHub app (docs/app/index.html), with the crest inlined (an artifact can't load files)
and a "review copy" footer. It can't reach docs/live.json, so its live numbers stop at the
last build. Run after build_app.py:

    python3 scripts/h2h.py && python3 scripts/build_app.py && python3 scripts/build_preview.py

Writes tmp/preview.html (not committed); publish that file to the artifact.
"""
import base64
import io
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "docs", "app", "index.html")
OUT = os.path.join(REPO, "tmp", "preview.html")

html = open(SRC, encoding="utf-8").read()

png = open(os.path.join(REPO, "docs", "img", "crest-shield.png"), "rb").read()
try:
    from PIL import Image

    im = Image.open(io.BytesIO(png)).convert("RGBA")
    im.thumbnail((144, 144), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    png = buf.getvalue()
except ImportError:
    pass
crest = "data:image/png;base64," + base64.b64encode(png).decode()

reps = [
    ('"../img/crest-shield.png?v=3"', f'"{crest}"'),
    ('<link rel="manifest" href="manifest.webmanifest">\n', ""),
    ('<link rel="apple-touch-icon" href="icon-180.png?v=3">\n', ""),
    ('<link rel="icon" type="image/png" href="icon-192.png?v=3">\n', ""),
    ("Updated through week ${L.through} · ", "Review copy · updated through week ${L.through} · "),
]
for old, new in reps:
    assert html.count(old) == 1, old[:50]
    html = html.replace(old, new)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", OUT, len(html), "bytes")
