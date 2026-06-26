"""
Slack ingestion.

Pulls messages from named channels for the last N days, formats them into a
readable transcript, and chunks them for storage in ChromaDB.

Auth: needs a Slack bot token (xoxb-...). Create one at api.slack.com/apps:
  1. Create an app → "From scratch"
  2. OAuth & Permissions → add bot scopes:
       channels:read, channels:history   (public channels)
       groups:read, groups:history       (private channels, optional)
       users:read                        (resolve user IDs to names)
  3. Install to workspace → copy the Bot User OAuth Token
  4. IMPORTANT: invite the bot to each channel you want to ingest
     (/invite @your-bot in Slack) — bots can only read channels they're in.

Why a transcript per channel (not one chunk per message)? Slack messages are
tiny — often under 10 words. A chunk per message would give ChromaDB thousands
of near-meaningless embeddings ("sounds good!", "+1"). Concatenating a channel's
messages chronologically and chunking the transcript keeps conversational
context together: a question and its answer land in the same chunk, which is
what makes retrieval useful.

Why prepend author + timestamp to each message? Same reason Gmail prepends the
header: a retrieved chunk must be self-identifying. "We decided to go with
option B" is useless without knowing who said it, where, and when.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from ingestion.chunker import Chunk, chunk_text
from utils.config import get_secret


def _get_client(token: str | None = None):
    """
    Build a Slack WebClient.

    Token resolution order: explicit argument (from the dashboard's token
    field) → SLACK_BOT_TOKEN from secrets/.env. The dashboard passes the token
    through rather than writing it to disk — tokens typed into a UI shouldn't
    be silently persisted. get_secret reads Streamlit Cloud secrets first,
    then the local environment.
    """
    from slack_sdk import WebClient

    token = token or get_secret("SLACK_BOT_TOKEN")
    if not token:
        raise EnvironmentError(
            "No Slack token. Pass one in, set SLACK_BOT_TOKEN in .env locally, "
            "or add it to the Streamlit Cloud secrets manager."
        )
    return WebClient(token=token)


def _resolve_channel_id(client, channel_name: str) -> str:
    """
    Convert a channel name ("engineering") to its ID ("C0123ABCDEF").

    The Slack API addresses channels by ID, but humans know them by name.
    conversations_list is paginated via cursors — a workspace can have
    thousands of channels, so we keep fetching pages until we find a match.

    Private channels need the optional groups:read scope. Rather than
    requiring it, we ask for public+private and fall back to public-only
    if Slack rejects the broader request with missing_scope — so the
    minimal 3-scope setup from the docstring works out of the box.
    """
    from slack_sdk.errors import SlackApiError

    name = channel_name.lstrip("#").strip()
    types = "public_channel,private_channel"
    cursor = None
    while True:
        try:
            response = client.conversations_list(
                types=types,
                limit=200,
                cursor=cursor,
            )
        except SlackApiError as e:
            if e.response["error"] == "missing_scope" and "private" in types:
                types = "public_channel"  # retry without the private scope
                cursor = None
                continue
            raise
        for channel in response["channels"]:
            if channel["name"] == name:
                return channel["id"]
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    raise ValueError(
        f"Channel '{name}' not found. Check the name, and make sure the bot "
        f"has been invited to it (/invite @your-bot)."
    )


def _build_user_cache(client) -> dict:
    """
    Map user IDs → display names in one users_list call.

    Messages reference authors by ID ("U0123ABC"). Calling users_info per
    message would be one API call per author per message — slow and rate-limit
    prone. One paginated users_list up front gives us the whole workspace.
    """
    users = {}
    cursor = None
    while True:
        response = client.users_list(limit=200, cursor=cursor)
        for user in response["members"]:
            profile = user.get("profile", {})
            users[user["id"]] = (
                profile.get("display_name")
                or profile.get("real_name")
                or user.get("name", user["id"])
            )
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return users


def fetch_messages(
    client,
    channel_id: str,
    days: int = 90,
    max_messages: int = 1000,
) -> List[dict]:
    """
    Fetch messages from one channel, oldest first.

    conversations_history returns newest-first pages; we collect then reverse
    so the transcript reads top-to-bottom chronologically — the order a human
    (and an embedding of conversational flow) expects.

    Skipped: messages with a "subtype" (channel_join, bot housekeeping, etc.)
    — they're noise, not knowledge. Thread replies are also skipped for now;
    pulling conversations_replies per thread is a Week 2 enhancement.
    """
    oldest = (datetime.now() - timedelta(days=days)).timestamp()

    messages = []
    cursor = None
    while len(messages) < max_messages:
        response = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest),
            limit=min(200, max_messages - len(messages)),
            cursor=cursor,
        )
        for msg in response["messages"]:
            if msg.get("subtype"):
                continue
            if not msg.get("text", "").strip():
                continue
            messages.append({
                "user": msg.get("user", "unknown"),
                "text": msg["text"],
                "ts": float(msg["ts"]),
            })
        if not response.get("has_more"):
            break
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    messages.sort(key=lambda m: m["ts"])
    return messages


def messages_to_chunks(
    messages: List[dict],
    channel_name: str,
    user_cache: dict,
    chunk_size: int = 300,
    overlap: int = 30,
) -> List[Chunk]:
    """
    Format a channel's messages into a transcript and chunk it.

    Each line: "[2026-06-12 14:32] Alice: message text"
    A channel header is prepended so every chunk knows where it came from
    (the chunker's overlap means later chunks won't contain the header, but
    the source metadata tag carries the channel name regardless).

    chunk_size=300 matches the Gmail ingestor — chat is even more fragmented
    than email, so smaller, more focused chunks retrieve better than the
    500-word default used for documents.
    """
    lines = [f"Slack channel: #{channel_name}", "---"]
    for msg in messages:
        author = user_cache.get(msg["user"], msg["user"])
        when = datetime.fromtimestamp(msg["ts"]).strftime("%Y-%m-%d %H:%M")
        lines.append(f"[{when}] {author}: {msg['text']}")

    transcript = "\n".join(lines)
    source = f"slack:{channel_name}"

    chunks = chunk_text(
        transcript,
        source=source,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    for chunk in chunks:
        chunk.metadata["channel"] = channel_name

    return chunks


def ingest_slack(
    channel_names: List[str],
    token: str | None = None,
    days: int = 90,
    max_messages: int = 1000,
) -> List[Chunk]:
    """
    Top-level function: resolve channels → fetch → format → return chunks.

    Deterministic re-ingest: chunk IDs in ChromaDB are derived from
    "slack:{channel}::chunk_{i}", so running this again on the same channel
    upserts (refreshes) rather than duplicating — same behavior as files.
    """
    client = _get_client(token)
    user_cache = _build_user_cache(client)

    all_chunks: List[Chunk] = []
    for name in channel_names:
        name = name.lstrip("#").strip()
        if not name:
            continue
        channel_id = _resolve_channel_id(client, name)
        messages = fetch_messages(client, channel_id, days=days, max_messages=max_messages)
        print(f"#{name}: {len(messages)} messages")

        if not messages:
            continue

        chunks = messages_to_chunks(messages, name, user_cache)
        all_chunks.extend(chunks)

    print(f"Created {len(all_chunks)} chunks from {len(channel_names)} channel(s)")
    return all_chunks
