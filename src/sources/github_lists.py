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

# raw listings.json URLs (the "dev" branch carries the live data file)
FEEDS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
]


def _fmt_loc(locations) -> str:
    if isinstance(locations, list):
        return ", ".join(str(x) for x in locations[:3])
    return str(locations or "")


def fetch(feeds: list[str] | None = None) -> list[Job]:
    feeds = feeds or FEEDS
    jobs: list[Job] = []
    for feed in feeds:
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
                ).clean()
            )
            count += 1
        print(f"  github-list -> {count} active jobs from {feed.split('/')[4]}")
    return jobs
