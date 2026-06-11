"""
Company Brain — Streamlit dashboard.

Three tabs:
  Ingest  — drag & drop PDF/DOCX files into ChromaDB
  Query   — semantic search across everything stored
  Stats   — what's in the DB right now

Why Streamlit? It turns Python functions into a web UI with almost no boilerplate.
st.file_uploader() gives you bytes in memory — that's why we built ingest_file_bytes()
yesterday instead of only supporting file paths.
"""

import streamlit as st

st.set_page_config(
    page_title="Company Brain",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Company Brain")
st.caption("Ingest company knowledge. Query it with natural language.")

ingest_tab, query_tab, stats_tab = st.tabs(["📥 Ingest", "🔍 Query", "📊 Stats"])


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
