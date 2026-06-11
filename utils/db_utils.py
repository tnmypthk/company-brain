"""Utility commands for managing the ChromaDB collection."""

from storage.chroma import _get_collection


def delete_source(source: str):
    """Remove all chunks from a specific source."""
    collection = _get_collection()
    all_items = collection.get(include=["metadatas"])
    ids_to_delete = [
        id_ for id_, meta in zip(all_items["ids"], all_items["metadatas"])
        if meta.get("source") == source
    ]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        print(f"Deleted {len(ids_to_delete)} chunks from '{source}'")
    else:
        print(f"No chunks found for source '{source}'")


def list_sources():
    """Print all sources and their chunk counts."""
    collection = _get_collection()
    all_items = collection.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for meta in all_items["metadatas"]:
        src = meta.get("source", "unknown")
        counts[src] = counts.get(src, 0) + 1
    for src, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {count:3d} chunks — {src}")


def nuke():
    """Delete everything in the collection. Use with care."""
    collection = _get_collection()
    all_items = collection.get()
    if all_items["ids"]:
        collection.delete(ids=all_items["ids"])
        print(f"Deleted {len(all_items['ids'])} chunks — collection is now empty")
    else:
        print("Collection already empty")
