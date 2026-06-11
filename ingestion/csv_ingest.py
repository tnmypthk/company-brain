"""
CSV ingestion — converts rows into readable prose sentences before chunking.

Why not chunk raw CSV? Vector embeddings measure semantic meaning. A row like
"121958,-2.28,1600.89,0,Low" has no meaning the model can latch onto. Converting
it to "Transaction at time 121958 with amount $1600.89, predicted Low risk,
classified as non-fraud." gives the embedder actual English to work with.

The row-to-sentence conversion is schema-aware: you pass a template or let it
auto-generate a generic sentence. For well-known schemas (fraud, sales, etc.)
a custom template produces far better retrieval.
"""

from __future__ import annotations

import csv
import io
from typing import Callable, List, Optional

from ingestion.chunker import Chunk


def _default_row_to_text(headers: list[str], row: dict) -> str:
    """Generic fallback: 'key: value, key: value, ...' """
    parts = [f"{h}: {row[h]}" for h in headers if row.get(h, "").strip()]
    return ", ".join(parts)


def _fraud_row_to_text(headers: list[str], row: dict) -> str:
    """Human-readable sentence for credit card fraud datasets."""
    amount = row.get("Amount", "unknown")
    risk = row.get("risk_level", "unknown")
    label = row.get("predicted_label", row.get("Class", "unknown"))
    prob = row.get("prediction_probability", "")
    time = row.get("Time", "")

    fraud_str = "fraud" if str(label) == "1" else "non-fraud"
    prob_str = f" (confidence: {float(prob):.1%})" if prob else ""
    time_str = f" at time {time}" if time else ""

    return (
        f"Transaction{time_str} of ${amount} was classified as {fraud_str}{prob_str}. "
        f"Risk level: {risk}."
    )


# Registry: map a keyword in the source name to a row converter
_CONVERTERS: dict[str, Callable] = {
    "fraud": _fraud_row_to_text,
}


def _pick_converter(source: str) -> Callable:
    for keyword, fn in _CONVERTERS.items():
        if keyword in source.lower():
            return fn
    return _default_row_to_text


def ingest_csv_bytes(
    content: bytes,
    source: str,
    rows_per_chunk: int = 20,
    max_rows: int = 500,
) -> List[Chunk]:
    """
    Convert CSV rows to prose sentences, then group into chunks.

    rows_per_chunk=20 means each chunk holds 20 row-sentences. This keeps
    chunks focused (one topic per chunk) while staying within embedding limits.

    max_rows=500 prevents accidentally ingesting a 1M-row dataset — for a
    portfolio demo, a representative sample is all you need.
    """
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    converter = _pick_converter(source)

    chunks: List[Chunk] = []
    batch: list[str] = []
    chunk_index = 0
    row_count = 0

    for row in reader:
        if row_count >= max_rows:
            break
        sentence = converter(headers, row)
        batch.append(sentence)
        row_count += 1

        if len(batch) >= rows_per_chunk:
            chunks.append(Chunk(
                text="\n".join(batch),
                metadata={"source": source, "chunk_index": chunk_index,
                          "row_start": chunk_index * rows_per_chunk,
                          "row_end": row_count},
            ))
            batch = []
            chunk_index += 1

    if batch:
        chunks.append(Chunk(
            text="\n".join(batch),
            metadata={"source": source, "chunk_index": chunk_index,
                      "row_start": chunk_index * rows_per_chunk,
                      "row_end": row_count},
        ))

    return chunks
