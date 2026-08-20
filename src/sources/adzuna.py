"""Adzuna job search API (official, free tier).

Get free keys at https://developer.adzuna.com/  -> set ADZUNA_APP_ID / ADZUNA_APP_KEY
If keys are missing, this source is skipped silently.
"""
from __future__ import annotations

import os

from ..models import Job
from ._http import get_json

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

# broad queries; the relevance filter narrows to student-level topic matches.
# spans ML, data science/analytics/consulting, quant/finance, and medical.
QUERIES = [
    "machine learning intern",
    "data science intern",
    "data analyst intern",
    "analytics consultant intern",
    "statistics intern",
    "biostatistics intern",
    "quantitative analyst intern",
    "actuarial intern",
    "software engineer intern",
    "data scientist new grad",
    "quantitative researcher new grad",
]


def fetch(country: str = "us", pages: int = 1) -> list[Job]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("  adzuna -> skipped (no ADZUNA_APP_ID/ADZUNA_APP_KEY)")
        return []

    jobs: list[Job] = []
    for query in QUERIES:
        for page in range(1, pages + 1):
            data = get_json(
                API.format(country=country, page=page),
                params={
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": query,
                    "results_per_page": 25,
                    "content-type": "application/json",
                    "max_days_old": 14,
                },
            )
            if not data:
                continue
            for j in data.get("results", []):
                jobs.append(
                    Job(
                        title=j.get("title", ""),
                        company=(j.get("company") or {}).get("display_name", ""),
                        url=j.get("redirect_url", ""),
                        source="adzuna",
                        location=(j.get("location") or {}).get("display_name", ""),
                        posted_at=(j.get("created") or "")[:10],
                        description=j.get("description", ""),
                    ).clean()
                )
    print(f"  adzuna -> {len(jobs)} raw jobs")
    return jobs
