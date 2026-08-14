"""Lever public postings API.

Endpoint: https://api.lever.co/v0/postings/<company>?mode=json  (public, no auth)
"""
from __future__ import annotations

from ..models import Job
from ._http import get_json

API = "https://api.lever.co/v0/postings/{company}"


def fetch(companies: list[str]) -> list[Job]:
    jobs: list[Job] = []
    for company in companies:
        data = get_json(API.format(company=company), params={"mode": "json"})
        if not data:
            continue
        name = company.replace("-", " ").title()
        for j in data:
            cats = j.get("categories") or {}
            desc = j.get("descriptionPlain") or j.get("description") or ""
            jobs.append(
                Job(
                    title=j.get("text", ""),
                    company=name,
                    url=j.get("hostedUrl", ""),
                    source="lever",
                    location=cats.get("location", ""),
                    posted_at="",
                    description=desc,
                ).clean()
            )
        print(f"  lever:{company} -> {len(data)} jobs")
    return jobs
