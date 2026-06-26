"""
Claude API agent that validates and improves extracted skills files.

This is the second half of a 2-agent pipeline:

  topic → [extractor] → draft skills dict → [validator] → final skills dict
            (Day 3)                            (Day 4)

WHY TWO AGENTS INSTEAD OF ONE BIGGER PROMPT?

1. Generation and critique are different jobs. The extractor is juggling
   retrieval context, schema compliance, and synthesis all at once. Asking it
   to *also* self-review in the same pass doesn't work well — a model that
   just produced a vague step tends to defend it, because the same reasoning
   that produced the flaw is still sitting in its context. The validator
   starts with a FRESH context containing only the draft, so it reads the
   steps the way a new employee would: "could I actually follow this?"

2. Focused prompts beat kitchen-sink prompts. Each agent gets a short, sharp
   role. Stuffing extraction rules + review rubric + revision instructions
   into one prompt dilutes all three (and models follow long prompts less
   reliably than short ones).

3. Separation gives you a quality dial. The generator can run on a cheaper
   model and the critic on a stronger one (what we do here), you can A/B test
   either half independently, and you can log where quality problems come
   from — extraction or review.

The pattern is called "generator–critic" (or actor–critic / reflection) and
it's one of the most reliable ways to lift LLM output quality.

WHY claude-opus-4-8 FOR THE VALIDATOR?
Critique is where model strength pays off most: spotting a logically-impossible
step ordering or an unrealistic edge case requires more reasoning than
reformatting chunks into JSON. Pairing a cheaper generator (the extractor's
Sonnet) with a stronger critic (Opus) is the classic cost/quality split.

WHY STRUCTURED OUTPUTS HERE (vs. Day 3's "respond with ONLY valid JSON")?
The extractor asks nicely for JSON and then hopes json.loads() works — that's
prompt-level enforcement, and it can fail (markdown fences, trailing prose).
Day 4 upgrade: the API's `output_config.format` accepts a JSON Schema and
*guarantees* the response parses and matches the schema. The contract moves
from the prompt (a suggestion) into the API (a constraint). No retry logic,
no "Claude returned non-JSON" errors.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from utils.config import get_secret


def _get_client():
    import anthropic
    # get_secret: Streamlit Cloud secrets first, then .env / environment.
    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Add it to .env locally, or to the "
            "Streamlit Cloud secrets manager when deployed."
        )
    return anthropic.Anthropic(api_key=api_key)


# ── OUTPUT SCHEMA ──────────────────────────────────────────────────────────────
#
# This is the same shape the extractor produces, plus `validation_notes`.
# The API enforces it: every field present, confidence constrained to the enum,
# no extra keys. "additionalProperties": false is required by the API for
# every object in the schema.
#
VALIDATED_PROCESS_SCHEMA = {
    "type": "object",
    "properties": {
        "process": {"type": "string"},
        "display_name": {"type": "string"},
        "owner": {"type": "string"},
        "trigger": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "edge_cases": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "validation_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["process", "display_name", "owner", "trigger", "steps",
                 "edge_cases", "sources", "confidence", "validation_notes"],
    "additionalProperties": False,
}


# ── PROMPT DESIGN ──────────────────────────────────────────────────────────────
#
# Note what's NOT here: no JSON formatting instructions. The schema handles
# format; the prompt is free to focus entirely on review quality. Compare
# with the extractor's SYSTEM_PROMPT, where half the text is output-format
# plumbing.
#
# The rubric is deliberately concrete ("could a new employee execute this?")
# rather than abstract ("ensure high quality") — models review much better
# against testable questions than against vibes.
#
SYSTEM_PROMPT = """You are a meticulous process documentation reviewer. You receive
a draft process definition that another analyst extracted from company knowledge,
and you return an improved version.

Review the draft against this rubric:

1. STEPS — Is each step clear and actionable? Could a new employee execute it
   without asking questions? Rewrite vague steps ("handle the request") into
   concrete ones ("reply to the customer within 24h confirming receipt").
   Fix ordering problems. Split steps that bundle multiple actions.

2. EDGE CASES — Are they realistic and relevant to this process? Remove
   speculative ones that don't follow from the sources. Add obvious missing
   ones (e.g. a refund process with no "payment already settled" case).

3. OWNER — Is the owner a specific, identifiable team or role? "unknown" is
   acceptable when the sources genuinely don't say; "the company" is not.

4. TRIGGER — Does it name a concrete event or condition, not a restatement
   of the process name?

5. CONFIDENCE — Re-assess honestly. If you had to infer or rewrite heavily,
   confidence should drop, not rise. Never raise confidence above the draft's
   level unless the draft was clearly underselling solid sourcing.

Rules:
- Improve, don't rewrite for taste. If a field is already good, keep it verbatim.
- Never invent facts. You only have the draft, not the source documents — when
  something is missing, flag it in validation_notes rather than fabricating it.
- Keep `process`, `display_name`, and `sources` unchanged unless they contain
  an outright error.
- validation_notes: 2-6 short entries describing what you checked and changed,
  e.g. "Rewrote step 3 — 'process the form' was not actionable" or
  "Owner could not be verified from draft; left as-is". If the draft was
  already solid, say so. These notes are read by humans deciding whether to
  trust the file.
"""


def _build_user_prompt(process: dict[str, Any]) -> str:
    # json.dumps with indent so the draft is as readable to the model as it
    # would be to a human reviewer — models parse pretty-printed JSON more
    # reliably than minified blobs.
    draft = json.dumps(process, indent=2)
    return f"""Here is the draft process definition to review:

{draft}

Return the improved version."""


def validate_process(process: dict[str, Any]) -> dict[str, Any]:
    """
    Review an extracted process dict and return an improved version with a
    `validation_notes` field added.

    Takes the dict the extractor produced (generated_at and all). We strip
    generated_at before sending — the validator has no business changing
    timestamps, and leaving it out of the schema means the model *can't*
    hallucinate one. We re-attach provenance timestamps in code afterwards,
    same principle as the extractor: timestamps are deterministic code, not
    LLM output.
    """
    client = _get_client()

    # Don't send fields the model shouldn't touch.
    draft = {k: v for k, v in process.items() if k != "generated_at"}

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=16000,
        # Adaptive thinking lets the model reason about the draft before
        # answering — critique benefits from deliberation more than the
        # extractor's mostly-mechanical restructuring does.
        thinking={"type": "adaptive"},
        # The API-enforced output contract (see module docstring).
        output_config={
            "format": {
                "type": "json_schema",
                "schema": VALIDATED_PROCESS_SCHEMA,
            }
        },
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_user_prompt(draft)}
        ],
    )

    # With output_config.format the text block is guaranteed valid JSON
    # matching the schema — but the response may also contain thinking
    # blocks, so we pick out the text block rather than assuming content[0].
    raw_text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(raw_text)

    # Provenance, attached in code: when the draft was generated, when it
    # was validated, and by what.
    result["generated_at"] = process.get("generated_at", datetime.now().isoformat())
    result["validated_at"] = datetime.now().isoformat()

    usage = response.usage
    print(f"  Validator tokens: {usage.input_tokens} in, {usage.output_tokens} out")

    return result


def run_pipeline(topic: str, n_chunks: int = 10) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Full 2-agent pipeline: extract a draft, then validate it.

    Returns (draft, validated) so callers can show both — seeing what the
    validator changed is how you build trust in (or catch problems with)
    the pipeline. The dashboard renders them side by side.
    """
    from agents.extractor import extract_process

    draft = extract_process(topic, n_chunks=n_chunks)
    validated = validate_process(draft)
    return draft, validated
