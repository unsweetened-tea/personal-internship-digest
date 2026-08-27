"""Orchestrator: fetch -> filter -> dedupe -> new-only -> email.

Run locally:
    python -m src.main            # full run, sends email if Gmail secrets set
    python -m src.main --dry-run  # fetch + filter, write preview HTML, no email
    python -m src.main --all      # email every match, not just new-since-last-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path

import yaml

from . import digest
from .dedupe import dedupe, load_seen, only_new, save_seen
from .filters import filter_jobs, sort_key
from .models import Job
from .sources import adzuna, ashby, github_lists, greenhouse, lever, programs, usajobs

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
    matched += programs.fetch()      # curated discovery programs (pre-approved)
    matched = dedupe(matched)
    matched.sort(key=sort_key, reverse=True)
    print(f"{len(matched)} roles after filters + curated programs.")

    seen = load_seen(SEEN_FILE)

    if seed:
        # Mark everything currently open as already-seen, no email. Run once
        # after deploy so your first real digest only shows genuinely new roles.
        only_new(matched, seen)
        save_seen(SEEN_FILE, seen)
        print(f"Seeded {len(matched)} roles as seen. Future runs email only new ones.")
        return 0

    today = dt.date.today().isoformat()
    cap = filters_cfg.get("max_items", 60)

    # Pick what to email. In normal mode only roles we haven't sent before are
    # candidates; if there are more than the cap, the rest stay unseen and get
    # picked up on following runs (the backlog drains instead of being dropped).
    def _due(j) -> bool:
        last = seen.get(j.id)
        if last is None:
            return True                       # never sent
        if j.recur_days:                      # recurring: due again after N days
            try:
                return (dt.date.today() - dt.date.fromisoformat(last)).days >= j.recur_days
            except ValueError:
                return True
        return False                          # one-time role already sent

    fresh = [] if send_all else [j for j in matched if _due(j)]
    pool = matched if send_all else fresh
    # Curated discovery programs always make the cut (they're shown once); fill
    # the remaining slots with the top scored roles, then re-sort for display.
    progs = [j for j in pool if j.source == "program"]
    others = [j for j in pool if j.source != "program"]
    to_send = (progs + others[: max(0, cap - len(progs))])[:cap]
    to_send.sort(key=sort_key, reverse=True)
    queued = 0 if send_all else max(0, len(fresh) - len(to_send))
    print(f"{len(to_send)} to include in digest "
          f"({'all' if send_all else f'new; {queued} more queued for later'}).")

    html_body = digest.build_html(to_send)
    text_body = digest.build_text(to_send)

    if dry_run:
        DATA.mkdir(parents=True, exist_ok=True)
        PREVIEW_FILE.write_text(html_body)
        print(f"Dry run — preview written to {PREVIEW_FILE}")
        return 0

    def _persist() -> None:
        # keep still-matching, already-seen roles alive so they aren't pruned and
        # re-emailed later; mark only the roles we actually sent as seen. Unsent
        # fresh roles stay unseen on purpose so the next run emails them.
        for j in matched:
            # refresh still-open one-time roles so they aren't pruned & re-emailed;
            # skip recurring programs, or their clock would reset every run and
            # they'd never age back into view.
            if j.id in seen and not j.recur_days:
                seen[j.id] = today
        for j in to_send:
            seen[j.id] = today
        save_seen(SEEN_FILE, seen)

    if not to_send:
        print("Nothing new — skipping email.")
        if not send_all:
            _persist()
        return 0

    # Only import/send if we actually have something and creds are present.
    if not os.getenv("GMAIL_REFRESH_TOKEN"):
        print("No Gmail secrets set — skipping send (run with --dry-run to preview).")
        return 0

    from . import email_gmail

    n = len(to_send)
    subject = f"🎓 {n} new internship match{'es' if n != 1 else ''}"
    if queued:
        subject += f" (+{queued} more queued)"
    email_gmail.send(subject, html_body, text_body)

    if not send_all:
        _persist()
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
