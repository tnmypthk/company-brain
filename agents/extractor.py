"""
Claude API agent for extracting structured process knowledge from retrieved chunks.

This is the "generation" half of RAG (Retrieval-Augmented Generation).
Day 1-2 built the retrieval half — finding relevant chunks.
Day 3 adds the generation half — Claude reads those chunks and reasons over them.

The flow:
  user question
    → ChromaDB returns top-N semantically similar chunks   (retrieval)
    → chunks + question sent to Claude API                 (generation)
    → Claude returns structured JSON describing the process

Why structure the output as JSON (not plain text)?
Because the next step is writing a YAML skills file. If Claude returns a paragraph,
you have to parse it — fragile. If Claude returns JSON matching a known schema,
you can validate it and write it directly. This pattern is called "structured output"
and is one of the most important prompt engineering techniques.

Why claude-sonnet-4-6?
Sonnet balances capability and cost well for structured extraction tasks. Opus is
more powerful but ~5x the cost — overkill for extracting a process from 10 chunks.
Haiku is cheaper but sometimes misses nuance in edge case extraction.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _get_client():
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=api_key)


# ── PROMPT DESIGN ──────────────────────────────────────────────────────────────
#
# The system prompt defines Claude's role and output contract.
# Separating role (system) from task (user) is a best practice because:
#   - The system prompt is cached by Anthropic (cost savings on repeated calls)
#   - It keeps the user prompt clean and focused on the specific task
#   - It lets you swap the user prompt without re-explaining the output format
#
SYSTEM_PROMPT = """You are a business process analyst. Your job is to read retrieved
knowledge chunks and extract a structured, actionable process definition.

You must respond with ONLY valid JSON — no markdown, no explanation, no preamble.
The JSON must match this exact schema:

{
  "process": "snake_case_process_name",
  "display_name": "Human Readable Process Name",
  "owner": "team or role who owns this process (infer from context, or 'unknown')",
  "trigger": "what event or condition starts this process",
  "steps": ["step 1", "step 2", "step 3"],
  "edge_cases": ["exception or special case 1", "exception 2"],
  "sources": ["source_name (chunk N)", "source_name (chunk M)"],
  "confidence": "high | medium | low"
}

Confidence rubric:
  high   — multiple chunks with consistent, detailed steps
  medium — some relevant information but gaps exist
  low    — only tangential mentions, process is inferred

If the chunks contain no relevant information for the requested process,
return confidence: "low" and fill steps with your best inference labeled
as "(inferred — not found in knowledge base)".
"""

# ── USER PROMPT TEMPLATE ────────────────────────────────────────────────────────
#
# The user prompt has two parts:
#   1. The retrieved context (chunks from ChromaDB)
#   2. The specific extraction task
#
# Why include the source metadata alongside each chunk?
# Claude needs to populate the "sources" field. Without knowing which chunk came
# from which document, it can't cite sources accurately.
#
# Why number the chunks?
# "Sources: [chunk 3]" is more useful than "Sources: [some text blob]".
# Numbered chunks let Claude reference specific evidence.
#
def _build_user_prompt(topic: str, chunks: list[dict]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks):
        source = chunk["metadata"].get("source", "unknown")
        chunk_idx = chunk["metadata"].get("chunk_index", i)
        context_parts.append(
            f"[Chunk {i+1} | Source: {source} | Index: {chunk_idx}]\n{chunk['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    return f"""Here are the {len(chunks)} most relevant knowledge chunks for this request:

{context}

---

Extract the structured process for: "{topic}"

Use only what is explicitly stated in the chunks above. For any field you cannot
determine from the chunks, make a reasonable inference and note it is inferred.
"""


def extract_process(topic: str, n_chunks: int = 10) -> dict[str, Any]:
    """
    Main entry point: retrieve relevant chunks and extract a structured process.

    Returns a dict matching the JSON schema above, plus a generated_at timestamp
    added here (not by Claude — timestamps are deterministic code, not LLM output).

    Why add generated_at in code and not in the prompt?
    LLMs don't know the current time reliably. Asking Claude to fill in a timestamp
    invites hallucination. Generate it here where it's guaranteed to be accurate.
    """
    from storage.chroma import query as chroma_query

    chunks = chroma_query(topic, n_results=n_chunks)

    if not chunks:
        return {
            "process": topic.lower().replace(" ", "_"),
            "display_name": topic,
            "owner": "unknown",
            "trigger": "unknown",
            "steps": ["(no relevant knowledge found — ingest documents first)"],
            "edge_cases": [],
            "sources": [],
            "confidence": "low",
            "generated_at": datetime.now().isoformat(),
        }

    client = _get_client()

    # Why messages API (not completions)?
    # The messages API is Claude's modern interface. It supports multi-turn
    # conversations, system prompts, and is what all current Claude models use.
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_user_prompt(topic, chunks)}
        ],
    )

    raw_text = response.content[0].text.strip()

    # Parse the JSON Claude returned
    # We validate it has the required keys before passing it downstream.
    # If Claude returns malformed JSON (rare but possible), we surface a clear error.
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Claude returned non-JSON output. Raw response:\n{raw_text}\nError: {e}"
        )

    required_keys = {"process", "display_name", "owner", "trigger", "steps",
                     "edge_cases", "sources", "confidence"}
    missing = required_keys - set(result.keys())
    if missing:
        raise ValueError(f"Claude's response missing keys: {missing}. Got: {result}")

    result["generated_at"] = datetime.now().isoformat()

    # Token usage logging — useful for understanding API costs as the project grows
    usage = response.usage
    print(f"  Tokens: {usage.input_tokens} in, {usage.output_tokens} out")

    return result
