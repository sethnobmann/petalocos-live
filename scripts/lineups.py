"""Starting lineups off Yahoo team pages, for the app's team page.

A team page (/f1/700759/<id>?week=N) has three stat tables (statTable0 offense,
statTable1 kicker, statTable2 defense). Each row is one roster slot:

  td (slot: QB, RB, WR, TE, W/R/T, K, DEF, BN, IR)
  td.player
     a.name                 "Nico Collins"
     span.Fz-xxs            "Hou - WR"
     span.ysf-game-status   "Final W 26-3 vs Ind" / "Sun 10:00 am vs Ten"
  ... stat columns, found by header: "Fan Pts", "Proj Pts" (header cells use colspan)

parse_team(html) returns the starters as [slot, name, "Tm - POS", game status, pts, proj],
the same rows data/live_week.json carries and the app's team page draws.
Bench and IR are left out. pts is None until the player's game starts.

  python3 scripts/lineups.py tmp/team_1.html   # print what a saved page parses to
"""
import re
import sys
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
TEAM_POS = re.compile(r"^[A-Za-z]{2,3} - [A-Z/,]+$")


class Node:
    __slots__ = ("tag", "attrs", "kids", "parent")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.kids, self.parent = tag, dict(attrs), [], parent

    @property
    def cls(self):
        return (self.attrs.get("class") or "").split()

    def text(self):
        out = []
        for k in self.kids:
            out.append(k if isinstance(k, str) else k.text())
        return " ".join(" ".join(out).split())

    def walk(self):
        for k in self.kids:
            if isinstance(k, Node):
                yield k
                yield from k.walk()

    def find(self, tag=None, cls=None):
        for n in self.walk():
            if (tag is None or n.tag == tag) and (cls is None or cls in n.cls):
                return n
        return None

    def find_all(self, tag=None, cls=None):
        return [n for n in self.walk() if (tag is None or n.tag == tag) and (cls is None or cls in n.cls)]

    def children(self, *tags):
        return [k for k in self.kids if isinstance(k, Node) and k.tag in tags]


class StatTables(HTMLParser):
    """Builds a small tree for each <table id="statTable..."> and ignores the rest of the page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.cur, self.depth = [], None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.cur is None:
            if tag == "table" and (a.get("id") or "").startswith("statTable"):
                self.cur = Node(tag, attrs, None)
                self.tables.append(self.cur)
                self.depth = 1
            return
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag == "table":
            self.depth += 1
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        if self.cur is not None:
            self.cur.kids.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        if self.cur is None or tag in VOID:
            return
        # close up to the matching open tag; stray end tags with no match are ignored
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is None:
            return
        if tag == "table":
            self.depth -= 1
            if self.depth == 0:
                self.cur = None
                return
        self.cur = n.parent

    def handle_data(self, data):
        if self.cur is not None and data.strip() and self.cur.tag not in ("script", "style"):
            self.cur.kids.append(data)


def _expand(cells):
    out = []
    for c in cells:
        try:
            span = int(c.attrs.get("colspan") or 1)
        except ValueError:
            span = 1
        out.extend([c] * max(span, 1))
    return out


def _num(s):
    s = (s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_team(html):
    p = StatTables()
    p.feed(html)
    rows = []
    for t in p.tables:
        thead = t.find("thead")
        tbody = t.find("tbody")
        if thead is None or tbody is None:
            continue
        head_rows = thead.find_all("tr")
        if not head_rows:
            continue
        H = [c.text() for c in _expand(head_rows[-1].children("th", "td"))]
        fi = next((i for i, h in enumerate(H) if h.startswith("Fan Pts")), None)
        pi = next((i for i, h in enumerate(H) if h.startswith("Proj Pts")), None)
        for tr in tbody.find_all("tr"):
            C = _expand(tr.children("td", "th"))
            if not C:
                continue
            slot = C[0].text()
            if not slot or slot == "BN" or slot.startswith("IR"):
                continue
            pc = next((c for c in C if "player" in c.cls), C[1] if len(C) > 1 else C[0])
            a = pc.find("a", "name")
            name = a.text() if a else pc.text()[:30]
            tp = next((s.text() for s in pc.find_all("span") if TEAM_POS.match(s.text())), "")
            gs = pc.find(cls="ysf-game-status")
            st = gs.text() if gs else ""
            pts = _num(C[fi].text()) if fi is not None and fi < len(C) else None
            proj = _num(C[pi].text()) if pi is not None and pi < len(C) else None
            rows.append([slot, name, tp, st, pts, proj])
    return rows


def team_ids(league_html, names):
    """{team name: yahoo team id} from the links on the league page."""
    import html as H
    ids = {}
    for tid, label in re.findall(r'href="[^"]*/f1/700759/(\d+)"[^>]*>([^<]{1,60})</a>', league_html):
        label = " ".join(H.unescape(label).split())
        if label in names and label not in ids:
            ids[label] = int(tid)
    return ids


if __name__ == "__main__":
    for path in sys.argv[1:]:
        rows = parse_team(open(path, encoding="utf-8", errors="ignore").read())
        print(f"{path}: {len(rows)} starters, {sum(r[4] or 0 for r in rows):g} pts")
        for r in rows:
            print("  ", r)
