"""Union-merge data/seen.json with another copy (usually the remote's version).

Two workflow runs (or a run + a manual push) can both change data/seen.json.
Since the file rewrites every timestamp each run, a git rebase/merge would just
conflict. Instead we merge by union: keep every id, and for shared ids keep the
newest date. This never loses a "seen" id, so roles are never re-emailed.

Usage: python scripts/merge_seen.py <other_seen.json>
"""
import json
import sys

SEEN = "data/seen.json"


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def main() -> None:
    ours = load(SEEN)
    theirs = load(sys.argv[1]) if len(sys.argv) > 1 else {}
    merged = dict(theirs)
    for k, v in ours.items():
        if k not in merged or v > merged[k]:
            merged[k] = v
    with open(SEEN, "w") as f:
        json.dump(merged, f, indent=0, sort_keys=True)
    print(f"merged seen.json: {len(merged)} ids "
          f"(ours={len(ours)}, theirs={len(theirs)})")


if __name__ == "__main__":
    main()
