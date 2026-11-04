"""Build data/season_2026.csv from weekly_scores_2026.csv + h2h_schedule.csv.

One row per team: Season, Team Name, Manager, Points, Place, H2H W, H2H L,
H2H Record, Last Week, Last Week Pts, Last Week Rank, Next Opp, Through Week.
Run after every roll.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")


def main():
    wk = list(csv.DictReader(open(os.path.join(D, "weekly_scores_2026.csv"), newline="")))
    sched = list(csv.DictReader(open(os.path.join(D, "h2h_schedule.csv"), newline="")))
    mgr = {r["team"]: r["manager"] for r in csv.DictReader(open(os.path.join(D, "managers.csv"), newline=""))}
    pts = {}
    for r in wk:
        pts.setdefault(r["Team Name"], {})[int(r["Week"])] = (int(r["Points"]), int(r["Week Rank"]))
    done = sorted({int(r["Week"]) for r in wk})
    last = done[-1] if done else 0
    w = {t: 0 for t in mgr}
    l = {t: 0 for t in mgr}
    tie = {t: 0 for t in mgr}
    for g in sched:
        week = int(g["week"])
        if week > last:
            continue
        h, a = g["home"], g["away"]
        hp, ap = pts[h][week][0], pts[a][week][0]
        if hp > ap:
            w[h] += 1
            l[a] += 1
        elif ap > hp:
            w[a] += 1
            l[h] += 1
        else:
            tie[h] += 1
            tie[a] += 1
    nxt = {}
    for g in sched:
        if int(g["week"]) == last + 1:
            nxt[g["home"]] = g["away"]
            nxt[g["away"]] = g["home"]
    season = {t: sum(v[0] for v in pts[t].values()) for t in mgr}
    order = sorted(mgr, key=lambda t: -season[t])
    out = os.path.join(D, "season_2026.csv")
    with open(out, "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["Season", "Team Name", "Manager", "Points", "Place", "H2H W", "H2H L", "H2H Record",
                     "Last Week", "Last Week Pts", "Last Week Rank", "Next Opp", "Through Week"])
        for i, t in enumerate(order):
            rec = f"{w[t]}-{l[t]}" + (f"-{tie[t]}" if tie[t] else "")
            lp, lr = pts[t].get(last, (0, 0))
            cw.writerow([2026, t, mgr[t], season[t], i + 1, w[t], l[t], rec, last, lp, lr, nxt.get(t, ""), last])
            print(f"{i+1:2d} {t:18s} {season[t]:4d}  {rec:5s} next: {nxt.get(t, '')}")
    print("wrote", out)


if __name__ == "__main__":
    main()
