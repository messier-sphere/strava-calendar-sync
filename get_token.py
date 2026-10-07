#!/usr/bin/env python3
"""One-time Strava OAuth helper. Run this on your own Mac, once.

It prints the Strava authorization URL. You open it in your browser, approve
the app, and Strava redirects you to http://localhost/?code=XXXX&scope=read.
Paste that full redirect URL back here and this script exchanges the code for
your access + refresh tokens. Put the REFRESH token in your GitHub repo
secrets as STRAVA_REFRESH_TOKEN. Your client secret never leaves this machine.

Standard library only — no pip installs.
"""
import json
import os
import sys
import urllib.parse
import urllib.request


def main():
    client_id = (os.environ.get("STRAVA_CLIENT_ID") or input("Strava Client ID: ")).strip()
    client_secret = (os.environ.get("STRAVA_CLIENT_SECRET")
                     or input("Strava Client Secret (never shared): ")).strip()
    if not client_id or not client_secret:
        print("Client ID and secret are both required.", file=sys.stderr)
        raise SystemExit(2)

    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={urllib.parse.quote(client_id)}"
        "&response_type=code"
        f"&redirect_uri={urllib.parse.quote('http://localhost')}"
        "&approval_prompt=force"
        "&scope=read"
    )
    print("\n1) Open this URL in your browser and approve the app:\n")
    print(f"   {auth_url}\n")
    print("2) You'll land on http://localhost/?code=XXXX&scope=read...")
    pasted = input("3) Paste that FULL redirect URL here: ").strip()

    try:
        code = urllib.parse.parse_qs(
            urllib.parse.urlparse(pasted).query)["code"][0]
    except (KeyError, IndexError):
        print("Couldn't find a ?code= parameter in that URL.", file=sys.stderr)
        raise SystemExit(2)

    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://www.strava.com/oauth/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        print(f"Token exchange failed: {e}", file=sys.stderr)
        raise SystemExit(1)

    print("\nSuccess. Save these as GitHub repo secrets:\n")
    print(f"  STRAVA_REFRESH_TOKEN = {data['refresh_token']}")
    print("\n(Keep this terminal output private — it contains credentials.)")


if __name__ == "__main__":
    main()
