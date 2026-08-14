"""Ashby public job board posting API.

Endpoint: https://api.ashbyhq.com/posting-api/job-board/<token>  (public, no auth)
"""
from __future__ import annotations

from ..models import Job
from ._http import get_json

API = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch(tokens: list[str]) -> list[Job]:
    jobs: list[Job] = []
    for token in tokens:
        data = get_json(API.format(token=token), params={"includeCompensation": "false"})
        if not data:
            continue
        name = token.replace("-", " ").title()
        postings = data.get("jobs", [])
        for j in postings:
            jobs.append(
                Job(
                    title=j.get("title", ""),
                    company=name,
                    url=j.get("jobUrl", "") or j.get("applyUrl", ""),
                    source="ashby",
                    location=j.get("location", ""),
                    posted_at=(j.get("publishedAt") or "")[:10],
                    description=j.get("descriptionPlain", "") or "",
                ).clean()
            )
        print(f"  ashby:{token} -> {len(postings)} jobs")
    return jobs
