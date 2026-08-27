"""Curated discovery/insight programs from config/programs.yaml.

Unlike the other sources, these are hand-picked and PRE-APPROVED: they bypass the
relevance filters (topic/location/recency) and are injected straight into the
digest as evergreen "discovery" entries. They still go through de-dup + the
seen-store, so each shows once until you've been notified.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..models import Job

PROGRAMS_YAML = Path(__file__).resolve().parent.parent.parent / "config" / "programs.yaml"

_VALID_BUCKETS = {
    "machine_learning", "data_science", "statistics",
    "quant_finance", "health_data", "software_engineering",
}
# curated programs rank prominently but below the very freshest scored roles
_PROGRAM_SCORE = 20.0
# While a program's application window is OPEN it resurfaces on this cadence
# (per-entry `recurring_days` overrides it). Without a window, a program shows
# once. See main._due() for the full open/closed behavior.
_OPEN_RECUR_DAYS = 7


def fetch(path: Path | None = None) -> list[Job]:
    path = path or PROGRAMS_YAML
    if not path.exists():
        return []
    entries = yaml.safe_load(path.read_text()) or []
    jobs: list[Job] = []
    for p in entries:
        if not p.get("url") or not p.get("title"):
            continue
        bucket = str(p.get("topic", "")).strip()
        if bucket not in _VALID_BUCKETS:
            bucket = "software_engineering"
        opens = str(p.get("opens", "")).strip()
        closes = str(p.get("closes", "")).strip()
        has_window = bool(opens or closes)
        # windowed programs recur weekly while open; window-less ones show once
        recur = int(p.get("recurring_days", _OPEN_RECUR_DAYS if has_window else 0))
        job = Job(
            title=p["title"],
            company=p.get("company", ""),
            url=p["url"],
            source="program",
            location=p.get("location", ""),
            description=p["title"],
            employment="discovery",
            evergreen=True,
            category=bucket,
            recur_days=recur,
            opens=opens,
            closes=closes,
        ).clean()
        job.score = _PROGRAM_SCORE
        jobs.append(job)
    print(f"  program -> {len(jobs)} curated discovery programs")
    return jobs
