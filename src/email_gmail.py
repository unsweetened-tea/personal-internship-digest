"""Send the digest via the Gmail API using an OAuth refresh token.

Auth model (works headless in GitHub Actions):
  - You create an OAuth "Desktop app" client once in Google Cloud Console.
  - You run `python -m src.auth` locally once to grant access and print a
    refresh token.
  - CI reads three secrets: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
    GMAIL_REFRESH_TOKEN, plus DIGEST_TO (recipient).
No password ever touches this code.
"""
from __future__ import annotations

import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def send(subject: str, html_body: str, text_body: str,
         to_addr: str | None = None, from_addr: str = "me") -> None:
    to_addr = to_addr or os.environ["DIGEST_TO"]

    msg = MIMEMultipart("alternative")
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = build("gmail", "v1", credentials=_credentials(), cache_discovery=False)
    service.users().messages().send(userId=from_addr, body={"raw": raw}).execute()
    print(f"  ✉️  sent digest to {to_addr}")
