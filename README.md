# Internship Digest

A daily email of college internships in statistics, machine learning, and
software engineering, plus related data roles in consulting, finance, and
healthcare. It checks a handful of job sources each morning and emails me the new
ones, ranked by how well they fit.

Sources (all public or official, nothing that breaks a site's terms of use):

- Company job boards on Greenhouse, Lever, and Ashby. These read the same JSON
  their own careers pages load. The list is in `config/companies.yaml`.
- Community internship lists from Simplify (their `listings.json` files).
- Adzuna and USAJobs search APIs. Optional, and need free keys.

It runs on GitHub Actions at no cost and sends the mail through the Gmail API.

## Quick start

```bash
cd internship-digest
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --dry-run
open data/preview.html
```

The dry run writes an HTML preview instead of sending anything. Company boards and
community lists work with no setup. Adzuna and USAJobs stay off until you add keys.

## Email setup (Gmail API)

1. In the Google Cloud Console, create a project and enable the Gmail API.
2. Open the OAuth consent screen, pick External, add `you@example.com` as a
   test user, then click Publish App so the status reads "In production". Leaving
   it in Testing makes Google expire the refresh token after 7 days, which quietly
   kills the digest.
3. Under Credentials, create an OAuth client ID of type Desktop app and download it
   as `client_secret.json` in this folder.
4. Run `python -m src.auth`. A browser opens. The app is unverified, so click
   Advanced, then "Go to (app)", and allow it. Copy the three values it prints.

## Deploy on GitHub Actions

1. Seed once so the first email isn't every open role at the same time:
   ```bash
   python -m src.main --seed
   ```
   That marks everything currently open as already seen and sends nothing.
2. Push the folder to a GitHub repo, including the updated `data/seen.json`.
3. In the repo, open Settings > Secrets and variables > Actions and add:
   - `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
   - `DIGEST_TO` set to `you@example.com`
   - optional: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `USAJOBS_API_KEY`, `USAJOBS_EMAIL`
4. In Settings > Actions > General, set Workflow permissions to "Read and write" so
   the job can commit `data/seen.json` back.
5. Open the Actions tab, pick daily-internship-digest, and click Run workflow to
   test it. Once the email lands you're set, and it runs on its own at noon daily.

The schedule is the cron line in `.github/workflows/daily.yml`, written in UTC and
set to noon Eastern. GitHub's cron ignores daylight saving, so shift it an hour at
the spring and fall time changes if you want it to stay at noon.

## Tuning

Everything is in `config/filters.yaml` unless the row says otherwise.

| To change | Edit |
|---|---|
| Companies to track | `config/companies.yaml` |
| Target cities | `preferred_locations` |
| Fields to include (ml, ds, stats, quant, health, swe) | `job_types` |
| Keep marketing and sales roles out | `exclude_title_keywords` |
| Drop roles by grad year or "new grad" | `exclude_keywords` |
| Internships only, or also full-time | `employment_types` in `hard_filters` |
| Turn the location / recency / employment gates on or off | `hard_filters` |
| How old a posting can be | `max_age_days` in `hard_filters` |
| Weighting of recency vs. preferred city in the ranking | `scoring` |
| Most roles in one email | `max_items` |
| Send time | cron line in `.github/workflows/daily.yml` |
| Add a source | new `fetch()` module in `src/sources/`, wired into `src/main.py` |

## How it works

Each run pulls every source, drops anything that isn't a student-level internship
in one of your chosen fields and cities, removes duplicates and anything already
emailed, then sends what's left ranked by topic match, recency, and preferred city.
Every role is tagged Internship or Full-time along the way.

Two things worth knowing:

- It only reads public JSON APIs and published data files. No scraping of sites
  that forbid it, and no CAPTCHAs.
- `data/seen.json` records what has already gone out. The Actions job commits it
  back after each run so you don't get repeats.
