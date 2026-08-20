"""Render the list of jobs into a sleek, scannable HTML (and text) email body.

Design goals: fast to skim, easy to navigate.
  - a header with the date + total count
  - a jump-nav bar of category pills (with counts) linking to each section
  - color-coded category accents so the eye can triage at a glance
  - compact cards with a freshness badge ("Today" / "3d") and source tag
Everything is inline-styled for maximum email-client compatibility.
"""
from __future__ import annotations

import datetime as dt
import html
from collections import defaultdict

from .models import Job

# per-category identity: label, emoji, accent color, soft background, anchor id
_CATS = {
    "machine_learning": {
        "label": "Machine Learning / AI", "emoji": "🤖",
        "accent": "#7c3aed", "soft": "#f5f3ff", "anchor": "cat-ml",
    },
    "data_science": {
        "label": "Data Science & Analytics", "emoji": "📈",
        "accent": "#0d9488", "soft": "#f0fdfa", "anchor": "cat-ds",
    },
    "quant_finance": {
        "label": "Quant & Finance", "emoji": "💹",
        "accent": "#c2410c", "soft": "#fff7ed", "anchor": "cat-quant",
    },
    "health_data": {
        "label": "Medical & Health Data", "emoji": "🧬",
        "accent": "#db2777", "soft": "#fdf2f8", "anchor": "cat-health",
    },
    "statistics": {
        "label": "Statistics", "emoji": "📊",
        "accent": "#0891b2", "soft": "#ecfeff", "anchor": "cat-stats",
    },
    "software_engineering": {
        "label": "Software Engineering", "emoji": "💻",
        "accent": "#2563eb", "soft": "#eff6ff", "anchor": "cat-swe",
    },
}
# display + primary-bucket priority order (most specific/topical first)
_ORDER = [
    "machine_learning", "data_science", "quant_finance",
    "health_data", "statistics", "software_engineering",
]
_FALLBACK = _CATS["software_engineering"]


def _primary_bucket(job: Job) -> str:
    """Pick the highest-priority bucket this job matched, for section grouping."""
    hits = {b.strip() for b in job.category.split(",")} if job.category else set()
    for bucket in _ORDER:
        if bucket in hits:
            return bucket
    return "software_engineering"


def _freshness(posted_at: str) -> tuple[str, str, str]:
    """Return (label, text_color, bg_color) for a recency badge."""
    if not posted_at:
        return ("", "", "")
    try:
        posted = dt.date.fromisoformat(posted_at[:10])
    except ValueError:
        return ("", "", "")
    age = (dt.date.today() - posted).days
    if age <= 0:
        return ("Today", "#065f46", "#d1fae5")
    if age == 1:
        return ("1d ago", "#065f46", "#d1fae5")
    if age <= 7:
        return (f"{age}d ago", "#1e3a8a", "#dbeafe")
    return (f"{age}d ago", "#6b7280", "#f3f4f6")


def _card(job: Job, cat: dict) -> str:
    title = html.escape(job.title)
    company = html.escape(job.company) or "—"
    loc = html.escape(job.location)
    src = html.escape(job.source)
    url = html.escape(job.url)
    accent = cat["accent"]

    meta_bits = []
    if loc:
        meta_bits.append(f"📍 {loc}")
    fresh_label, fresh_fg, fresh_bg = _freshness(job.posted_at)
    meta = " &nbsp;·&nbsp; ".join(meta_bits)

    badge = ""
    if fresh_label:
        badge = (
            f"<span style=\"display:inline-block;background:{fresh_bg};color:{fresh_fg};"
            f"font-size:11px;font-weight:700;border-radius:10px;padding:2px 8px;"
            f"margin-left:6px;vertical-align:middle;\">{fresh_label}</span>"
        )

    # employment tag (Internship / Full-time) — solid pill in the category accent
    emp_tag = ""
    if job.employment == "internship":
        emp_tag = _emp_pill("Internship", "#ffffff", accent)
    elif job.employment == "full-time":
        emp_tag = _emp_pill("Full-time", accent, cat["soft"])

    return (
        f"<a href=\"{url}\" style=\"text-decoration:none;color:inherit;\">"
        "<div style=\"border-left:3px solid " + accent + ";background:#ffffff;"
        "border:1px solid #eceef2;border-left:3px solid " + accent + ";"
        "border-radius:0 10px 10px 0;padding:12px 14px;margin:8px 0;\">"
        f"<div style=\"font-weight:600;font-size:15px;line-height:1.35;color:{accent};\">"
        f"{title}{badge}</div>"
        f"<div style=\"margin-top:5px;\">{emp_tag}"
        f"<span style=\"font-size:13px;color:#111827;font-weight:500;\">{company}</span></div>"
        f"<div style=\"margin-top:5px;font-size:12px;color:#6b7280;\">{meta}"
        f"<span style=\"color:#c3c7cf;\"> &nbsp;·&nbsp; {src}</span></div>"
        "</div></a>"
    )


def _emp_pill(text: str, fg: str, bg: str) -> str:
    return (
        f"<span style=\"display:inline-block;background:{bg};color:{fg};font-size:11px;"
        f"font-weight:700;border-radius:6px;padding:2px 7px;margin-right:7px;"
        f"vertical-align:middle;\">{text}</span>"
    )


def build_html(jobs: list[Job]) -> str:
    today = dt.date.today().strftime("%A, %B %-d")
    wrap_open = (
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "Helvetica,Arial,sans-serif;max-width:640px;margin:0 auto;padding:20px 16px;"
        "background:#ffffff;color:#111827;\">"
    )

    if not jobs:
        return (
            wrap_open
            + "<div style=\"font-size:20px;font-weight:700;\">🎓 Internship Digest</div>"
            + f"<div style=\"color:#6b7280;margin-top:2px;\">{today}</div>"
            + "<div style=\"margin-top:24px;padding:20px;background:#f9fafb;border-radius:12px;"
              "text-align:center;color:#6b7280;\">No new matching roles today. "
              "Check back tomorrow. 👀</div></div>"
        )

    groups: dict[str, list[Job]] = defaultdict(list)
    for j in jobs:
        groups[_primary_bucket(j)].append(j)

    parts = [wrap_open]

    # ---- header -------------------------------------------------------------
    parts.append(
        "<div style=\"border-bottom:1px solid #eceef2;padding-bottom:14px;margin-bottom:6px;\">"
        "<div style=\"font-size:22px;font-weight:800;letter-spacing:-0.02em;\">"
        "🎓 Internship Digest</div>"
        f"<div style=\"color:#6b7280;font-size:14px;margin-top:3px;\">{today} "
        f"&nbsp;·&nbsp; <b style=\"color:#111827;\">{len(jobs)}</b> new "
        f"role{'s' if len(jobs) != 1 else ''}</div></div>"
    )

    # ---- jump-nav pills -----------------------------------------------------
    pills = []
    for bucket in _ORDER:
        bjobs = groups.get(bucket)
        if not bjobs:
            continue
        cat = _CATS[bucket]
        pills.append(
            f"<a href=\"#{cat['anchor']}\" style=\"display:inline-block;text-decoration:none;"
            f"background:{cat['soft']};color:{cat['accent']};border-radius:20px;"
            f"padding:6px 13px;margin:4px 6px 4px 0;font-size:13px;font-weight:700;\">"
            f"{cat['emoji']} {cat['label']} · {len(bjobs)}</a>"
        )
    parts.append(f"<div style=\"margin:12px 0 8px;\">{''.join(pills)}</div>")

    # ---- sections -----------------------------------------------------------
    for bucket in _ORDER:
        bjobs = groups.get(bucket)
        if not bjobs:
            continue
        cat = _CATS[bucket]
        parts.append(
            f"<a name=\"{cat['anchor']}\"></a>"
            f"<div id=\"{cat['anchor']}\" style=\"margin-top:22px;margin-bottom:2px;\">"
            f"<span style=\"display:inline-block;font-size:16px;font-weight:800;"
            f"color:{cat['accent']};border-bottom:3px solid {cat['accent']};"
            f"padding-bottom:3px;\">{cat['emoji']} {cat['label']}</span>"
            f"<span style=\"color:#9ca3af;font-weight:600;font-size:13px;\"> "
            f"&nbsp;{len(bjobs)}</span></div>"
        )
        for j in bjobs:
            parts.append(_card(j, cat))

    # ---- footer -------------------------------------------------------------
    parts.append(
        "<div style=\"margin-top:28px;padding-top:14px;border-top:1px solid #eceef2;"
        "color:#9ca3af;font-size:11px;line-height:1.5;\">"
        "Sourced from company ATS boards (Greenhouse · Lever · Ashby), community "
        "listing repos, and job-search APIs. "
        "Tune locations, recency &amp; job types in <code>config/filters.yaml</code>.</div>"
    )
    parts.append("</div>")
    return "".join(parts)


def build_text(jobs: list[Job]) -> str:
    today = dt.date.today().strftime("%Y-%m-%d")
    if not jobs:
        return f"Internship Digest — {today}\nNo new matching roles today."

    groups: dict[str, list[Job]] = defaultdict(list)
    for j in jobs:
        groups[_primary_bucket(j)].append(j)

    lines = [f"🎓 Internship Digest — {today}  ({len(jobs)} new)", ""]
    for bucket in _ORDER:
        bjobs = groups.get(bucket)
        if not bjobs:
            continue
        cat = _CATS[bucket]
        lines.append(f"== {cat['emoji']} {cat['label']} ({len(bjobs)}) ==")
        for j in bjobs:
            fresh = _freshness(j.posted_at)[0]
            emp = {"internship": "Internship", "full-time": "Full-time"}.get(j.employment, "")
            tags = " ".join(t for t in (f"[{emp}]" if emp else "", f"[{fresh}]" if fresh else "") if t)
            tags = f"  {tags}" if tags else ""
            loc = f" — {j.location}" if j.location else ""
            lines.append(f"• {j.title}{tags}")
            lines.append(f"  {j.company}{loc}  ({j.source})")
            lines.append(f"  {j.url}")
        lines.append("")
    return "\n".join(lines)
