"""
Company Brain — Streamlit dashboard.

Four tabs:
  Ingest  — drag & drop PDF/DOCX files into ChromaDB
  Query   — semantic search across everything stored
  Skills  — generate structured process YAML files using Claude API (RAG)
  Stats   — what's in the DB right now
"""

import streamlit as st

st.set_page_config(
    page_title="Company Brain",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Company Brain")
st.caption("Ingest company knowledge. Query it with natural language.")

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

    # Google Drive section — shows setup instructions if credentials.json is missing
    st.subheader("Or ingest from Google Drive")
    from pathlib import Path
    if not Path("credentials.json").exists():
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

    # Gmail section
    st.subheader("Or ingest from Gmail")
    from pathlib import Path
    if not Path("credentials.json").exists():
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


# ── QUERY TAB ─────────────────────────────────────────────────────────────────
with query_tab:
    st.header("Query Your Knowledge Base")
    st.write("Ask anything. Results are ranked by semantic similarity — not keyword match.")

    query_text = st.text_input(
        "What do you want to know?",
        placeholder="e.g. how do we handle customer escalations?",
    )

    col1, col2 = st.columns([1, 3])
    n_results = col1.slider("Results to show", min_value=1, max_value=10, value=5)

    if query_text:
        from storage.chroma import query

        with st.spinner("Searching..."):
            results = query(query_text, n_results=n_results)

        if not results:
            st.warning("No results found. Try ingesting some documents first.")
        else:
            st.write(f"**{len(results)} results** for: *{query_text}*")
            st.divider()

            for i, r in enumerate(results, 1):
                source = r["metadata"].get("source", "unknown")
                chunk_idx = r["metadata"].get("chunk_index", "?")
                distance = r["distance"]

                # Convert distance to a 0-100 relevance score for display.
                # Cosine distance is 0 (identical) to 2 (opposite). We map to
                # 100 (perfect) to 0 (unrelated) so it reads naturally.
                relevance = max(0, int((1 - distance) * 100))

                with st.expander(f"Result {i} — {source} (chunk {chunk_idx}) — {relevance}% relevant"):
                    st.progress(relevance)
                    st.write(r["text"])


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
    n_chunks = col1.slider("Chunks to retrieve", min_value=3, max_value=15, value=10)

    # Session state holds the last generated result so the Save button works
    # without re-running the expensive Claude API call.
    # Why session_state? Streamlit re-runs the entire script on every interaction.
    # Without session_state, clicking "Save" would lose the generated result from
    # the "Generate" button click.
    if "last_generated" not in st.session_state:
        st.session_state.last_generated = None

    if st.button("Generate Skills File", type="primary", disabled=not topic):
        from agents.extractor import extract_process
        from agents.skills_writer import process_to_yaml

        with st.spinner(f"Retrieving chunks and calling Claude API..."):
            try:
                process = extract_process(topic, n_chunks=n_chunks)
                st.session_state.last_generated = process
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.last_generated = None

    if st.session_state.last_generated:
        from agents.skills_writer import process_to_yaml, save_skills_file

        process = st.session_state.last_generated
        yaml_str = process_to_yaml(process)

        st.divider()
        conf = process.get("confidence", "low")
        conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
        st.write(f"**{process.get('display_name', process['process'])}** — Confidence: {conf_color} {conf.upper()}")

        st.code(yaml_str, language="yaml")

        if st.button("💾 Save Skills File"):
            path = save_skills_file(process)
            st.success(f"Saved to {path}")
            st.session_state.last_generated = None

    # ── Saved skills library ──
    st.divider()
    st.subheader("Saved Skills Library")

    from agents.skills_writer import list_skills_files
    saved = list_skills_files()

    if not saved:
        st.info("No skills files saved yet. Generate and save one above.")
    else:
        for skill in saved:
            conf = skill["confidence"]
            conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
            with st.expander(f"{conf_color} {skill['display_name']} — owned by {skill['owner']}"):
                st.caption(f"Generated: {skill['generated_at']}  |  File: {skill['filename']}")
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
        st.info("Nothing ingested yet. Go to the Ingest tab to add documents.")
    else:
        # Fetch all metadata to build a per-source summary
        all_items = collection.get(include=["metadatas"])
        source_counts: dict[str, int] = {}
        for meta in all_items["metadatas"]:
            src = meta.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            st.write(f"- **{src}** — {count} chunk{'s' if count != 1 else ''}")
