"""Thin Yahoo Fantasy Sports API client.

Env vars: YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_REFRESH_TOKEN.
"""
import os
import sys
import time
import requests

TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API = "https://fantasysports.yahooapis.com/fantasy/v2"
LEAGUE_KEY = os.environ.get("YAHOO_LEAGUE_KEY", "nfl.l.700759")


def access_token():
    cid = os.environ["YAHOO_CLIENT_ID"]
    sec = os.environ["YAHOO_CLIENT_SECRET"]
    rt = os.environ["YAHOO_REFRESH_TOKEN"]
    r = requests.post(
        TOKEN_URL,
        auth=(cid, sec),
        data={"grant_type": "refresh_token", "refresh_token": rt, "redirect_uri": "oob"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


class Yahoo:
    def __init__(self):
        self.tok = access_token()

    def get(self, path, tries=3):
        url = f"{API}/{path}"
        sep = "&" if "?" in url else "?"
        url += f"{sep}format=json"
        for i in range(tries):
            r = requests.get(url, headers={"Authorization": f"Bearer {self.tok}"}, timeout=30)
            if r.status_code == 999 or r.status_code == 429:
                time.sleep(30 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"rate limited on {path}")


def walk(obj):
    """Yield every dict nested anywhere in Yahoo's list-of-dicts JSON."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def find_all(obj, key):
    return [d[key] for d in walk(obj) if key in d]


def league_settings(y):
    j = y.get(f"league/{LEAGUE_KEY}")
    lg = j["fantasy_content"]["league"]
    meta = lg[0] if isinstance(lg, list) else lg
    return {
        "name": meta.get("name"),
        "current_week": int(meta.get("current_week", 1)),
        "start_week": int(meta.get("start_week", 1)),
        "end_week": int(meta.get("end_week", 18)),
        "season": meta.get("season"),
    }


def week_points(y, week):
    """Return {team_name: (points, projected)} for one week."""
    j = y.get(f"league/{LEAGUE_KEY}/teams/stats;type=week;week={week}")
    teams = j["fantasy_content"]["league"][1]["teams"]
    out = {}
    for k, v in teams.items():
        if k == "count":
            continue
        t = v["team"]
        name = find_all(t, "name")[0]
        pts = 0.0
        proj = None
        for d in walk(t):
            if "team_points" in d:
                pts = float(d["team_points"].get("total") or 0)
            if "team_projected_points" in d:
                proj = float(d["team_projected_points"].get("total") or 0)
        out[name] = (pts, proj)
    return out


if __name__ == "__main__":
    y = Yahoo()
    s = league_settings(y)
    print(s)
    wk = int(sys.argv[1]) if len(sys.argv) > 1 else s["current_week"]
    for name, (p, pr) in sorted(week_points(y, wk).items(), key=lambda x: -x[1][0]):
        print(f"{name:24s} {p:7.2f}  proj {pr}")
