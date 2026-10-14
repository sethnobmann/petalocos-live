"""One-time: get a Yahoo refresh token.

Run:  python3 scripts/yahoo_auth.py
It prints a URL. Open it signed in as Seffonz, click Agree, paste the code back.
Prints the refresh token to store as the YAHOO_REFRESH_TOKEN secret.
"""
import os
import requests

cid = os.environ.get("YAHOO_CLIENT_ID") or input("Client ID: ").strip()
sec = os.environ.get("YAHOO_CLIENT_SECRET") or input("Client secret: ").strip()

print("\nOpen this in a browser where you're signed in to Yahoo:\n")
print(
    "https://api.login.yahoo.com/oauth2/request_auth"
    f"?client_id={cid}&redirect_uri=oob&response_type=code&language=en-us\n"
)
code = input("Paste the code Yahoo shows you: ").strip()
r = requests.post(
    "https://api.login.yahoo.com/oauth2/get_token",
    auth=(cid, sec),
    data={"grant_type": "authorization_code", "code": code, "redirect_uri": "oob"},
    timeout=30,
)
r.raise_for_status()
j = r.json()
print("\nRefresh token (save as YAHOO_REFRESH_TOKEN secret, do not share):\n")
print(j["refresh_token"])
