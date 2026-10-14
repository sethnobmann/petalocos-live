"""Pull live week scores from Yahoo and write docs/live.json.

Season totals are the sum of every week's team points, so they are right even
mid-game (Yahoo's own standings only roll the next morning).
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from yahoo import Yahoo, league_settings, week_points  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_csv(name):
    with open(os.path.join(ROOT, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def rank(items, key):
    """1224-style ranking: ties share a rank."""
    out = {}
    ordered = sorted(items, key=lambda x: -x[key])
    for i, it in enumerate(ordered):
        if i and it[key] == ordered[i - 1][key]:
            out[it["team"]] = out[ordered[i - 1]["team"]]
        else:
            out[it["team"]] = i + 1
    return out


def main():
    y = Yahoo()
    s = league_settings(y)
    cur = s["current_week"]
    managers = {r["team"]: r["manager"] for r in load_csv("managers.csv")}
    schedule = [r for r in load_csv("h2h_schedule.csv") if int(r["week"]) == cur]

    weeks = {}
    for w in range(s["start_week"], cur + 1):
        weeks[w] = week_points(y, w)

    live = weeks[cur]
    teams = []
    for name, (pts, proj) in live.items():
        season = sum(weeks[w].get(name, (0, None))[0] for w in weeks)
        teams.append(
            {
                "team": name,
                "manager": managers.get(name, "?"),
                "week_pts": round(pts, 2),
                "week_proj": None if proj is None else round(proj, 2),
                "season_pts": round(season, 2),
            }
        )
    wr = rank(teams, "week_pts")
    sr = rank(teams, "season_pts")
    for t in teams:
        t["week_rank"] = wr[t["team"]]
        t["season_rank"] = sr[t["team"]]
    teams.sort(key=lambda t: t["week_rank"])

    by_team = {t["team"]: t for t in teams}
    matchups = []
    for m in schedule:
        h, a = by_team.get(m["home"]), by_team.get(m["away"])
        matchups.append(
            {
                "home": m["home"],
                "away": m["away"],
                "home_manager": h["manager"] if h else "?",
                "away_manager": a["manager"] if a else "?",
                "home_pts": h["week_pts"] if h else None,
                "away_pts": a["week_pts"] if a else None,
                "home_proj": h["week_proj"] if h else None,
                "away_proj": a["week_proj"] if a else None,
            }
        )

    unmapped = [t["team"] for t in teams if t["manager"] == "?"]
    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "league": s["name"],
        "season": s["season"],
        "week": cur,
        "teams": teams,
        "matchups": matchups,
        "unmapped_teams": unmapped,
    }
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    with open(os.path.join(ROOT, "docs", "live.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"week {cur}: {len(teams)} teams, {len(matchups)} matchups, unmapped={unmapped}")


if __name__ == "__main__":
    main()
