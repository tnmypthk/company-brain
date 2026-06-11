"""
Google Drive ingestion.

Auth flow: OAuth2 with a local credentials.json from Google Cloud Console.
On first run it opens a browser to authorize; subsequent runs use token.json.

Why export Google Docs as plain text? Drive Docs are stored in Google's internal
format, not as files. The export API converts them on the fly — text/plain is the
simplest target that preserves all the content we care about.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ingestion.chunker import Chunk, chunk_text

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_PATH = Path("token.json")
CREDENTIALS_PATH = Path("credentials.json")

# MIME types we know how to handle
_EXPORTABLE = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
}
_DOWNLOADABLE = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def _get_service():
    """Build and return an authenticated Drive service, refreshing creds as needed."""
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
                    "credentials.json not found. Download it from Google Cloud Console → "
                    "APIs & Services → Credentials → OAuth 2.0 Client IDs."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


def list_files(folder_id: str | None = None, max_results: int = 50) -> list[dict]:
    """
    List files in Drive (or a specific folder). Returns dicts with id, name, mimeType.

    folder_id=None lists from your entire Drive — fine for demos, but scope it
    to a folder in production so you're not ingesting personal files.
    """
    service = _get_service()
    query = f"'{folder_id}' in parents" if folder_id else None
    results = (
        service.files()
        .list(
            q=query,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime)",
        )
        .execute()
    )
    return results.get("files", [])


def ingest_drive_file(file_id: str, chunk_size: int = 500, overlap: int = 50) -> List[Chunk]:
    """
    Download or export a single Drive file and return chunks.

    Google Docs → exported as plain text (no download URL exists for native formats).
    PDFs/DOCX → downloaded as binary, then parsed by file_upload.ingest_file_bytes.
    """
    service = _get_service()
    from googleapiclient.http import MediaIoBaseDownload
    import io

    meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
    name = meta["name"]
    mime = meta["mimeType"]

    if mime in _EXPORTABLE:
        export_mime, _ = _EXPORTABLE[mime]
        content_bytes = (
            service.files().export_media(fileId=file_id, mimeType=export_mime).execute()
        )
        source = f"drive:{name}"
        # Sheets export as CSV — use the row-to-prose converter instead of raw chunking
        if mime == "application/vnd.google-apps.spreadsheet":
            from ingestion.csv_ingest import ingest_csv_bytes
            return ingest_csv_bytes(content_bytes, source=source)
        text = content_bytes.decode("utf-8", errors="replace")
        return chunk_text(text, source=source, chunk_size=chunk_size, overlap=overlap)

    elif mime in _DOWNLOADABLE:
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)

        from ingestion.file_upload import ingest_file_bytes
        return ingest_file_bytes(buf.read(), name, chunk_size=chunk_size, overlap=overlap)

    else:
        raise ValueError(f"Unsupported Drive MIME type: {mime} ({name})")


def ingest_folder(folder_id: str, chunk_size: int = 500, overlap: int = 50) -> List[Chunk]:
    """Ingest all supported files in a Drive folder."""
    files = list_files(folder_id=folder_id)
    all_chunks: List[Chunk] = []

    for f in files:
        if f["mimeType"] not in {**_EXPORTABLE, **_DOWNLOADABLE}:
            continue
        try:
            chunks = ingest_drive_file(f["id"], chunk_size=chunk_size, overlap=overlap)
            all_chunks.extend(chunks)
            print(f"  Ingested {f['name']} → {len(chunks)} chunks")
        except Exception as e:
            print(f"  Skipping {f['name']}: {e}")

    return all_chunks
