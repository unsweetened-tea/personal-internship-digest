# 🎓 Internship Digest

A daily email digest of **college-level internship / new-grad roles** in
**statistics, machine learning, and software engineering** at tech / finance /
medical firms.

It pulls from ToS-friendly sources only:

- **Company ATS boards** — Greenhouse, Lever, Ashby public JSON (the same feeds
  the companies' own careers pages use). Edit `config/companies.yaml`.
- **Community listing repos** — Simplify/pittcsc `listings.json` feeds.
- **Job-search APIs** — Adzuna and USAJobs (official, free API keys, optional).

Runs free on **GitHub Actions** every morning and emails you via the **Gmail API**.

```
fetch sources → filter (level + topic) → dedupe → new-since-last-run → email
```

## Quick start (local)

```bash
cd internship-digest
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Preview today's matches without emailing — writes data/preview.html
python -m src.main --dry-run
open data/preview.html
```

No API keys are needed for the ATS + GitHub-list sources — the dry run works
immediately. Adzuna/USAJobs skip themselves until you add keys.

## Turn on email (Gmail API)

1. Google Cloud Console → new project → **enable Gmail API**.
2. **OAuth consent screen** → External. Add `you@example.com` as a Test user,
   then click **PUBLISH APP** so the status is **In production**.
   ⚠️ Skip this and your refresh token silently **expires after 7 days** (Google
   expires tokens for apps stuck in "Testing"). Production tokens don't expire.
3. **Credentials → OAuth client ID → Desktop app** → download `client_secret.json`
   into this folder.
4. Mint a refresh token once:
   ```bash
   python -m src.auth
   ```
   A browser opens. Because the app is unverified you'll see a warning — click
   **Advanced → Go to (app)** and allow. Copy the three printed values.

## Deploy on GitHub Actions

1. **Seed locally first** so your first email isn't a firehose of every open role:
   ```bash
   python -m src.main --seed      # marks all current roles "seen", sends nothing
   ```
2. Push this folder to a new GitHub repo (include the updated `data/seen.json`).
3. Repo **Settings → Secrets and variables → Actions → New repository secret** → add:
   - `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
   - `DIGEST_TO` = `you@example.com`
   - *(optional)* `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `USAJOBS_API_KEY`, `USAJOBS_EMAIL`
4. Repo **Settings → Actions → General → Workflow permissions** → select
   **Read and write permissions** (lets the job commit `data/seen.json` back).
5. **Actions** tab → **daily-internship-digest** → *Run workflow* to test right now.
   Check your inbox, then you're done — it runs **daily at 12:00 PM** on its own.

**Send time** lives in `.github/workflows/daily.yml` (`cron:` line, in UTC —
currently noon Eastern). GitHub cron doesn't follow daylight saving, so nudge it
±1 hour at the spring/fall switch if you want it exactly at local noon.

## Tuning

| Want to… | Edit |
|---|---|
| Track different companies | `config/companies.yaml` |
| Change keywords / topics / seniority filter | `config/filters.yaml` |
| Set target metros | `preferred_locations` in `config/filters.yaml` |
| Restrict to ml / swe / stats (or all) | `job_types:` in `config/filters.yaml` |
| Turn location/recency gates on/off | `hard_filters:` in `config/filters.yaml` |
| Tune recency vs location weighting | `scoring:` block in `config/filters.yaml` |
| Change send time | the `cron:` line in `.github/workflows/daily.yml` |
| Add a new source | drop a `fetch()` module in `src/sources/`, wire it in `src/main.py` |

## Notes

- Only uses **official/public JSON APIs and published data files** — no scraping
  of sites whose terms forbid it, no CAPTCHA solving.
- `data/seen.json` is the memory of what's already been emailed; it's committed
  back each run so the "new only" logic survives across days.
