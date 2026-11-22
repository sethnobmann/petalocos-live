"""Build the Petalocos app page: docs/app/index.html (served by GitHub Pages at /petalocos-live/app/).

Reads league history (data/history/) plus this season's tables written by scripts/h2h.py,
computes everything, and embeds it as JSON in one page. Run after h2h.py:

    python3 scripts/h2h.py && python3 scripts/build_app.py
"""
import csv
import json
import re
from collections import defaultdict

try:
    from PIL import Image  # only for the home-screen icons, which are already made
except ImportError:
    Image = None

import datetime
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(REPO, "data", "history")
OUT = os.path.join(REPO, "docs", "app")


def rd(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fmt(n):
    return f"{n:,}"


def ordn(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


meta = json.load(open(f"{HIST}/meta.json", encoding="utf-8"))
rows = [
    {"y": int(r["Season"]), "f": int(r["Finish"]), "team": r["Team"], "mgr": r["Manager"], "pts": int(r["Points"])}
    for r in rd(f"{HIST}/standings.csv")
]
s26 = {r["Manager"]: r for r in rd(f"{REPO}/data/season_2026.csv")}
short = {m: r["Short"] for m, r in s26.items()}
short.update({"Jerre Hernandez": "Jerre"})

by_year = defaultdict(list)
for r in rows:
    by_year[r["y"]].append(r)
teams_in = {y: len(v) for y, v in by_year.items()}

# ---- seasons -------------------------------------------------------------
seasons, title_no = [], defaultdict(int)
for y in sorted(by_year):
    rs = sorted(by_year[y], key=lambda r: r["f"])
    champ, run, last = rs[0], rs[1], rs[-1]
    title_no[champ["mgr"]] += 1
    h2h = meta["h2h"].get(str(y))
    seasons.append({
        "y": y, "n": len(rs),
        "champ": {"mgr": champ["mgr"], "team": champ["team"], "pts": champ["pts"]},
        "run": {"mgr": run["mgr"], "team": run["team"], "pts": run["pts"]},
        "last": {"mgr": last["mgr"], "team": last["team"], "pts": last["pts"]},
        "nth": title_no[champ["mgr"]],
        "margin": champ["pts"] - run["pts"],
        "avg": round(sum(r["pts"] for r in rs) / len(rs), 1),
        "h2h": h2h,
        "double": h2h == champ["mgr"],
        "rows": [[r["f"], r["team"], r["mgr"], r["pts"]] for r in rs],
    })

# ---- members -------------------------------------------------------------
by_mgr = defaultdict(list)
for r in rows:
    if r["mgr"] != "Unknown":
        by_mgr[r["mgr"]].append(r)


def initials(name):
    if name.startswith("CJ "):
        return "CJ"
    p = name.split()
    return (p[0][0] + p[-1][0]).upper()


members = []
for m, rs in by_mgr.items():
    rs = sorted(rs, key=lambda r: r["y"])
    info = meta["managers"][m]
    best = max(rs, key=lambda r: r["pts"])
    worst = min(rs, key=lambda r: r["pts"])
    now = None
    if m in s26:
        t = s26[m]
        now = {"team": t["Team Name"], "place": int(t["Place"]), "pts": int(t["Points"]),
               "w": int(t["H2H W"]), "l": int(t["H2H L"])}
    members.append({
        "name": m, "slug": slug(m), "short": short.get(m, m.split()[0]), "ini": initials(m),
        "active": m in s26, "status": info["status"], "teams": info["teams"],
        "since": rs[0]["y"], "seasons": len(rs),
        "titles": [r["y"] for r in rs if r["f"] == 1],
        "h2h": sorted(int(y) for y, v in meta["h2h"].items() if v == m),
        "seconds": sum(r["f"] == 2 for r in rs),
        "top3": sum(r["f"] <= 3 for r in rs),
        "lasts": sum(r["f"] == teams_in[r["y"]] for r in rs),
        "avg": round(sum(r["f"] for r in rs) / len(rs), 1),
        "career": sum(r["pts"] for r in rs),
        "best": {"y": best["y"], "pts": best["pts"], "team": best["team"]},
        "worst": {"y": worst["y"], "pts": worst["pts"], "team": worst["team"]},
        "fin": [[r["y"], r["f"], teams_in[r["y"]], r["team"], r["pts"]] for r in rs],
        "now": now,
    })

# ---- 2026 live -----------------------------------------------------------
standings = []
for m, t in s26.items():
    standings.append({
        "team": t["Team Name"], "mgr": m, "short": t["Short"], "pts": int(t["Points"]),
        "place": int(t["Place"]), "prev": int(t["Prev Place"]),
        "w": int(t["H2H W"]), "l": int(t["H2H L"]), "streak": t["Streak"],
        "pf": int(t["PF"]), "pa": int(t["PA"]),
        "hp": int(t["H2H place"]), "hpp": int(t["H2H prev place"]), "form": t["Form"],
    })
through = max(int(t["Through Week"]) for t in s26.values())

weeks = defaultdict(list)
for r in rd(f"{REPO}/data/weeks_2026.csv"):
    weeks[int(r["Week"])].append([r["Team Name"], r["Manager"], int(r["Points"]), int(r["Week Rank"]),
                                  r["Opp"], int(r["Opp pts"]), r["Result"], int(r["Season pts"]), int(r["Place"])])
games = defaultdict(list)
for r in rd(f"{REPO}/data/games_2026.csv"):
    games[int(r["Week"])].append([r["Away"], int(r["Away pts"]), r["Home"], int(r["Home pts"]),
                                  r["Winner"], int(r["Margin"])])
nxt = [r for r in rd(f"{REPO}/data/schedule_2026.csv") if r["Is next"] == "true"]
live = {
    "through": through, "standings": standings,
    "weeks": {str(k): v for k, v in weeks.items()},
    "games": {str(k): v for k, v in games.items()},
    "next": {"week": int(nxt[0]["Week"]), "games": [[r["Away"], r["Home"]] for r in nxt]} if nxt else None,
}
try:
    cur = json.load(open(f"{REPO}/data/live_week.json", encoding="utf-8"))
    live["cur"] = {"week": cur["week"], "asOf": cur["as_of"], "teams": cur["teams"], "base": cur.get("base"), "lineups": cur.get("lineups")}
except FileNotFoundError:
    live["cur"] = None
# After a weekly roll live_week.json is a week behind: start the new week from the scraper's
# docs/live.json (team totals only, no lineups); the app keeps pulling that file on its own.
nweek = live["next"]["week"] if live["next"] else None
if nweek and (not live["cur"] or live["cur"]["week"] != nweek):
    live["cur"] = None
    try:
        lj = json.load(open(f"{REPO}/docs/live.json", encoding="utf-8"))
        if lj.get("week") == nweek:
            live["cur"] = {
                "week": nweek, "asOf": lj["updated"], "lineups": None,
                "teams": {t["team"]: [round(t["week_pts"]), round(max(t["week_proj"] or 0, t["week_pts"]))] for t in lj["teams"]},
                "base": {s["team"]: [s["pts"], s["place"]] for s in standings},
            }
    except (FileNotFoundError, KeyError, ValueError):
        pass
live["sched"] = {}
for _r in rd(f"{REPO}/data/schedule_2026.csv"):
    if nxt and int(_r["Week"]) > int(nxt[0]["Week"]):
        live["sched"].setdefault(_r["Week"], []).append([_r["Away"], _r["Home"]])

# ---- records -------------------------------------------------------------
known = [r for r in rows if r["mgr"] != "Unknown"]
b, w = max(known, key=lambda r: r["pts"]), min(known, key=lambda r: r["pts"])
big = max(seasons, key=lambda s: s["margin"])
close = min(seasons, key=lambda s: s["margin"])
wk26 = [(int(r["Points"]), r) for r in rd(f"{REPO}/data/weekly_scores_2026.csv")]
hi26 = max(wk26, key=lambda x: x[0])[1]
lo26 = min(wk26, key=lambda x: x[0])[1]
hi, lo = meta["weekRecords"]["high"], meta["weekRecords"]["low"]


def most(key, label, fmt_v=str):
    best_v = max(key(m) for m in members)
    who = [m for m in members if key(m) == best_v]
    return {"k": label, "v": fmt_v(best_v), "who": " & ".join(m["name"] for m in who),
            "ctx": f"{who[0]['seasons']} seasons" if len(who) == 1 else "tied",
            "href": f"member-{who[0]['slug']}" if len(who) == 1 else None}


ten = [m for m in members if m["seasons"] >= 10]
best_avg = min(ten, key=lambda m: m["avg"])
no_title = max((m for m in members if not m["titles"]), key=lambda m: m["seasons"])
records = {
    "season": [
        {"k": "Best season", "v": fmt(b["pts"]), "who": b["mgr"], "ctx": f"{b['team']} · {b['y']}", "href": f"season-{b['y']}"},
        {"k": "Worst season", "v": fmt(w["pts"]), "who": w["mgr"], "ctx": f"{w['team']} · {w['y']}", "href": f"season-{w['y']}"},
        {"k": "Biggest championship margin", "v": str(big["margin"]), "who": big["champ"]["mgr"], "ctx": f"over {big['run']['mgr']} · {big['y']}", "href": f"season-{big['y']}"},
        {"k": "Closest championship race", "v": str(close["margin"]), "who": close["champ"]["mgr"], "ctx": f"over {close['run']['mgr']} · {close['y']}", "href": f"season-{close['y']}"},
    ],
    "week": [
        {"k": "Highest week", "v": str(hi["value"]), "who": hi["who"], "ctx": f"{hi['team']} · Wk {hi['week']}, {hi['season']}", "href": f"season-{hi['season']}"},
        {"k": "Lowest week", "v": str(lo["value"]), "who": lo["who"], "ctx": f"{lo['team']} · Wk {lo['week']}, {lo['season']}", "href": f"season-{lo['season']}"},
        {"k": "2026 high so far", "v": hi26["Points"], "who": hi26["Manager"], "ctx": f"{hi26['Team Name']} · Wk {hi26['Week']}", "href": None},
        {"k": "2026 low so far", "v": lo26["Points"], "who": lo26["Manager"], "ctx": f"{lo26['Team Name']} · Wk {lo26['Week']}", "href": None},
    ],
    "career": [
        most(lambda m: len(m["titles"]), "Most championships"),
        most(lambda m: m["seconds"], "Most runner-ups"),
        most(lambda m: m["top3"], "Most top-3 finishes"),
        most(lambda m: m["lasts"], "Most last places"),
        {"k": "Best avg finish", "v": f"{best_avg['avg']:.1f}", "who": best_avg["name"], "ctx": "10+ seasons", "href": f"member-{best_avg['slug']}"},
        {"k": "Most seasons, no championship", "v": str(no_title["seasons"]), "who": no_title["name"], "ctx": f"{no_title['seasons']} seasons", "href": f"member-{no_title['slug']}"},
    ],
    "points": [
        {"name": m["name"], "slug": m["slug"], "seasons": m["seasons"], "career": m["career"],
         "avg": round(m["career"] / m["seasons"])}
        for m in sorted(members, key=lambda m: -m["career"])
    ],
}

data = {"seasons": seasons, "members": members, "live": live, "records": records}

# ---- icons + manifest (made once) -------------------------------------
os.makedirs(OUT, exist_ok=True)
for size in (180, 192, 512):
    path = f"{OUT}/icon-{size}.png"
    if os.path.exists(path) or Image is None:
        continue
    crest = Image.open(f"{REPO}/docs/img/crest-shield.png").convert("RGBA")
    tile = Image.new("RGBA", (size, size), (11, 20, 36, 255))
    c = crest.copy()
    c.thumbnail((int(size * 0.74), int(size * 0.74)), Image.LANCZOS)
    tile.alpha_composite(c, ((size - c.width) // 2, (size - c.height) // 2))
    tile.convert("RGB").save(path, "PNG", optimize=True)
manifest = {
    "name": "Petalocos", "short_name": "Petalocos", "start_url": "./", "scope": "./",
    "display": "standalone", "background_color": "#0B1424", "theme_color": "#0B1424",
    "icons": [{"src": f"icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png"} for s in (192, 512)],
}
with open(f"{OUT}/manifest.webmanifest", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

updated = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-8))).strftime("%b %-d")
html = open(f"{REPO}/app/template.html", encoding="utf-8").read()
html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
html = html.replace("__UPDATED__", updated)
with open(f"{OUT}/index.html", "w", encoding="utf-8") as f:
    f.write(html)

# quick sanity print
print("seasons", len(seasons), "members", len(members), "through week", through)
for m in sorted(members, key=lambda m: -m["career"])[:4]:
    print(m["name"], m["career"], len(m["titles"]), m["avg"], m["top3"], m["lasts"])
for grp in ("season", "week", "career"):
    for r in records[grp]:
        print(grp, r["k"], r["v"], r["who"], r["ctx"])
print("bytes", len(html))
