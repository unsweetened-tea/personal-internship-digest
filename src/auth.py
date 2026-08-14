"""One-time local helper to mint a Gmail API refresh token.

Prereqs (do this once in the Google Cloud Console):
  1. Create/select a project at https://console.cloud.google.com/
  2. APIs & Services -> Enable "Gmail API".
  3. APIs & Services -> OAuth consent screen -> External -> add yourself as a
     Test user (you@example.com). No app verification needed for personal use.
  4. Credentials -> Create Credentials -> OAuth client ID -> "Desktop app".
     Download the JSON as `client_secret.json` into this project folder.

Then run:
    python -m src.auth

A browser opens; approve access. This prints CLIENT_ID / CLIENT_SECRET /
REFRESH_TOKEN. Paste those into your GitHub repo secrets (never commit them).
"""
from __future__ import annotations

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_FILE = Path("client_secret.json")


def main() -> None:
    if not CLIENT_FILE.exists():
        raise SystemExit(
            "client_secret.json not found. Download your OAuth 'Desktop app' "
            "credentials from Google Cloud Console into this folder first."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    data = json.loads(CLIENT_FILE.read_text())
    node = data.get("installed") or data.get("web") or {}
    print("\n=== Add these to your GitHub repo secrets ===")
    print("GMAIL_CLIENT_ID    =", node.get("client_id"))
    print("GMAIL_CLIENT_SECRET=", node.get("client_secret"))
    print("GMAIL_REFRESH_TOKEN=", creds.refresh_token)
    print("=============================================\n")


if __name__ == "__main__":
    main()
