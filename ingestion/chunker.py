"""
Text chunking for ingestion.

Why chunk at all? LLMs and vector DBs work best on focused units of meaning.
A 50-page doc as one blob gives you a useless embedding — it averages everything
to noise. Chunks of ~500 tokens keep semantic focus while staying large enough
to hold context across a paragraph.

Why overlap? If a key sentence sits at a chunk boundary, neither chunk captures
it fully. Overlap (e.g. 50 tokens) ensures boundary content appears in at least
one chunk's full context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)  # source, page, chunk_index, etc.


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Chunk]:
    """
    Split text into overlapping word-based chunks.

    Word-based (not character-based) because token count tracks words much more
    closely than characters — a 500-word chunk is ~650 tokens, safe for most
    embedding models whose limit is 512 tokens.
    """
    words = text.split()
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        chunks.append(Chunk(
            text=chunk_text_str,
            metadata={
                "source": source,
                "chunk_index": chunk_index,
                "word_start": start,
                "word_end": end,
            },
        ))

        chunk_index += 1
        # Move forward by (chunk_size - overlap) so next chunk re-uses the tail
        start += chunk_size - overlap

    return chunks
