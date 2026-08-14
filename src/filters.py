"""Relevance filtering + scoring, driven by config/filters.yaml."""
from __future__ import annotations

import datetime as dt
import re

from .models import Job


def _recency_bonus(posted_at: str, weight: float, window_days: int) -> float:
    """Linear-decay bonus: +weight if posted today, 0 once older than window."""
    if not posted_at or window_days <= 0:
        return 0.0
    try:
        posted = dt.date.fromisoformat(posted_at[:10])
    except ValueError:
        return 0.0
    age = (dt.date.today() - posted).days
    if age < 0:  # future-dated postings: treat as brand new
        age = 0
    if age >= window_days:
        return 0.0
    return weight * (1 - age / window_days)

# cache compiled patterns per keyword so we don't rebuild them for every job
_PAT_CACHE: dict[str, re.Pattern] = {}


def _pattern(term: str) -> re.Pattern:
    pat = _PAT_CACHE.get(term)
    if pat is None:
        # word-boundary match so "coop" doesn't hit "cooperative" and
        # "ml"/"ai"/"ii" only match as standalone tokens.
        pat = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)")
        _PAT_CACHE[term] = pat
    return pat


def _norm(text: str) -> str:
    return (text or "").lower()


# friendly job-type names -> internal topic bucket keys
_TOPIC_ALIASES = {
    "ml": "machine_learning",
    "machine_learning": "machine_learning",
    "machine learning": "machine_learning",
    "ai": "machine_learning",
    "swe": "software_engineering",
    "software_engineering": "software_engineering",
    "software engineering": "software_engineering",
    "stats": "statistics",
    "stat": "statistics",
    "statistics": "statistics",
}


def enabled_topics(cfg: dict) -> set[str] | None:
    """Return the set of allowed topic buckets, or None if all are allowed."""
    jt = [str(x).strip().lower() for x in (cfg.get("job_types") or ["all"])]
    if not jt or "all" in jt:
        return None
    return {_TOPIC_ALIASES.get(x, x) for x in jt}


def _passes_location(job: Job, cfg: dict) -> bool:
    hf = cfg.get("hard_filters", {})
    if not hf.get("by_location"):
        return True
    loc = _norm(job.location)
    if not loc:
        return bool(hf.get("include_unlocated", False))
    return bool(_any_in(cfg.get("preferred_locations", []), loc))


def _passes_recency(job: Job, cfg: dict) -> bool:
    hf = cfg.get("hard_filters", {})
    if not hf.get("by_recency"):
        return True
    if not job.posted_at:
        return bool(hf.get("include_undated", True))
    try:
        posted = dt.date.fromisoformat(job.posted_at[:10])
    except ValueError:
        return bool(hf.get("include_undated", True))
    age = (dt.date.today() - posted).days
    return age <= hf.get("max_age_days", 30)


def _any_in(needles: list[str], haystack: str) -> list[str]:
    hits = []
    for n in needles:
        term = n.strip().lower()
        if term and _pattern(term).search(haystack):
            hits.append(n)
    return hits


def relevant(job: Job, cfg: dict) -> bool:
    """Return True and annotate job.category/score/matched if it passes filters."""
    title = _norm(job.title)
    body = _norm(f"{job.title} {job.description} {job.location}")

    # 1) reject obviously senior roles (checked on the title, always)
    if _any_in(cfg["seniority_blocklist"], title):
        return False

    # 2) must look student / early-career.
    #    - github-list feeds are already curated internship/new-grad lists, so the
    #      list itself is the level signal (their titles often omit "intern").
    #    - every other source: require a level word IN THE TITLE. Matching the long
    #      description body caused senior/full-time roles to leak in via boilerplate.
    level_in_title = _any_in(cfg["level_keywords"], title)
    if job.source == "github-list":
        level_in_body = level_in_title  # trusted list; body==title for these anyway
    else:
        if not level_in_title:
            return False
        level_in_body = level_in_title

    # 3) hard filters: location + recency (fail fast, before topic scan)
    if not _passes_location(job, cfg):
        return False
    if not _passes_recency(job, cfg):
        return False

    # 4) must match at least one ENABLED topic bucket (job_types hard filter)
    allowed = enabled_topics(cfg)
    matched_topics: list[str] = []
    hit_buckets: list[str] = []
    score = 0.0
    s = cfg["scoring"]

    for bucket, words in cfg["topics"].items():
        if allowed is not None and bucket not in allowed:
            continue
        in_title = _any_in(words, title)
        in_body = _any_in(words, body)
        if in_title or in_body:
            hit_buckets.append(bucket)
            matched_topics.extend(in_title or in_body)
            score += s["title_topic_hit"] * len(in_title)
            score += s["desc_topic_hit"] * len(in_body)

    if not hit_buckets:
        return False

    # 5) scoring bonuses (ordering only — everything here has already passed)
    if level_in_title:
        score += s["level_title_hit"]

    # location: prefer your target metros; fall back to a small US/remote nudge
    loc = _norm(job.location)
    if _any_in(cfg.get("preferred_locations", []), loc):
        score += s.get("preferred_location_bonus", 0)
    elif _any_in(["remote", "united states", "usa", "u.s.", "us"], loc):
        score += s.get("us_location_bonus", 0)

    # recency: freshest postings float to the top
    score += _recency_bonus(
        job.posted_at,
        s.get("recency_weight", 0),
        s.get("recency_window_days", 30),
    )

    job.category = ", ".join(sorted(set(hit_buckets)))
    job.matched = sorted(set(matched_topics + level_in_title + level_in_body))
    job.score = score
    return True


def sort_key(job: Job):
    """Relevance-first, then most-recently-posted as the tiebreaker."""
    return (job.score, job.posted_at or "")


def filter_jobs(jobs: list[Job], cfg: dict) -> list[Job]:
    kept = [j for j in jobs if relevant(j, cfg)]
    kept.sort(key=sort_key, reverse=True)
    return kept
