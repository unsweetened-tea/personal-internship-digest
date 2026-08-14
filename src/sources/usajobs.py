"""USAJobs search API (official U.S. government jobs, free).

Register at https://developer.usajobs.gov/APIRequest to get an API key.
Set USAJOBS_API_KEY and USAJOBS_EMAIL (the email you registered with).
If missing, this source is skipped silently. Great for federal medical/stats roles.
"""
from __future__ import annotations

import os

from ..models import Job
from ._http import get_json

API = "https://data.usajobs.gov/api/search"

QUERIES = [
    "data science intern",
    "statistics intern",
    "machine learning",
]


def fetch() -> list[Job]:
    api_key = os.getenv("USAJOBS_API_KEY")
    email = os.getenv("USAJOBS_EMAIL")
    if not (api_key and email):
        print("  usajobs -> skipped (no USAJOBS_API_KEY/USAJOBS_EMAIL)")
        return []

    headers = {"Host": "data.usajobs.gov", "User-Agent": email, "Authorization-Key": api_key}
    jobs: list[Job] = []
    for query in QUERIES:
        data = get_json(
            API,
            params={"Keyword": query, "ResultsPerPage": 25, "WhoMayApply": "public"},
            headers=headers,
        )
        if not data:
            continue
        for item in data.get("SearchResult", {}).get("SearchResultItems", []):
            d = item.get("MatchedObjectDescriptor", {})
            locs = d.get("PositionLocationDisplay", "")
            jobs.append(
                Job(
                    title=d.get("PositionTitle", ""),
                    company=d.get("OrganizationName", ""),
                    url=d.get("PositionURI", ""),
                    source="usajobs",
                    location=locs,
                    posted_at=(d.get("PublicationStartDate") or "")[:10],
                    description=(d.get("UserArea", {}).get("Details", {}) or {}).get(
                        "JobSummary", ""
                    ),
                ).clean()
            )
    print(f"  usajobs -> {len(jobs)} raw jobs")
    return jobs
