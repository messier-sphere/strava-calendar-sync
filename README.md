# Strava events → Apple Calendar (free, no IFTTT)

Pulls upcoming events from your Strava clubs and publishes them as an `.ics`
feed you subscribe to once in Apple Calendar. A scheduled GitHub Action
rebuilds the feed every morning. Total cost: $0.

Your Strava credentials never leave your control: the client secret is only
ever typed into your own Mac (one-time token helper) and stored in your
repo's encrypted GitHub Secrets.

## Setup (about 15 minutes)

### 1. Create the Strava API app
1. Go to <https://www.strava.com/settings/api> (log in with your Strava account — free tier is fine).
2. Fill in anything for the app name/category; set **Authorization Callback Domain** to `localhost`.
3. Note your **Client ID** and **Client Secret**.

### 2. Get your tokens (one time, on your Mac)
```bash
cd strava-calendar-sync
python3 get_token.py
```
- It prints an authorization URL → open it, approve the app.
- You'll land on `http://localhost/?code=XXXX…` → paste that full URL back into the script.
- It prints a refresh token. Keep it private.

### 3. Create the GitHub repo and push these files
1. Create a new **public** repo on GitHub (Pages needs a public repo on the free plan).
2. Push this folder's contents to it.

### 4. Add repo secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN` (from step 2)
- `STRAVA_CLUB_IDS` (optional — comma-separated club IDs to limit the feed; leave empty for all your clubs)

### 5. Enable GitHub Pages
Repo → Settings → Pages → Deploy from a branch → branch `main`, folder `/(root)` → Save.
Your feed URL will be `https://<your-username>.github.io/<repo-name>/strava-events.ics`.

### 6. Run it once and subscribe
1. Repo → Actions → "Sync Strava events" → Run workflow. Check it goes green and `strava-events.ics` appears in the repo.
2. **Mac:** Calendar → File → New Calendar Subscription → paste the feed URL. Set Auto-refresh to every hour and give it a color.
3. **iPhone:** the subscribed calendar syncs over via iCloud automatically.

Done. The feed rebuilds every morning at ~7:15 AM PT and Apple Calendar picks up changes on its own.

## Notes
- Strava's club-events endpoint is undocumented (`/clubs/{id}/group_events`). If Strava changes it, the Action will fail and you'll see it in the Actions tab — the script prints a clear error.
- Strava API limits: 200 calls / 15 min, 2000 / day. A handful of clubs uses ~10 calls per run.
- GitHub disables scheduled workflows after 60 days of repo inactivity — the daily feed commit counts as activity, so it stays alive.
- To force a refresh anytime: Actions → Run workflow.
