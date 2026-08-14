"""Greenhouse public job board API.

Endpoint: https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true
Docs: https://developers.greenhouse.io/job-board.html  (public, no auth)
"""
from __future__ import annotations

import html
import re

from ..models import Job
from ._http import get_json

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(text or ""))


def fetch(tokens: list[str]) -> list[Job]:
    jobs: list[Job] = []
    for token in tokens:
        data = get_json(API.format(token=token), params={"content": "true"})
        if not data:
            continue
        company = token.replace("-", " ").title()
        for j in data.get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            jobs.append(
                Job(
                    title=j.get("title", ""),
                    company=company,
                    url=j.get("absolute_url", ""),
                    source="greenhouse",
                    location=loc,
                    posted_at=(j.get("updated_at") or "")[:10],
                    description=_strip_html(j.get("content", "")),
                ).clean()
            )
        print(f"  greenhouse:{token} -> {len(data.get('jobs', []))} jobs")
    return jobs
