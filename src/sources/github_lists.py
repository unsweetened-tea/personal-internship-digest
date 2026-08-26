"""Community-maintained internship listing repos.

These repos publish a machine-readable listings.json that their bots keep fresh.
We read the raw JSON directly (no scraping of rendered pages).

Default: SimplifyJobs / Summer2026-Internships. Add more entries as they appear
(the schema below is the common Simplify/pittcsc format).
"""
from __future__ import annotations

import datetime as dt

from ..models import Job
from ._http import get_json

# Each feed: (raw listings.json URL, employment type, evergreen?).
#   - employment: authoritative label for the feed (internship vs new-grad).
#   - evergreen: True skips the recency age-gate — for curated program lists whose
#     "date_posted" is just when they were added, not a fresh posting date.
FEEDS = [
    ("https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json", "internship", False),
    ("https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json", "full-time", False),
    # Underclassmen (freshman/sophomore) opportunities — rolling programs, so evergreen.
    ("https://raw.githubusercontent.com/Jose-Gael-Cruz-Lopez/underclassmen-opportunities/main/.github/scripts/listings.json", "internship", True),
]


def _fmt_loc(locations) -> str:
    if isinstance(locations, list):
        return ", ".join(str(x) for x in locations[:3])
    return str(locations or "")


def fetch(feeds: list[tuple[str, str, bool]] | None = None) -> list[Job]:
    feeds = feeds or FEEDS
    jobs: list[Job] = []
    for feed, employment, evergreen in feeds:
        data = get_json(feed)
        if not data:
            continue
        count = 0
        for j in data:
            # skip closed / hidden rows
            if j.get("active") is False or j.get("is_visible") is False:
                continue
            url = j.get("url", "")
            posted = j.get("date_posted")
            posted_str = ""
            if isinstance(posted, (int, float)):
                posted_str = dt.datetime.utcfromtimestamp(posted).strftime("%Y-%m-%d")
            jobs.append(
                Job(
                    title=j.get("title", ""),
                    company=j.get("company_name", ""),
                    url=url,
                    source="github-list",
                    location=_fmt_loc(j.get("locations")),
                    posted_at=posted_str,
                    # these feeds carry no long description; title carries the signal
                    description=j.get("title", ""),
                    employment=employment,
                    evergreen=evergreen,
                ).clean()
            )
            count += 1
        print(f"  github-list -> {count} active jobs from {feed.split('/')[4]}")
    return jobs
