# Petalocos app: how edits work

The app the league uses is a GitHub Pages site: https://sethnobmann.github.io/petalocos-live/app/
Seth reviews it and leaves comments on its review copy, the claude.ai artifact "Petalocos"
(slug 1e38950b-ed26-41e1-b6dd-7ae08fca69df, shared by link).

## Making a change

1. Edit `app/template.html`. It is the only source for the page: markup, styles and script in one file,
   with the data embedded at build time as `const D = __DATA__`.
2. Build:
   `python3 scripts/h2h.py && python3 scripts/build_app.py && python3 scripts/build_preview.py`
   - `docs/app/index.html` is the GitHub app.
   - `tmp/preview.html` is the review copy (crest inlined, no live feed). It is not committed.
3. Check it in a headless browser at phone width (390px), signed in by setting
   localStorage `petalocos.me` to a manager's name.
4. Republish the artifact from `tmp/preview.html` so Seth can look at it. The artifact is
   shared by link, so pass shared_live "public".
5. Push to `main` only after Seth says so. Pushing publishes to the GitHub app.

Seth's comments on the artifact don't wake a chat. When he says to check them, read them with
the artifact comment tools.

## Data

- `data/weekly_scores_2026.csv`: final points per team per week. The scraper on Seth's Mac mini
  (`scripts/scrape_live.py`, launchd every 10 min) rolls each finished week in and rebuilds the app.
- `docs/live.json`: live week points from that scraper. The GitHub app pulls it every 2 minutes.
  While NFL games are on (per ESPN's scoreboard) the scraper also loads the 10 team pages and adds `lineups` (each team's starters
  with points, projections and game status; parsed by `scripts/lineups.py`), so the app's team page is live too.
  Check a saved page with `python3 scripts/lineups.py tmp/team_1.html`.
- `data/live_week.json`: a live week snapshot with starting lineups, made by hand from Yahoo team pages.
- `data/history/`: all-time standings and `meta.json` (H2H champions, managers, weekly records).
  H2H champions not on file yet: 2005, 2015-2018, 2020-2023.

## League rules the app assumes

- Points league on Yahoo (league 700759). The head-to-head side game isn't on Yahoo; its schedule is
  `data/h2h_schedule.csv`.
- H2H playoffs: top 6 by record, ties broken by total points. Seeds 1-2 get a week 15 bye, 3v6 and 4v5.
  Week 16 re-seeds: #1 plays the lowest seed left. Week 17 is the final.
