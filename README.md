# Petalocos live

Live scoring board for the Petalocos Yahoo league (nfl.l.700759), embedded in the
Glide app's Live tab. A GitHub Action pulls team points from the Yahoo Fantasy API
every 10 minutes during game windows and commits `docs/live.json`; GitHub Pages
serves `docs/`, and `docs/index.html` renders it.

## One-time setup

1. **Yahoo app.** https://developer.yahoo.com/apps/create (signed in as Seffonz).
   Name "Petalocos live", redirect URI `oob`, API permission: Fantasy Sports (read).
   Copy the Client ID and Client Secret.
2. **Refresh token.** On the Mac:
   `python3 scripts/yahoo_auth.py` → open the URL it prints, click Agree, paste the code.
   It prints a refresh token.
3. **GitHub secrets** (repo Settings → Secrets → Actions):
   `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REFRESH_TOKEN`.
4. **Pages.** Repo Settings → Pages → Deploy from branch `main`, folder `/docs`.
   The board lives at `https://<user>.github.io/petalocos-live/`.
5. **Glide.** Live tab → Web Embed component → that URL.

## Data files

- `data/managers.csv` – Yahoo team name → manager. If a team renames, add a row.
  The board shows a red warning when a team isn't mapped.
- `data/h2h_schedule.csv` – `week,home,away` using Yahoo team names. This is the
  head-to-head schedule, which doesn't exist on Yahoo.
- `data/weekly_scores_2026.csv` – written by the Tuesday roll. Import into the Glide
  `Weekly Scores` table (Data → Weekly Scores → Import) to keep history current.
  Rows are already in that table's column order.

## Schedule (UTC cron, padded for PDT/PST)

- Thu night, Sun 6:30am PT through the night game, Mon night: every 10 min.
- Tuesday 7am PT: roll last week's finals into `weekly_scores_2026.csv`.
- Anything else: run the workflow by hand from the Actions tab.

## Local test

```bash
export YAHOO_CLIENT_ID=… YAHOO_CLIENT_SECRET=… YAHOO_REFRESH_TOKEN=…
python3 scripts/yahoo.py        # prints current week scores
python3 scripts/fetch_live.py   # writes docs/live.json
python3 -m http.server -d docs 8000   # open http://localhost:8000
```
