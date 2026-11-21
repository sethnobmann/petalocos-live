"""Append one final week to data/weekly_scores_2026.csv from a JSON map.

Usage: python3 scripts/add_week.py 9 '{"Umbertos": 139, ...}'
Idempotent: a week already in the file is skipped. Run h2h.py after.
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "weekly_scores_2026.csv")


def add_week(week, pts):
    with open(os.path.join(ROOT, "data", "managers.csv"), newline="") as f:
        mgr = {r["team"]: r["manager"] for r in csv.DictReader(f)}
    missing = [t for t in mgr if t not in pts]
    if missing or len(pts) != len(mgr):
        raise SystemExit(f"week {week}: teams don't match managers.csv, missing {missing}")
    raw = open(OUT, "rb").read()
    with open(OUT, newline="", encoding="utf-8-sig") as f:
        have = {int(r["Week"]) for r in csv.DictReader(f)}
    if week in have:
        print(f"week {week} already in file")
        return False
    nl = "\r\n" if b"\r\n" in raw else "\n"
    ordered = sorted(pts.items(), key=lambda kv: -kv[1])
    with open(OUT, "a", newline="") as f:
        if not raw.endswith(b"\n"):
            f.write(nl)
        w = csv.writer(f, lineterminator=nl)
        rk, prev = 0, None
        for i, (team, p) in enumerate(ordered):
            if p != prev:
                rk = i + 1
            prev = p
            w.writerow([2026, week, team, mgr[team], round(p), rk])
    print(f"added week {week}: {len(ordered)} rows")
    return True


if __name__ == "__main__":
    add_week(int(sys.argv[1]), json.loads(sys.argv[2]))
