"""
CLI entry point for ingestion.

Usage:
  python ingest.py file path/to/doc.pdf
  python ingest.py file path/to/doc.docx
  python ingest.py drive <file_id>
  python ingest.py folder <folder_id>
  python ingest.py gmail               (last 90 days, up to 200 emails)
  python ingest.py gmail 30            (last 30 days)
  python ingest.py stats
  python ingest.py query "how do we handle customer escalations"
"""

import sys
import warnings
warnings.filterwarnings("ignore", category=Warning)

from storage.chroma import collection_stats, query, store_chunks


def cmd_file(path: str):
    from ingestion.file_upload import ingest_file
    chunks = ingest_file(path)
    print(f"Extracted {len(chunks)} chunks from {path}")
    stored = store_chunks(chunks)
    print(f"Stored {stored} chunks in ChromaDB")


def cmd_drive(file_id: str):
    from ingestion.drive import ingest_drive_file
    chunks = ingest_drive_file(file_id)
    print(f"Extracted {len(chunks)} chunks from Drive file {file_id}")
    stored = store_chunks(chunks)
    print(f"Stored {stored} chunks in ChromaDB")


def cmd_gmail(days: int = 90):
    from ingestion.gmail import ingest_gmail
    chunks = ingest_gmail(days=days)
    stored = store_chunks(chunks)
    print(f"Stored {stored} chunks from Gmail")


def cmd_folder(folder_id: str):
    from ingestion.drive import ingest_folder
    chunks = ingest_folder(folder_id)
    stored = store_chunks(chunks)
    print(f"\nTotal: stored {stored} chunks from folder {folder_id}")


def cmd_stats():
    stats = collection_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")


def cmd_query(text: str):
    results = query(text, n_results=5)
    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} (distance={r['distance']:.3f}) ---")
        print(f"Source: {r['metadata'].get('source', 'unknown')}")
        print(r["text"][:300])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "file" and len(sys.argv) == 3:
        cmd_file(sys.argv[2])
    elif cmd == "drive" and len(sys.argv) == 3:
        cmd_drive(sys.argv[2])
    elif cmd == "gmail":
        days = int(sys.argv[2]) if len(sys.argv) == 3 else 90
        cmd_gmail(days)
    elif cmd == "folder" and len(sys.argv) == 3:
        cmd_folder(sys.argv[2])
    elif cmd == "stats":
        cmd_stats()
    elif cmd == "query" and len(sys.argv) >= 3:
        cmd_query(" ".join(sys.argv[2:]))
    else:
        print(__doc__)
        sys.exit(1)
