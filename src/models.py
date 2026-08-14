"""Shared data model for a single job posting."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Job:
    title: str
    company: str
    url: str
    source: str                       # e.g. "greenhouse", "adzuna"
    location: str = ""
    posted_at: str = ""               # ISO date string if known
    description: str = ""             # plain text, used for relevance scoring
    category: str = ""                # filled in by the relevance filter
    score: float = 0.0                # relevance score, higher = better

    # matched keyword buckets, for display + debugging
    matched: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Stable id for de-duplication across runs.

        Uses the URL when present (canonical), else company+title+location.
        """
        basis = self.url.strip().lower() or f"{self.company}|{self.title}|{self.location}".lower()
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

    def clean(self) -> "Job":
        self.title = (self.title or "").strip()
        self.company = (self.company or "").strip()
        self.location = (self.location or "").strip()
        self.url = (self.url or "").strip()
        # keep description compact — we only need it for keyword matching
        self.description = " ".join((self.description or "").split())[:4000]
        return self
