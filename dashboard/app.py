"""
Company Brain — Streamlit dashboard.

Four tabs:
  Ingest  — drag & drop PDF/DOCX files, Google Drive, Gmail, or Slack into ChromaDB
  Query   — synthesized answers with citations, or raw semantic search
  Skills  — 2-agent pipeline (extractor → validator) producing process YAML files
  Stats   — what's in the DB right now
"""

import streamlit as st

from utils.config import get_config, get_secret, running_on_cloud

# Retrieval defaults for the sliders/calls below come from config.yaml.
_RETRIEVAL = get_config()["retrieval"]

st.set_page_config(
    page_title="Company Brain",
    page_icon="🧠",
    layout="wide",
)

# ── CUSTOM STYLING ─────────────────────────────────────────────────────────────
# Pure presentation: a small CSS layer so the app reads as a product, not a
# dev tool. Injected once via st.markdown(unsafe_allow_html=True). Every class
# here is cosmetic — no behavior changes anywhere in this file.
st.markdown(
    """
    <style>
      /* Metric cards — subtle border + raised background */
      div[data-testid="stMetric"] {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 16px 18px;
      }
      div[data-testid="stMetric"] label { opacity: 0.7; }

      /* Tab bar — more breathing room, rounded tabs, accent on active */
      .stTabs [data-baseweb="tab-list"] { gap: 6px; }
      .stTabs [data-baseweb="tab"] {
          border-radius: 8px 8px 0 0;
          padding: 8px 18px;
      }
      .stTabs [aria-selected="true"] {
          background: rgba(107, 138, 253, 0.12);
      }

      /* Source-type badges (gmail=red, slack=purple, drive=blue, file=grey) */
      .source-badge {
          display: inline-block;
          padding: 2px 10px;
          border-radius: 999px;
          font-size: 0.70rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: #fff;
      }
      .src-gmail { background: #d93025; }
      .src-slack { background: #6b3fa0; }
      .src-drive { background: #1a73e8; }
      .src-file  { background: #5f6368; }

      /* Confidence chips (high=green, medium=yellow, low=red) */
      .confidence-chip {
          display: inline-block;
          padding: 2px 12px;
          border-radius: 999px;
          font-size: 0.70rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
      }
      .conf-high   { background: rgba(46, 160, 67, 0.18);  color: #3fb950; }
      .conf-medium { background: rgba(210, 153, 34, 0.18); color: #d29922; }
      .conf-low    { background: rgba(218, 54, 51, 0.18);  color: #f85149; }

      /* Source cards (Stats grid) */
      .source-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 14px 16px;
          margin-bottom: 10px;
          min-height: 96px;
      }
      .source-card .src-name {
          font-weight: 600;
          font-size: 0.95rem;
          word-break: break-word;
          margin-top: 6px;
      }
      .source-card .src-count { opacity: 0.6; font-size: 0.8rem; margin-top: 2px; }

      /* Skill cards (Saved library) */
      .skill-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 14px 18px;
          margin-bottom: 4px;
      }
      .skill-card .skill-name { font-size: 1.15rem; font-weight: 700; }
      .skill-card .skill-owner { opacity: 0.75; font-size: 0.9rem; }
      .skill-card .skill-date { font-size: 0.78rem; opacity: 0.5; margin-top: 4px; }

      /* Answer card — subtle left-border accent. :has() targets only the
         bordered container that wraps the synthesized answer (marked with an
         .answer-accent sentinel), so other bordered containers are untouched. */
      div[data-testid="stVerticalBlockBorderWrapper"]:has(.answer-accent) {
          border-left: 4px solid #6b8afd;
          background: rgba(107, 138, 253, 0.04);
      }

      /* Empty state */
      .empty-state { text-align: center; padding: 44px 16px; }
      .empty-state .es-title { font-size: 1.6rem; font-weight: 700; }
      .empty-state .es-sub { opacity: 0.6; margin-top: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── PRESENTATION HELPERS ───────────────────────────────────────────────────────
import html as _html
import os as _os

# icon + CSS class per source type
_SOURCE_META = {
    "gmail": ("📧", "src-gmail"),
    "slack": ("💬", "src-slack"),
    "drive": ("📁", "src-drive"),
    "file":  ("📄", "src-file"),
}


def classify_source(src: str):
    """Return (type, clean_display_name) for a raw source string.

    Ingestors prefix their sources: 'gmail:Subject', 'slack:channel',
    'drive:name'. File uploads have no prefix — just a filename or full path —
    so anything unprefixed is a file, and we strip the directory for display.
    """
    for kind in ("gmail", "slack", "drive"):
        if src.startswith(kind + ":"):
            name = src[len(kind) + 1:]
            if kind == "slack":
                name = "#" + name
            return kind, name
    return "file", _os.path.basename(src) or src


def source_badge(kind: str) -> str:
    _, cls = _SOURCE_META.get(kind, _SOURCE_META["file"])
    return f'<span class="source-badge {cls}">{kind}</span>'


def source_icon(kind: str) -> str:
    icon, _ = _SOURCE_META.get(kind, _SOURCE_META["file"])
    return icon


def confidence_chip(conf: str) -> str:
    conf = (conf or "low").lower()
    cls = {"high": "conf-high", "medium": "conf-medium", "low": "conf-low"}.get(conf, "conf-low")
    return f'<span class="confidence-chip {cls}">{_html.escape(conf)}</span>'


st.title("🧠 Company Brain")
st.caption("Ingest company knowledge. Query it with natural language.")


# ── HERO METRICS ───────────────────────────────────────────────────────────────
# Real numbers, computed at load: distinct sources + total chunks from
# ChromaDB, and saved skills files from disk. (ChromaDB already loads every
# run via the Stats tab, so this adds no extra startup cost.)
from storage.chroma import collection_stats as _hero_stats, _get_collection as _hero_coll
from agents.skills_writer import list_skills_files as _hero_skills

_stats = _hero_stats()
_total_chunks = _stats["total_chunks"]
try:
    _hero_metas = _hero_coll().get(include=["metadatas"])["metadatas"] if _total_chunks else []
except Exception:
    _hero_metas = []
_distinct_sources = {m.get("source", "unknown") for m in _hero_metas}
_skills_generated = len(_hero_skills())

_h1, _h2, _h3 = st.columns(3)
_h1.metric("Total Sources", len(_distinct_sources))
_h2.metric("Total Chunks", _total_chunks)
_h3.metric("Skills Generated", _skills_generated)

# Empty state — first-run guidance pointing at the Ingest tab (just below).
if _total_chunks == 0:
    st.markdown(
        """
        <div class="empty-state">
          <div class="es-title">🧠 No knowledge ingested yet</div>
          <div class="es-sub">⬇️ &nbsp; Open the <b>📥 Ingest</b> tab below to add your first documents</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")  # spacer above the tab bar

ingest_tab, query_tab, skills_tab, stats_tab = st.tabs(["📥 Ingest", "🔍 Query", "🗂 Skills", "📊 Stats"])


# ── INGEST TAB ────────────────────────────────────────────────────────────────
with ingest_tab:
    st.header("Ingest Documents")
    st.write("Upload PDF or DOCX files. Each file is chunked and embedded into ChromaDB.")

    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("Ingest All", type="primary"):
            from ingestion.file_upload import ingest_file_bytes
            from storage.chroma import store_chunks

            total_chunks = 0
            for f in uploaded_files:
                with st.spinner(f"Processing {f.name}..."):
                    try:
                        # f.read() gives us bytes — exactly what ingest_file_bytes expects
                        chunks = ingest_file_bytes(f.read(), f.name)
                        stored = store_chunks(chunks)
                        total_chunks += stored
                        st.success(f"✓ {f.name} — {stored} chunks stored")
                    except Exception as e:
                        st.error(f"✗ {f.name} — {e}")

            if total_chunks:
                st.balloons()
                st.info(f"Total: {total_chunks} chunks added to ChromaDB")

    st.divider()

    # Google Drive section.
    # On a deployed server, file-based Google OAuth can't work (no browser to
    # complete the consent flow, no credentials.json on disk) — so we detect
    # the cloud and show a clear message instead of letting run_local_server()
    # hang the request. Locally, we fall back to the existing setup flow.
    st.subheader("Or ingest from Google Drive")
    from pathlib import Path
    if running_on_cloud():
        st.info(
            "🔒 Google Drive ingestion needs interactive OAuth on a local "
            "machine (a browser consent flow + `credentials.json` on disk), "
            "neither of which exists on the hosted demo. Run Company Brain "
            "locally to ingest from Drive. File upload and Slack work here."
        )
    elif not Path("credentials.json").exists():
        with st.expander("Setup required — click to see instructions"):
            st.markdown("""
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Drive API**
3. Create **OAuth 2.0 credentials** (Desktop app) → Download as `credentials.json`
4. Place `credentials.json` in your project root (`~/company-brain/`)
5. Refresh this page
            """)
    else:
        drive_input = st.text_input("Paste a Drive file ID or folder ID")
        col1, col2 = st.columns(2)
        ingest_file_btn = col1.button("Ingest File")
        ingest_folder_btn = col2.button("Ingest Folder")

        if drive_input and (ingest_file_btn or ingest_folder_btn):
            from storage.chroma import store_chunks
            with st.spinner("Connecting to Google Drive..."):
                try:
                    if ingest_file_btn:
                        from ingestion.drive import ingest_drive_file
                        chunks = ingest_drive_file(drive_input)
                    else:
                        from ingestion.drive import ingest_folder
                        chunks = ingest_folder(drive_input)
                    stored = store_chunks(chunks)
                    st.success(f"✓ {stored} chunks stored from Drive")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # Gmail section — same cloud constraint as Drive (shared OAuth flow).
    st.subheader("Or ingest from Gmail")
    from pathlib import Path
    if running_on_cloud():
        st.info(
            "🔒 Gmail ingestion needs interactive OAuth on a local machine, "
            "which isn't available on the hosted demo. Run Company Brain "
            "locally to ingest from Gmail."
        )
    elif not Path("credentials.json").exists():
        st.info("Add credentials.json to enable Gmail ingestion.")
    else:
        col1, col2 = st.columns(2)
        days = col1.slider("Days to look back", min_value=7, max_value=365, value=90)
        max_emails = col2.slider("Max emails", min_value=10, max_value=500, value=200)

        if st.button("Ingest Gmail"):
            from ingestion.gmail import ingest_gmail
            from storage.chroma import store_chunks
            with st.spinner(f"Fetching last {days} days of email... (this may take a minute)"):
                try:
                    chunks = ingest_gmail(days=days, max_emails=max_emails)
                    stored = store_chunks(chunks)
                    st.success(f"✓ {stored} chunks stored from Gmail")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # Slack section
    st.subheader("Or ingest from Slack")
    st.write(
        "Needs a bot token (`xoxb-...`) with `channels:read`, `channels:history`, "
        "and `users:read` scopes — and the bot must be invited to each channel."
    )

    # type="password" masks the token on screen. We pass it straight to the
    # ingestor and never write it to disk; set SLACK_BOT_TOKEN in .env (local)
    # or the Streamlit Cloud secrets manager to skip typing it each time.
    slack_token = st.text_input(
        "Bot token",
        type="password",
        placeholder="xoxb-... (leave empty to use SLACK_BOT_TOKEN from secrets/.env)",
    )
    slack_channels = st.text_input(
        "Channel names (comma-separated)",
        placeholder="e.g. engineering, customer-support",
    )
    slack_days = st.slider("Days of history", min_value=7, max_value=365, value=90, key="slack_days")

    if st.button("Ingest Slack", disabled=not slack_channels):
        from ingestion.slack import ingest_slack
        from storage.chroma import store_chunks

        channels = [c.strip() for c in slack_channels.split(",") if c.strip()]
        with st.spinner(f"Fetching {slack_days} days from {len(channels)} channel(s)..."):
            try:
                chunks = ingest_slack(
                    channels,
                    token=slack_token or get_secret("SLACK_BOT_TOKEN"),
                    days=slack_days,
                )
                stored = store_chunks(chunks)
                st.success(f"✓ {stored} chunks stored from Slack")
            except Exception as e:
                st.error(f"Error: {e}")


# ── QUERY TAB ─────────────────────────────────────────────────────────────────
with query_tab:
    st.header("Query Your Knowledge Base")

    query_text = st.text_input(
        "What do you want to know?",
        placeholder="e.g. how do we handle customer escalations?",
    )

    # Two modes for the same retrieval:
    #   Get Answer — RAG synthesis: chunks go to Claude, you get a cited answer
    #   Raw chunks — Day 1 behavior: see exactly what semantic search returns
    # Raw view stays first-class because it's the debugging tool — when an
    # answer looks wrong, the first question is "what did retrieval feed it?"
    mode = st.radio(
        "Mode",
        ["💬 Get Answer", "📄 Raw chunks"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # Shared renderer for both views. expandable=False is for use INSIDE the
    # answer view's "Show source chunks" expander — Streamlit doesn't allow
    # nesting expanders, so there we render flat blocks instead.
    def _render_chunks(results, expandable=True):
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "unknown")
            chunk_idx = r["metadata"].get("chunk_index", "?")
            distance = r["distance"]

            # Convert distance to a 0-100 relevance score for display.
            # Cosine distance is 0 (identical) to 2 (opposite). We map to
            # 100 (perfect) to 0 (unrelated) so it reads naturally.
            relevance = max(0, int((1 - distance) * 100))

            label = f"Result {i} — {source} (chunk {chunk_idx}) — {relevance}% relevant"
            if expandable:
                with st.expander(label):
                    st.progress(relevance)
                    st.write(r["text"])
            else:
                st.markdown(f"**{label}**")
                st.progress(relevance)
                st.write(r["text"])
                st.divider()

    if mode == "💬 Get Answer":
        if query_text:
            from agents.answerer import answer_question

            with st.spinner("Retrieving chunks and synthesizing answer..."):
                try:
                    result = answer_question(query_text, n_chunks=_RETRIEVAL["answer_chunks"])
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result:
                # Styled card with a left-border accent. The .answer-accent
                # sentinel lets the CSS target just this bordered container;
                # the answer itself renders as normal markdown inside it.
                with st.container(border=True):
                    st.markdown('<div class="answer-accent"></div>', unsafe_allow_html=True)
                    st.markdown(result["answer"])

                if result["chunks"]:
                    st.divider()
                    with st.expander(f"📄 Show source chunks ({len(result['chunks'])} retrieved)"):
                        _render_chunks(result["chunks"], expandable=False)

    else:  # Raw chunks mode — unchanged Day 1-2 behavior
        st.write("Results are ranked by semantic similarity — not keyword match.")
        col1, col2 = st.columns([1, 3])
        n_results = col1.slider("Results to show", min_value=1, max_value=10, value=_RETRIEVAL["raw_results"])

        if query_text:
            from storage.chroma import query

            with st.spinner("Searching..."):
                results = query(query_text, n_results=n_results)

            if not results:
                st.warning("No results found. Try ingesting some documents first.")
            else:
                st.write(f"**{len(results)} results** for: *{query_text}*")
                st.divider()
                _render_chunks(results)


# ── SKILLS TAB ────────────────────────────────────────────────────────────────
with skills_tab:
    st.header("Skills File Generator")
    st.write(
        "Describe a process in plain English. Claude will retrieve the most relevant "
        "knowledge chunks and extract a structured, reusable skills file."
    )

    topic = st.text_input(
        "What process do you want to document?",
        placeholder="e.g. how do we handle customer refunds",
    )

    col1, col2 = st.columns([1, 3])
    n_chunks = col1.slider("Chunks to retrieve", min_value=3, max_value=15, value=_RETRIEVAL["skills_chunks"])

    # Session state holds the last generated result so the Save button works
    # without re-running the expensive Claude API call.
    # Why session_state? Streamlit re-runs the entire script on every interaction.
    # Without session_state, clicking "Save" would lose the generated result from
    # the "Generate" button click.
    # Two slots: the extractor's draft and the validator's improved version.
    # Both are kept so we can render them side by side — seeing the diff is
    # how a human learns to trust (or distrust) the pipeline.
    if "last_generated" not in st.session_state:
        st.session_state.last_generated = None
    if "last_validated" not in st.session_state:
        st.session_state.last_validated = None

    if st.button("Generate Skills File", type="primary", disabled=not topic):
        from agents.extractor import extract_process
        from agents.validator import validate_process

        # Stage 1 — extractor (RAG: retrieve chunks, draft the process)
        with st.spinner("Agent 1/2 — extracting draft from knowledge base..."):
            try:
                draft = extract_process(topic, n_chunks=n_chunks)
                st.session_state.last_generated = draft
                st.session_state.last_validated = None
            except Exception as e:
                st.error(f"Extractor error: {e}")
                st.session_state.last_generated = None
                st.session_state.last_validated = None
                draft = None

        # Stage 2 — validator (review and improve the draft). If it fails we
        # still have the draft: a degraded result beats no result.
        if draft:
            with st.spinner("Agent 2/2 — validating and improving the draft..."):
                try:
                    st.session_state.last_validated = validate_process(draft)
                except Exception as e:
                    st.warning(f"Validator failed ({e}) — showing unvalidated draft only.")

    if st.session_state.last_generated:
        from agents.skills_writer import process_to_yaml, save_skills_file

        draft = st.session_state.last_generated
        validated = st.session_state.last_validated

        st.divider()

        conf_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}

        # Side-by-side: what the extractor drafted vs. what the validator
        # shipped. Confidence can move in either direction — a drop means
        # the validator found the draft was overselling its sourcing.
        col_draft, col_final = st.columns(2)

        with col_draft:
            st.subheader("📝 Draft (extractor)")
            conf = draft.get("confidence", "low")
            st.write(f"Confidence: {conf_colors.get(conf, '⚪')} {conf.upper()}")
            st.code(process_to_yaml(draft), language="yaml")

        with col_final:
            st.subheader("✅ Improved (validator)")
            if validated:
                conf = validated.get("confidence", "low")
                st.write(f"Confidence: {conf_colors.get(conf, '⚪')} {conf.upper()}")
                st.code(process_to_yaml(validated), language="yaml")
            else:
                st.info("Validation unavailable for this run.")

        # The validator's review notes, pulled out of the YAML for visibility —
        # this is the audit trail a human reads before trusting the file.
        if validated and validated.get("validation_notes"):
            with st.expander("🔍 What the validator checked and changed", expanded=True):
                for note in validated["validation_notes"]:
                    st.write(f"- {note}")

        # Save the validated version when we have one; the draft otherwise.
        final = validated or draft
        label = "💾 Save Validated Skills File" if validated else "💾 Save Draft (unvalidated)"
        if st.button(label):
            path = save_skills_file(final)
            st.success(f"Saved to {path}")
            st.session_state.last_generated = None
            st.session_state.last_validated = None

    # ── Saved skills library ──
    st.divider()
    st.subheader("Saved Skills Library")

    from agents.skills_writer import list_skills_files
    saved = list_skills_files()

    if not saved:
        st.info("No skills files saved yet. Generate and save one above.")
    else:
        for skill in saved:
            name = _html.escape(str(skill["display_name"]))
            owner = _html.escape(str(skill["owner"]))
            generated = _html.escape(str(skill["generated_at"]))
            filename = _html.escape(str(skill["filename"]))

            # Styled header card: process name (bold/large) on the left,
            # confidence chip + owner on the right, generated date small/grey.
            st.markdown(
                f"""
                <div class="skill-card">
                  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                    <span class="skill-name">{name}</span>
                    <span style="white-space:nowrap;">{confidence_chip(skill["confidence"])}
                      &nbsp; <span class="skill-owner">👤 {owner}</span></span>
                  </div>
                  <div class="skill-date">Generated {generated} · {filename}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Full YAML stays one click away (expand on click).
            with st.expander("View full definition"):
                content = skill["path"].read_text(encoding="utf-8")
                st.code(content, language="yaml")


# ── STATS TAB ─────────────────────────────────────────────────────────────────
with stats_tab:
    st.header("Knowledge Base Stats")

    from storage.chroma import collection_stats, _get_collection

    stats = collection_stats()

    col1, col2 = st.columns(2)
    col1.metric("Total Chunks", stats["total_chunks"])
    col2.metric("Embedding Model", stats["embed_model"])

    st.divider()

    # Show what sources are stored, with chunk counts per source
    st.subheader("Ingested Sources")
    collection = _get_collection()

    if stats["total_chunks"] == 0:
        st.markdown(
            """
            <div class="empty-state">
              <div class="es-title">🧠 No knowledge ingested yet</div>
              <div class="es-sub">⬆️ &nbsp; Use the <b>📥 Ingest</b> tab to add documents</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Fetch all metadata to build a per-source summary
        all_items = collection.get(include=["metadatas"])
        source_counts: dict[str, int] = {}
        for meta in all_items["metadatas"]:
            src = meta.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        # Styled grid: each source is a card with a type icon + badge, the
        # cleaned name (no full path), and a chunk-count line. Laid out 3-wide.
        ordered = sorted(source_counts.items(), key=lambda x: -x[1])
        per_row = 3
        for i in range(0, len(ordered), per_row):
            cols = st.columns(per_row)
            for col, (src, count) in zip(cols, ordered[i:i + per_row]):
                kind, clean_name = classify_source(src)
                plural = "s" if count != 1 else ""
                with col:
                    st.markdown(
                        f"""
                        <div class="source-card">
                          <div>{source_icon(kind)} &nbsp; {source_badge(kind)}</div>
                          <div class="src-name">{_html.escape(clean_name)}</div>
                          <div class="src-count">{count} chunk{plural}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
