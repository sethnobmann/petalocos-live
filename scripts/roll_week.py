"""Tuesday roll: append last week's final scores to data/weekly_scores_2026.csv.

Rows match the Glide Weekly Scores table (Season, Week, Team Name, Manager,
Points, Week Rank) so the file imports straight in. Idempotent: a week already
in the file is skipped.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from yahoo import Yahoo, league_settings, week_points  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "weekly_scores_2026.csv")
HEAD = ["Season", "Week", "Team Name", "Manager", "Points", "Week Rank"]


def main():
    y = Yahoo()
    s = league_settings(y)
    week = int(sys.argv[1]) if len(sys.argv) > 1 else s["current_week"] - 1
    if week < s["start_week"]:
        print("nothing to roll yet")
        return
    with open(os.path.join(ROOT, "data", "managers.csv"), newline="") as f:
        managers = {r["team"]: r["manager"] for r in csv.DictReader(f)}

    existing = []
    if os.path.exists(OUT):
        with open(OUT, newline="") as f:
            existing = list(csv.DictReader(f))
    if any(int(r["Week"]) == week for r in existing):
        print(f"week {week} already rolled")
        return

    pts = week_points(y, week)
    ordered = sorted(pts.items(), key=lambda kv: -kv[1][0])
    rows = []
    for i, (team, (p, _)) in enumerate(ordered):
        rk = i + 1
        if i and p == ordered[i - 1][1][0]:
            rk = rows[-1][5]
        rows.append([s["season"], week, team, managers.get(team, "?"), round(p), rk])

    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEAD)
        w.writerows(rows)
    print(f"rolled week {week}: {len(rows)} rows")


if __name__ == "__main__":
    main()
