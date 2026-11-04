"""Build the 2026 Glide tables from weekly_scores_2026.csv + h2h_schedule.csv.

data/season_2026.csv  one row per team: points, place, move vs last week,
                      H2H W-L, streak, form, PF/PA, next opponent.
data/schedule_2026.csv one row per game, weeks after the last rolled week.
Run after every roll, then re-import both into Glide (delete rows, Import).
Written with a UTF-8 BOM: without it Glide reads the arrows and dots as Latin-1.
"""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
SHORT = {"Lincoln Hawk": "Boo", "Maverick": "Chris S", "Miwok Indians": "Brandon", "FANTASY KING": "Chris K",
         "SHOW ME THE $$$$": "CJ", "FOTY*": "Dave", "u got pzzzed": "Tone", "Umbertos": "Rob",
         "dontmindme": "Seth", "Mooseknuckle's": "Brian"}


MONO = "font-family:'Share Tech Mono',Menlo,monospace"


def row_html(team, manager, w, l, pts, leader, lead):
    """One standings row for the Home custom collection (Glide Rich Text keeps inline styles).
    Left: team, manager, points back. Right: points + PTS, H2H record colored by result."""
    col = "#4CD37B" if w > l else "#FF5C5C" if w < l else "#C9D1DE"
    back = "leader" if leader else f"{lead - pts} back"
    return (
        '<div style="display:flex;align-items:flex-start">'
        '<div style="flex:1;min-width:0">'
        f'<div style="font-weight:700;font-size:16px;color:#F2F2F0;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{team}</div>'
        f'<div style="font-size:13px;color:#A3A9B3;margin-top:2px">{manager}</div>'
        f'<div style="font-size:12px;margin-top:2px;color:#6B717A;{MONO}">{back}</div></div>'
        '<div style="text-align:right;padding-left:8px">'
        f'<div style="{MONO};color:#FFB454;font-size:22px;line-height:1;text-shadow:0 0 8px rgba(255,180,84,.5)">{pts}'
        '<span style="font-size:9px;color:#6B717A;letter-spacing:.18em;margin-left:5px;text-shadow:none">PTS</span></div>'
        f'<div style="font-size:13px;margin-top:5px;color:{col};{MONO}">H2H {w}-{l}</div></div></div>'
    )


BADGE = "https://sethnobmann.github.io/petalocos-live/img/rk/{}-{}.png"


def h2h_html(team, manager, w, l, streak, pf, pa, pts, leader_w, wins_back):
    """One Head to head row: team, manager, streak / PF / PA on the left; W-L and points on the right."""
    col = "#4CD37B" if w > l else "#FF5C5C" if w < l else "#C9D1DE"
    back = "leader" if leader_w else f"{wins_back} back"
    return (
        '<div style="display:flex;align-items:flex-start">'
        '<div style="flex:1;min-width:0">'
        f'<div style="font-weight:700;font-size:16px;color:#F2F2F0;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{team}</div>'
        f'<div style="font-size:13px;color:#A3A9B3;margin-top:2px">{manager} \u00b7 {streak}</div>'
        f'<div style="font-size:12px;margin-top:2px;color:#6B717A;{MONO}">{back} \u00b7 PF {pf} \u00b7 PA {pa}</div></div>'
        '<div style="text-align:right;padding-left:8px">'
        f'<div style="{MONO};color:{col};font-size:22px;line-height:1">{w}-{l}'
        '<span style="font-size:9px;color:#6B717A;letter-spacing:.18em;margin-left:5px">H2H</span></div>'
        f'<div style="font-size:13px;margin-top:5px;color:#FFB454;{MONO}">{pts} PTS</div></div></div>'
    )


def main():
    wk = list(csv.DictReader(open(os.path.join(D, "weekly_scores_2026.csv"), newline="")))
    sched = list(csv.DictReader(open(os.path.join(D, "h2h_schedule.csv"), newline="")))
    mgr = {r["team"]: r["manager"] for r in csv.DictReader(open(os.path.join(D, "managers.csv"), newline=""))}
    pts = {}
    for r in wk:
        pts.setdefault(r["Team Name"], {})[int(r["Week"])] = (int(r["Points"]), int(r["Week Rank"]))
    done = sorted({int(r["Week"]) for r in wk})
    last = done[-1] if done else 0
    res = {t: [] for t in mgr}  # (week, 'W'/'L'/'T', opp, own, theirs)
    for g in sched:
        week = int(g["week"])
        if week > last:
            continue
        h, a = g["home"], g["away"]
        hp, ap = pts[h][week][0], pts[a][week][0]
        hr = "W" if hp > ap else "L" if hp < ap else "T"
        ar = "W" if ap > hp else "L" if ap < hp else "T"
        res[h].append((week, hr, a, hp, ap))
        res[a].append((week, ar, h, ap, hp))
    nxt = {}
    for g in sched:
        if int(g["week"]) == last + 1:
            nxt[g["home"]] = g["away"]
            nxt[g["away"]] = g["home"]
    season = {t: sum(v[0] for v in pts[t].values()) for t in mgr}
    prev = {t: season[t] - pts[t].get(last, (0, 0))[0] for t in mgr}
    order = sorted(mgr, key=lambda t: -season[t])
    prev_order = sorted(mgr, key=lambda t: -prev[t])
    place = {t: i + 1 for i, t in enumerate(order)}
    prev_place = {t: i + 1 for i, t in enumerate(prev_order)}
    lead = season[order[0]]

    def wl(t, upto):
        g = [x for x in res[t] if x[0] <= upto]
        return sum(1 for x in g if x[1] == "W"), sum(1 for x in g if x[1] == "L")

    h_key = {t: wl(t, last)[0] * 10000 + season[t] for t in mgr}
    h_prev_key = {t: wl(t, last - 1)[0] * 10000 + prev[t] for t in mgr}
    h_order = sorted(mgr, key=lambda t: -h_key[t])
    h_prev_order = sorted(mgr, key=lambda t: -h_prev_key[t])
    h_place = {t: i + 1 for i, t in enumerate(h_order)}
    h_prev_place = {t: i + 1 for i, t in enumerate(h_prev_order)}
    top_w = wl(h_order[0], last)[0]
    rows = []
    for t in order:
        r = sorted(res[t])
        W = sum(1 for x in r if x[1] == "W")
        L = sum(1 for x in r if x[1] == "L")
        T = sum(1 for x in r if x[1] == "T")
        streak = ""
        if r:
            k = r[-1][1]
            n = 0
            for x in reversed(r):
                if x[1] == k:
                    n += 1
                else:
                    break
            streak = f"{k}{n}"
        d = prev_place[t] - place[t]
        move = f"▲{d}" if d > 0 else f"▼{-d}" if d < 0 else "–"
        code = f"u{d}" if d > 0 else f"d{-d}" if d < 0 else "s"
        rec = f"{W}-{L}" + (f"-{T}" if T else "")
        hd = h_prev_place[t] - h_place[t]
        hcode = f"u{hd}" if hd > 0 else f"d{-hd}" if hd < 0 else "s"
        lp, lr = pts[t].get(last, (0, 0))
        rows.append({
            "Season": 2026, "Team Name": t, "Manager": mgr[t], "Short": SHORT[t], "Points": season[t],
            "Place": place[t], "Prev Place": prev_place[t], "Move": move, "Move code": code,
            "Back": season[t] - lead, "Back text": "" if season[t] == lead else f"-{lead - season[t]}",
            "H2H W": W, "H2H L": L, "H2H key": W * 10000 + season[t], "Streak": streak,
            "Form": "".join(x[1] for x in r[-5:]), "PF": season[t], "PA": sum(x[4] for x in r),
            "Last Week": last, "Last Week Pts": lp, "Last Week Rank": lr, "Next Opp": nxt.get(t, ""),
            "Through Week": last, "Record text": rec,
            "Row html": row_html(t, mgr[t], W, L, season[t], season[t] == lead, lead),
            "H2H place": h_place[t], "H2H prev place": h_prev_place[t],
            "H2H badge": BADGE.format(h_place[t], hcode),
            "H2H html": h2h_html(t, mgr[t], W, L, streak, season[t], sum(x[4] for x in r), season[t], W == top_w, top_w - W),
        })
        print(f"{place[t]:2d} {move:3s} {t:18s} {season[t]:4d}  {rec:5s} {streak:3s} next: {nxt.get(t, '')}")
    out = os.path.join(D, "season_2026.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)

    recs = {r["Team Name"]: r["Record text"] for r in rows}
    srows = []
    for g in sched:
        week = int(g["week"])
        if week <= last:
            continue
        h, a = g["home"], g["away"]
        srows.append({
            "Week": week, "Week label": f"Week {week}" + (" · this week" if week == last + 1 else ""),
            "Home": h, "Away": a, "Game": f"{a} at {h}",
            "Line": f"{SHORT[a]} {recs[a]} · {SHORT[h]} {recs[h]}",
            "Is next": "true" if week == last + 1 else "false",
        })
    out2 = os.path.join(D, "schedule_2026.csv")
    with open(out2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(srows[0].keys()))
        w.writeheader()
        w.writerows(srows)
    print("wrote", out2, len(srows), "games")


if __name__ == "__main__":
    main()
