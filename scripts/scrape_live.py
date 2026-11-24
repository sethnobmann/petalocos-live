"""Live scores without the Yahoo API.

Loads the league home page in the Chrome that's already signed in to Yahoo (through
chrome_save.applescript), reads the "Week Rank" table (live fantasy points + projection
per team) and the standings table, and writes docs/live.json for the live board.

Runs from launchd every 10 minutes and decides for itself whether to do anything:
  - while ESPN's public NFL scoreboard shows a game in progress, and for 30 minutes after
    the last one ends: every run (so Thanksgiving, Saturday and early London games count too)
  - if ESPN can't be reached: the usual windows (Thu night, all Sunday, Mon night)
  - otherwise 6am-11pm: one quiet look an hour, which commits only if Yahoo's numbers moved
tmp/state.json keeps the last ESPN check ("nfl") so you can see why it ran or didn't.
While games are on it also loads the 10 team pages and adds each team's starters
(points, projections, game status) to docs/live.json as "lineups", so the app's team
page shows players live (scripts/lineups.py does the parsing; --no-lineups skips it).
When the last NFL game of the week ends (ESPN shows every game final) it locks the week's
points in as finals and reruns H2H right away; when Yahoo then moves to the new week it fixes
any team a late stat change moved, and rebuilds the app for the new week.
If Yahoo moves on before that happened, it rolls last week's finals into
data/weekly_scores_2026.csv and rebuilds the Glide tables with h2h.py. The Glide import
itself is still a manual step.

  python3 scripts/scrape_live.py            # what launchd runs
  python3 scripts/scrape_live.py --force    # scrape now, whatever the clock says
  python3 scripts/scrape_live.py --force --no-push
  python3 scripts/lineups.py tmp/team_1.html   # check what a saved team page parses to
"""
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "tmp")
LEAGUE = "https://football.fantasysports.yahoo.com/f1/700759"
LIVE = os.path.join(ROOT, "docs", "live.json")
STATE = os.path.join(TMP, "state.json")
SCORES = os.path.join(ROOT, "data", "weekly_scores_2026.csv")


def log(msg):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


# ---------- when to run ----------

def in_window(now):
    """Standard NFL windows, local (Pacific) time. weekday(): Mon=0 ... Sun=6."""
    hm = now.hour * 60 + now.minute
    wd = now.weekday()
    if wd == 3 and 16 * 60 + 30 <= hm <= 22 * 60:  # Thursday night
        return True
    if wd == 6 and 6 * 60 <= hm <= 22 * 60:  # Sunday, London kick through the night game
        return True
    if wd == 0 and 16 * 60 + 30 <= hm <= 22 * 60:  # Monday night
        return True
    return False


ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"


def nfl_games():
    """This NFL week's games as [(kickoff, state)] from ESPN's public scoreboard, state being
    "pre", "in" or "post". None if it can't be read, and the old fixed windows take over."""
    import urllib.request
    try:
        req = urllib.request.Request(ESPN, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            j = json.load(r)
        return [(datetime.fromisoformat(ev["date"].replace("Z", "+00:00")),
                 ((ev.get("status") or {}).get("type") or {}).get("state"))
                for ev in j.get("events", [])]
    except Exception:
        return None


def should_run(now, state, games=None):
    """Scrape only while an NFL game is being played (ESPN says so), plus half an hour after the
    last one ends for late stat changes. Outside that, one quiet look an hour, which only
    commits if Yahoo's numbers moved (a stat correction, or the new week)."""
    games = nfl_games() if games is None else games
    if games is not None:
        on = sum(1 for _, st in games if st == "in")
        state["nfl"] = f"{now:%m-%d %H:%M} {on} on, {sum(1 for _, st in games if st == 'pre')} to come"
        if on:
            state["game_on"] = now.timestamp()
            state["week_over"] = False
            return "game on"
        if state.get("game_on") and now.timestamp() - state["game_on"] < 30 * 60:
            return "wrap-up"
        # every game of the NFL week has been played (Monday night is done): finalize once
        state["week_over"] = bool(games) and all(st == "post" for _, st in games)
        if state["week_over"] and state.get("sig") and state.get("final_week") != state["sig"][0]:
            return "week over"
    elif in_window(now):  # ESPN unreachable: fall back to the usual kickoff windows
        state["nfl"] = f"{now:%m-%d %H:%M} ESPN unreachable, using fixed windows"
        return "window"
    if 6 <= now.hour <= 22 and now.minute < 10:
        return "hourly probe"
    return None


# ---------- page -> numbers ----------

class Tables(HTMLParser):
    """Every <table> as a list of rows, each row a list of cell text."""

    def __init__(self):
        super().__init__()
        self.tables, self.row, self.cell, self.depth = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.depth += 1
            self.tables.append([])
        elif tag == "tr" and self.depth:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "sup" and self.cell is not None:
            self.cell.append("\x00")  # marks the "1st / 2nd" place chip after a team name

    def handle_endtag(self, tag):
        if tag == "table" and self.depth:
            self.depth -= 1
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.tables:
            self.tables[-1].append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def num(s):
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_league(html):
    m = re.search(r"selected\s*>\s*Week (\d+)<", html)
    if not m:
        raise ValueError("no current week on the page (signed out, or Yahoo changed the layout)")
    week = int(m.group(1))
    p = Tables()
    p.feed(html)
    live, totals, change = {}, {}, {}
    for t in p.tables:
        if not t:
            continue
        head = t[0]
        if "Week Rank" in head and "Fantasy Points" in head:
            ti, pi, fi = head.index("Team"), head.index("Projected Points"), head.index("Fantasy Points")
            for r in t[1:]:
                if len(r) <= fi:
                    continue
                # "Umbertos 1\x00st": drop the place chip that trails the name
                team = re.sub(r"\s*\d+\s*\x00.*$", "", r[ti]).strip()
                live[team] = (num(r[fi]) or 0.0, num(r[pi]))
        elif "Team" in head and "Points" in head and "Pts Back" in head:
            ti, pi = head.index("Team"), head.index("Points")
            ci = head.index("Pts Change") if "Pts Change" in head else None
            for r in t[1:]:
                if len(r) <= pi:
                    continue
                team = r[ti].replace("\x00", "").strip()
                totals[team] = num(r[pi])
                if ci is not None:
                    change[team] = num(r[ci])
    if len(live) != 10:
        raise ValueError(f"expected 10 teams in the Week Rank table, got {len(live)}")
    return week, live, totals, change


# ---------- data ----------

def load_csv(name):
    with open(os.path.join(ROOT, "data", name), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def season_before(week):
    """Each team's total from the rolled weeks before `week`, and the last rolled week."""
    tot, last = {}, 0
    for r in load_csv("weekly_scores_2026.csv"):
        w = int(r["Week"])
        last = max(last, w)
        if w < week:
            tot[r["Team Name"]] = tot.get(r["Team Name"], 0) + int(r["Points"])
    return tot, last


def rank(items, key):
    out, ordered = {}, sorted(items, key=lambda x: -x[key])
    for i, it in enumerate(ordered):
        if i and it[key] == ordered[i - 1][key]:
            out[it["team"]] = out[ordered[i - 1]["team"]]
        else:
            out[it["team"]] = i + 1
    return out


def try_roll(week, live, totals, change):
    """Yahoo is on `week` but the file stops at week-2: work out week-1's finals.

    Final = Yahoo season total - this week's live points - what the file already has.
    It only rolls when that matches Yahoo's own "Pts Change" column for every team.
    """
    have, last = season_before(week)
    if last != week - 2:
        return f"file stops at week {last}, Yahoo is on week {week}: more than one week behind, roll by hand"
    final = {}
    for team, (pts, _) in live.items():
        if totals.get(team) is None:
            return f"no season total for {team}"
        f = totals[team] - pts - have.get(team, 0)
        if change.get(team) is not None and abs(change[team] - f) > 0.01:
            return f"{team}: computed week {week - 1} = {f:g} but Yahoo shows {change[team]:g}"
        if f < 0 or f > 400:
            return f"{team}: week {week - 1} = {f:g} looks wrong"
        final[team] = f
    from add_week import add_week

    add_week(week - 1, final)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "h2h.py")], check=True,
                   stdout=subprocess.DEVNULL)
    return None


def finalize(week, live):
    """Every NFL game of the week has been played: lock this week's points in as finals and rerun
    H2H, without waiting for Yahoo to move to the next week. Stat changes Yahoo makes later are
    picked up by reconcile() when it does move."""
    pts = {team: p for team, (p, _) in live.items()}
    if len(pts) != 10 or any(p is None or p < 0 or p > 400 for p in pts.values()):
        return f"week {week} points look wrong: {pts}"
    from add_week import add_week

    if not add_week(week, pts):
        return f"week {week} is already in the file"
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "h2h.py")], check=True, stdout=subprocess.DEVNULL)
    return None


def reconcile(week, live, totals, change):
    """Yahoo just moved to `week` and week-1 was finalized early: compare it with Yahoo's own final
    (season total - this week's points - the weeks before) and fix any team a stat change moved."""
    path = os.path.join(ROOT, "data", "weekly_scores_2026.csv")
    rows = load_csv("weekly_scores_2026.csv")
    before = {}
    for r in rows:
        if int(r["Week"]) < week - 1:
            before[r["Team Name"]] = before.get(r["Team Name"], 0) + int(r["Points"])
    mine = {r["Team Name"]: int(r["Points"]) for r in rows if int(r["Week"]) == week - 1}
    fixes = {}
    for team, (pts, _) in live.items():
        if totals.get(team) is None or team not in mine:
            return None
        f = totals[team] - pts - before.get(team, 0)
        if change.get(team) is not None and abs(change[team] - f) > 0.01:
            return None  # Yahoo's numbers don't agree with each other yet; try again next run
        if abs(f - mine[team]) > 0.01:
            fixes[team] = f
    if not fixes:
        return None
    pts = {**mine, **fixes}
    order = sorted(pts.items(), key=lambda kv: -kv[1])
    rank, prev = {}, None
    for i, (team, p) in enumerate(order):
        rank[team] = rank[prev] if prev is not None and p == pts[prev] else i + 1
        prev = team
    raw = open(path, "rb").read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rdr = csv.reader(f)
        head = next(rdr)
        body = [r for r in rdr if r]
    wi, ti, pi, ri = head.index("Week"), head.index("Team Name"), head.index("Points"), head.index("Week Rank")
    for r in body:
        if int(r[wi]) == week - 1:
            r[pi], r[ri] = str(round(pts[r[ti]])), str(rank[r[ti]])
    with open(path, "w", newline="", encoding="utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8") as f:
        csv.writer(f, lineterminator=nl).writerows([head] + body)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "h2h.py")], check=True, stdout=subprocess.DEVNULL)
    return ", ".join(f"{t} {mine[t]}→{round(v)}" for t, v in fixes.items())


def build(week, live, note=None):
    managers = {r["team"]: r["manager"] for r in load_csv("managers.csv")}
    before, last = season_before(week)
    teams = []
    for name, (pts, proj) in live.items():
        teams.append({
            "team": name,
            "manager": managers.get(name, "?"),
            "week_pts": round(pts, 2),
            "week_proj": None if proj is None else round(proj, 2),
            "season_pts": round(before.get(name, 0) + pts, 2),
        })
    wr, sr = rank(teams, "week_pts"), rank(teams, "season_pts")
    for t in teams:
        t["week_rank"], t["season_rank"] = wr[t["team"]], sr[t["team"]]
    teams.sort(key=lambda t: (t["week_rank"], t["team"]))
    by = {t["team"]: t for t in teams}
    matchups = []
    for m in load_csv("h2h_schedule.csv"):
        if int(m["week"]) != week:
            continue
        h, a = by.get(m["home"]), by.get(m["away"])
        matchups.append({
            "home": m["home"], "away": m["away"],
            "home_manager": h["manager"] if h else "?", "away_manager": a["manager"] if a else "?",
            "home_pts": h["week_pts"] if h else None, "away_pts": a["week_pts"] if a else None,
            "home_proj": h["week_proj"] if h else None, "away_proj": a["week_proj"] if a else None,
        })
    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "league": "Petalocos", "season": "2026", "week": week,
        "teams": teams, "matchups": matchups,
        "unmapped_teams": [t["team"] for t in teams if t["manager"] == "?"],
        "source": "yahoo site",
    }
    if last < week - 1:
        out["note"] = note or f"Season totals are missing week {week - 1}."
    return out


# ---------- chrome + git ----------

def fetch_page(url=LEAGUE, name="league.html"):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, name)
    if os.path.exists(out):
        os.remove(out)
    r = subprocess.run(["/usr/bin/osascript", os.path.join(ROOT, "scripts", "chrome_save.applescript"), url, out],
                       capture_output=True, text=True, timeout=90)
    final = r.stdout.strip()
    if r.returncode != 0:
        raise RuntimeError(f"Chrome: {r.stderr.strip()[:300]}")
    if "/f1/700759" not in final:
        raise RuntimeError(f"Chrome landed on {final.split('?')[0][:80]} (signed out of Yahoo, or no Chrome window)")
    for _ in range(20):  # Chrome writes the file a beat after the save call returns
        if os.path.exists(out) and os.path.getsize(out) > 100000:
            break
        subprocess.run(["/bin/sleep", "0.5"])
    with open(out, encoding="utf-8", errors="ignore") as f:
        return f.read()


def fetch_lineups(week, league_html, names):
    """{team: starters} from the 10 team pages, loaded one after another in the same Chrome tab."""
    import lineups as L
    ids = L.team_ids(league_html, names)
    if len(ids) != len(names):
        raise ValueError(f"found team links for {len(ids)} of {len(names)} teams")
    out = {}
    for team, tid in sorted(ids.items(), key=lambda kv: kv[1]):
        rows = L.parse_team(fetch_page(f"{LEAGUE}/{tid}?week={week}", f"team_{tid}.html"))
        if not rows:
            raise ValueError(f"no starters on {team}'s page")
        out[team] = rows
    return out


def git(*args):
    return subprocess.run(["/usr/bin/git", "-C", ROOT, *args], capture_output=True, text=True)


def push(paths, msg):
    git("add", *paths)
    if git("diff", "--cached", "--quiet").returncode == 0:
        return "nothing to commit"
    c = git("-c", "user.name=petalocos-bot", "-c", "user.email=bot@users.noreply.github.com", "commit", "-q", "-m", msg)
    if c.returncode:
        return f"commit failed: {c.stderr.strip()[:200]}"
    p = git("push", "-q")
    if p.returncode:
        git("pull", "-q", "--rebase")
        p = git("push", "-q")
    return "pushed" if p.returncode == 0 else f"push failed: {p.stderr.strip()[:200]}"


def main():
    force, no_push, no_lineups = "--force" in sys.argv, "--no-push" in sys.argv, "--no-lineups" in sys.argv
    flag = os.path.join(TMP, "force")  # touch tmp/force, then launchctl kickstart: one forced run under launchd
    if os.path.exists(flag):
        os.remove(flag)
        force = True
    state = {}
    if os.path.exists(STATE):
        with open(STATE) as f:
            state = json.load(f)
    now = datetime.now()
    why = "forced" if force else should_run(now, state)
    if not why:
        with open(STATE, "w") as f:  # keeps the last ESPN check visible in tmp/state.json
            json.dump(state, f)
        return
    # start from GitHub's latest, so a rebuild here never uses an older copy of the app
    if not git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        git("pull", "-q", "--rebase")
    try:
        league_html = fetch_page()
        week, live, totals, change = parse_league(league_html)
    except Exception as e:  # leave the board as it was; the log says why
        log(f"FAILED ({why}): {e}")
        state["last_error"] = f"{now:%Y-%m-%d %H:%M} {e}"
        with open(STATE, "w") as f:
            json.dump(state, f)
        sys.exit(1)

    paths, note, rolled = ["docs/live.json"], None, False
    new_week = bool(state.get("sig")) and state["sig"][0] != week
    _, last = season_before(week)
    if last < week - 1:
        note = try_roll(week, live, totals, change)
        if note is None:
            rolled = True
            paths.append("data")
            log(f"rolled week {week - 1} into weekly_scores_2026.csv (Glide import still to do)")
        else:
            log(f"roll skipped: {note}")
    elif last == week - 1 and new_week:
        fixed = reconcile(week, live, totals, change)  # Yahoo's final for last week, after stat changes
        if fixed:
            rolled = True
            paths.append("data")
            log(f"week {week - 1} stat changes: {fixed}")
    elif last == week - 1 and state.get("week_over") and state.get("final_week") != week:
        note = finalize(week, live)  # Monday night is over: lock the week in and update H2H now
        if note is None:
            rolled = True
            paths.append("data")
            state["final_week"] = week
            log(f"finalized week {week} after the last game")
        else:
            log(f"finalize skipped: {note}")
    if season_before(week + 1)[1] >= week:  # this week is already in the file, by hand or above
        state["final_week"] = week

    out = build(week, live, note)
    if why != "hourly probe" and not no_lineups:
        try:  # players are a bonus: if a team page won't load or parse, the totals still go out
            out["lineups"] = fetch_lineups(week, league_html, set(live))
            out["lineups_updated"] = out["updated"]
        except Exception as e:
            log(f"lineups skipped: {e}")
    sig = [week] + [[t["team"], t["week_pts"]] for t in out["teams"]]  # lists, so it matches after a trip through JSON
    moved = sig != state.get("sig")
    if moved:
        state["sig"], state["last_change"] = sig, now.timestamp()
    state.pop("last_error", None)
    state["last_ok"] = f"{now:%Y-%m-%d %H:%M}"
    # A quiet hourly probe doesn't need a commit; a window run does, so the board's clock moves.
    write = moved or rolled or why != "hourly probe"
    if write:
        with open(LIVE, "w") as f:
            json.dump(out, f, indent=1)
    with open(STATE, "w") as f:
        json.dump(state, f)
    if rolled or new_week:  # rebuild the web app so standings, H2H and the bracket take in the finals, or the new week
        b = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_app.py")], capture_output=True, text=True)
        if b.returncode == 0:
            paths.append("docs/app")
        else:
            log(f"app rebuild failed: {b.stderr.strip()[-200:]}")
    res = "not written" if not write else "not pushed" if no_push else push(paths, f"live: week {week} {now:%m-%d %H:%M}")
    top = out["teams"][0]
    log(f"ok ({why}) week {week}, leader {top['team']} {top['week_pts']:g}, moved={moved}, {res}")


if __name__ == "__main__":
    main()
