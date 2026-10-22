"""One-time: get a Yahoo refresh token and save it to .env.

Run:  python3 scripts/yahoo_auth.py
It prints a URL. Open it signed in as Seffonz, click Agree. The browser lands on
https://localhost/callback?code=XXXX (page won't load, that's fine). Paste the
part after code= here. The refresh token is written to .env, never printed.
"""
import os
import sys
import webbrowser
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")
REDIRECT = "https://localhost/callback"


def read_env():
    out = {}
    if os.path.exists(ENV):
        for line in open(ENV):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                out[k] = v
    return out


env = read_env()
fresh = "--new" in sys.argv
cid = (None if fresh else env.get("YAHOO_CLIENT_ID")) or input("Client ID: ").strip()
sec = (None if fresh else env.get("YAHOO_CLIENT_SECRET")) or input("Client secret: ").strip()

url = (
    "https://api.login.yahoo.com/oauth2/request_auth"
    f"?client_id={cid}&redirect_uri={REDIRECT}&response_type=code&scope=fspt-r&language=en-us"
)
print("\nOpening the Yahoo consent page in your browser. Click Agree.\n")
webbrowser.open(url)
code = input("Paste the code from the localhost URL (everything after code=): ").strip()
if "code=" in code:
    code = code.split("code=")[1].split("&")[0]
r = requests.post(
    "https://api.login.yahoo.com/oauth2/get_token",
    auth=(cid, sec),
    data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT},
    timeout=30,
)
if r.status_code != 200:
    print("Yahoo said:", r.status_code, r.text[:300])
    raise SystemExit(1)
env["YAHOO_CLIENT_ID"] = cid
env["YAHOO_CLIENT_SECRET"] = sec
env["YAHOO_REFRESH_TOKEN"] = r.json()["refresh_token"]
with open(ENV, "w") as f:
    for k, v in env.items():
        f.write(f"{k}={v}\n")
os.chmod(ENV, 0o600)
print("\nRefresh token saved to .env. Done.")
