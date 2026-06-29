"""
Gmail ingestion.

Pulls emails from the last N days, extracts subject + sender + body,
and chunks them for storage in ChromaDB.

Auth: reuses the same credentials.json as Drive, but needs an additional
Gmail scope. If you've already authorized Drive, you'll get a one-time
re-auth prompt to approve the new scope — then token.json is updated and
you won't be asked again.

Why subject + sender + body together in one chunk? For emails, context
collapses fast without the header. "Please approve this by Friday" means
nothing without knowing who sent it and what thread it's on. Keeping them
together means every retrieved chunk is self-contained.

Why skip attachments? Attachments are handled by the Drive/file_upload
modules. Gmail ingestion focuses on the text conversation layer only.
"""

from __future__ import annotations

import base64
import email as email_lib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from ingestion.chunker import Chunk, chunk_text
from utils.config import get_config

# Email chunk size/overlap come from config.yaml (chunking.email) — smaller
# than documents because emails are short and focused.
_EMAIL = get_config()["chunking"]["email"]

# Gmail needs its own scope on top of (or instead of) Drive's scope.
# We request both so a single token.json covers the full app.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

TOKEN_PATH = Path("token.json")
CREDENTIALS_PATH = Path("credentials.json")


def _get_service():
    """
    Build an authenticated Gmail service.

    Important: we pass the combined SCOPES list here. If token.json was
    created with only the Drive scope, this will trigger a re-auth so Gmail
    access gets added to the token.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    "credentials.json not found. See Drive setup instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    """
    Recursively extract plain text from a Gmail message payload.

    Gmail stores email bodies as a tree of MIME parts. A simple email has
    one part; a reply chain or HTML email has nested parts. We walk the tree
    and collect all text/plain leaves, skipping HTML (too noisy with tags).
    """
    body_text = []

    mime_type = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and data:
        decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        body_text.append(decoded)

    # Recurse into multipart/* parts
    for part in payload.get("parts", []):
        body_text.append(_decode_body(part))

    return "\n".join(filter(None, body_text))


def _clean_body(text: str) -> str:
    """
    Strip quoted reply chains and excessive whitespace.

    Why? A 20-email thread where each reply re-quotes the full history would
    create enormous chunks that are ~90% duplicate content. Stripping quoted
    lines (lines starting with >) keeps each chunk focused on new content.
    """
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip quoted reply lines and common reply headers
        if stripped.startswith(">"):
            continue
        if re.match(r"^On .+ wrote:$", stripped):
            continue
        cleaned.append(line)

    # Collapse 3+ consecutive blank lines into 2
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_emails(days: int = 90, max_emails: int = 200, label: str = "INBOX") -> List[dict]:
    """
    Fetch emails from Gmail, returning a list of dicts with subject/sender/body/date.

    days=90 covers a quarter of activity — enough for a demo without being slow.
    max_emails=200 prevents runaway API calls on large inboxes.
    label="INBOX" skips sent mail and spam; pass "SENT" to include outbound.
    """
    service = _get_service()

    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    query = f"after:{after_date}"

    results = service.users().messages().list(
        userId="me",
        q=query,
        labelIds=[label],
        maxResults=max_emails,
    ).execute()

    messages = results.get("messages", [])
    print(f"Found {len(messages)} emails to process...")

    emails = []
    for i, msg_ref in enumerate(messages):
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="full",
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "(no subject)")
        sender = headers.get("From", "unknown")
        date = headers.get("Date", "")

        body = _decode_body(msg["payload"])
        body = _clean_body(body)

        if not body.strip():
            continue  # skip empty emails (calendar invites, etc.)

        emails.append({
            "id": msg_ref["id"],
            "subject": subject,
            "sender": sender,
            "date": date,
            "body": body,
        })

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(messages)}...")

    return emails


def emails_to_chunks(emails: List[dict], chunk_size: int = _EMAIL["size"], overlap: int = _EMAIL["overlap"]) -> List[Chunk]:
    """
    Convert email dicts into chunks.

    Each email becomes: a header block (subject + sender + date) followed by
    the body. The header is prepended to every chunk from that email so that
    any retrieved chunk is self-identifying — you always know who sent it and
    what it was about, even if you get chunk 3 of 5.

    chunk_size=300 (not 500) because emails are shorter and more focused than
    docs. Smaller chunks = more precise retrieval.
    """
    all_chunks: List[Chunk] = []

    for email in emails:
        header = (
            f"Email from: {email['sender']}\n"
            f"Subject: {email['subject']}\n"
            f"Date: {email['date']}\n"
            f"---\n"
        )
        full_text = header + email["body"]
        source = f"gmail:{email['subject'][:60]}"

        chunks = chunk_text(
            full_text,
            source=source,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        # Tag each chunk with the email ID so we can deduplicate on re-ingest
        for chunk in chunks:
            chunk.metadata["email_id"] = email["id"]
            chunk.metadata["sender"] = email["sender"]
            chunk.metadata["subject"] = email["subject"]
            chunk.metadata["date"] = email["date"]

        all_chunks.extend(chunks)

    return all_chunks


def ingest_gmail(days: int = 90, max_emails: int = 200) -> List[Chunk]:
    """Top-level function: fetch → convert → return chunks ready for ChromaDB."""
    emails = fetch_emails(days=days, max_emails=max_emails)
    print(f"Converting {len(emails)} emails to chunks...")
    chunks = emails_to_chunks(emails)
    print(f"Created {len(chunks)} chunks from {len(emails)} emails")
    return chunks
