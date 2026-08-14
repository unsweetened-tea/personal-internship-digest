"""Orchestrator: fetch -> filter -> dedupe -> new-only -> email.

Run locally:
    python -m src.main            # full run, sends email if Gmail secrets set
    python -m src.main --dry-run  # fetch + filter, write preview HTML, no email
    python -m src.main --all      # email every match, not just new-since-last-run
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml

from . import digest
from .dedupe import dedupe, load_seen, only_new, save_seen
from .filters import filter_jobs, sort_key
from .models import Job
from .sources import adzuna, ashby, github_lists, greenhouse, lever, usajobs

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
SEEN_FILE = DATA / "seen.json"
PREVIEW_FILE = DATA / "preview.html"


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a local .env if present (no-op in CI)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text()) or {}


def collect() -> list[Job]:
    companies = _load_yaml("companies.yaml")
    jobs: list[Job] = []
    print("Fetching sources...")
    jobs += greenhouse.fetch(companies.get("greenhouse", []))
    jobs += lever.fetch(companies.get("lever", []))
    jobs += ashby.fetch(companies.get("ashby", []))
    jobs += github_lists.fetch()
    jobs += adzuna.fetch()
    jobs += usajobs.fetch()
    print(f"Collected {len(jobs)} raw postings.")
    return jobs


def run(dry_run: bool = False, send_all: bool = False, seed: bool = False) -> int:
    _load_dotenv()
    filters_cfg = _load_yaml("filters.yaml")

    raw = collect()
    matched = filter_jobs(raw, filters_cfg)
    matched = dedupe(matched)
    matched.sort(key=sort_key, reverse=True)
    print(f"{len(matched)} roles matched relevance filters.")

    seen = load_seen(SEEN_FILE)

    if seed:
        # Mark everything currently open as already-seen, no email. Run once
        # after deploy so your first real digest only shows genuinely new roles.
        only_new(matched, seen)
        save_seen(SEEN_FILE, seen)
        print(f"Seeded {len(matched)} roles as seen. Future runs email only new ones.")
        return 0

    to_send = matched if send_all else only_new(matched, seen)
    to_send = to_send[: filters_cfg.get("max_items", 60)]
    print(f"{len(to_send)} to include in digest ({'all' if send_all else 'new only'}).")

    html_body = digest.build_html(to_send)
    text_body = digest.build_text(to_send)

    if dry_run:
        DATA.mkdir(parents=True, exist_ok=True)
        PREVIEW_FILE.write_text(html_body)
        print(f"Dry run — preview written to {PREVIEW_FILE}")
        return 0

    if not to_send:
        print("Nothing new — skipping email.")
        if not send_all:
            save_seen(SEEN_FILE, seen)
        return 0

    # Only import/send if we actually have something and creds are present.
    if not os.getenv("GMAIL_REFRESH_TOKEN"):
        print("No Gmail secrets set — skipping send (run with --dry-run to preview).")
        return 0

    from . import email_gmail

    subject = f"🎓 {len(to_send)} new internship match{'es' if len(to_send) != 1 else ''}"
    email_gmail.send(subject, html_body, text_body)

    if not send_all:
        save_seen(SEEN_FILE, seen)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily internship digest")
    ap.add_argument("--dry-run", action="store_true", help="preview HTML, don't email")
    ap.add_argument("--all", action="store_true", help="include all matches, not just new")
    ap.add_argument("--seed", action="store_true",
                    help="mark all current roles seen without emailing (run once after deploy)")
    args = ap.parse_args()
    raise SystemExit(run(dry_run=args.dry_run, send_all=args.all, seed=args.seed))


if __name__ == "__main__":
    main()
