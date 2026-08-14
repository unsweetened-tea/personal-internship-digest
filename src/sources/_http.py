"""Tiny shared HTTP helper with a session, retries, and a friendly UA."""
from __future__ import annotations

import time

import requests

_UA = "internship-digest/1.0 (+personal job digest; contact via GitHub)"

_session = requests.Session()
_session.headers.update({"User-Agent": _UA, "Accept": "application/json"})


def get_json(url: str, *, params=None, headers=None, timeout=20, retries=2):
    """GET and parse JSON, retrying transient failures. Returns None on failure."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = _session.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 404:
                return None  # unknown token/company — skip quietly
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 - we want to keep the run alive
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    print(f"  ! request failed {url}: {last_err}")
    return None
