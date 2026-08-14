"""De-duplication + a persisted 'seen' store so the digest only shows new roles.

seen.json maps job-id -> ISO date first seen. Old entries are pruned so the file
doesn't grow forever. GitHub Actions commits this file back to the repo each run.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .models import Job

_PRUNE_AFTER_DAYS = 60


def load_seen(path: Path) -> dict[str, str]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_seen(path: Path, seen: dict[str, str]) -> None:
    cutoff = (dt.date.today() - dt.timedelta(days=_PRUNE_AFTER_DAYS)).isoformat()
    pruned = {k: v for k, v in seen.items() if v >= cutoff}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pruned, indent=0, sort_keys=True))


def dedupe(jobs: list[Job]) -> list[Job]:
    """Collapse duplicate postings (same job listed on multiple sources)."""
    by_id: dict[str, Job] = {}
    for j in jobs:
        existing = by_id.get(j.id)
        if existing is None or j.score > existing.score:
            by_id[j.id] = j
    return list(by_id.values())


def only_new(jobs: list[Job], seen: dict[str, str]) -> list[Job]:
    """Return jobs not seen before, and mark them seen (mutates `seen`)."""
    today = dt.date.today().isoformat()
    fresh = []
    for j in jobs:
        if j.id not in seen:
            fresh.append(j)
        seen[j.id] = today  # refresh timestamp so active roles aren't pruned
    return fresh
