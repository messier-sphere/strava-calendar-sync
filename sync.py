#!/usr/bin/env python3
"""Fetch upcoming Strava club events and publish them as an .ics calendar feed.

Uses only the Python standard library (no pip installs needed).

Configuration via environment variables:
    STRAVA_CLIENT_ID       Strava API app client ID
    STRAVA_CLIENT_SECRET   Strava API app client secret
    STRAVA_REFRESH_TOKEN   Long-lived refresh token from the one-time OAuth flow
    STRAVA_CLUB_IDS        Optional comma-separated club IDs to limit the feed
                           (empty = all clubs the athlete belongs to)

Writes: strava-events.ics  (subscribe to it from Apple Calendar)
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://www.strava.com/api/v3"
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strava-events.ics")


def _req(method, url, data=None, token=None):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode()[:300]
        except Exception:
            detail = ""
        print(f"HTTP {e.code} on {method} {url}: {detail}", file=sys.stderr)
        if e.code in (401, 403):
            print("Auth failed: your refresh token may be expired or revoked. "
                  "Re-run get_token.py to get a fresh one.", file=sys.stderr)
        raise SystemExit(1)


def refresh_access_token(client_id, client_secret, refresh_token):
    data = _req("POST", "https://www.strava.com/oauth/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    return data["access_token"]


def get_clubs(token):
    return _req("GET", f"{API}/athlete/clubs", token=token)


def get_group_events(token, club_id):
    # Undocumented endpoint; also filter client-side in case ?upcoming is ignored.
    return _req("GET", f"{API}/clubs/{club_id}/group_events?upcoming=true", token=token)


def ics_escape(text):
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    # ICS lines should be <= 75 octets; fold longer ones. Simple ASCII-safe fold.
    out = []
    while len(line.encode("utf-8")) > 75:
        cut = 75
        while len(line[:cut].encode("utf-8")) > 75:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)


def to_ics_utc(value):
    """Accept '2026-04-01T09:00:00Z' (or with offset) -> '20260401T090000Z'."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(events):
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//strava-calendar-sync//EN",
             "X-WR-CALNAME:Strava Events", "CALSCALE:GREGORIAN"]
    for ev in events:
        title = ev.get("title") or "Strava event"
        club = (ev.get("club") or {}).get("name", "")
        url = ev.get("url", "")
        uid = f"strava-event-{ev.get('id', hash(title + str(ev.get('start'))))}@strava-calendar-sync"
        lines.append("BEGIN:VEVENT")
        lines.append(fold(f"UID:{uid}"))
        lines.append(f"DTSTAMP:{now}")
        lines.append(f"DTSTART:{to_ics_utc(ev['start'])}")
        if ev.get("end"):
            lines.append(f"DTEND:{to_ics_utc(ev['end'])}")
        lines.append(fold(f"SUMMARY:{ics_escape(title)}"))
        if club:
            lines.append(fold(f"LOCATION:{ics_escape(club)}"))
        desc = "\n".join(p for p in [url, "via Strava"] if p)
        lines.append(fold(f"DESCRIPTION:{ics_escape(desc)}"))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    client_id = os.environ.get("STRAVA_CLIENT_ID", "").strip()
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh_token):
        print("Missing STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET / STRAVA_REFRESH_TOKEN.",
              file=sys.stderr)
        raise SystemExit(2)

    only = {c.strip() for c in os.environ.get("STRAVA_CLUB_IDS", "").split(",") if c.strip()}

    token = refresh_access_token(client_id, client_secret, refresh_token)
    clubs = get_clubs(token)
    print(f"Found {len(clubs)} clubs.")

    now = datetime.now(timezone.utc)
    events = []
    for club in clubs:
        cid = str(club.get("id"))
        if only and cid not in only:
            continue
        try:
            fetched = get_group_events(token, cid)
        except SystemExit:
            print(f"Skipping club {club.get('name')} ({cid}) after error.", file=sys.stderr)
            continue
        if isinstance(fetched, dict):  # some responses wrap in {"events": [...]}
            fetched = fetched.get("events", [])
        upcoming = []
        for ev in fetched or []:
            try:
                start = datetime.fromisoformat(
                    ev["start"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if start >= now:
                ev = dict(ev)
                ev.setdefault("club", {}).setdefault("name", club.get("name", ""))
                upcoming.append(ev)
        print(f"Club '{club.get('name')}': {len(upcoming)} upcoming events.")
        events.extend(upcoming)

    events.sort(key=lambda e: e["start"])
    ics = build_ics(events)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(ics)
    print(f"Wrote {len(events)} events to {OUT_FILE}")


if __name__ == "__main__":
    main()
