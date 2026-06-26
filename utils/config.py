"""
Centralized secret + environment resolution.

WHY THIS FILE EXISTS — the st.secrets vs os.getenv problem:

The app runs in two very different places:

  • Local dev    — secrets live in a .env file, read by python-dotenv into
                   the process environment, fetched with os.getenv().
  • Streamlit    — there is no .env on the server. Streamlit Cloud has its own
    Cloud          encrypted secrets manager; values are exposed to the app as
                   st.secrets["KEY"], NOT as environment variables.

If the code only calls os.getenv(), it works locally and silently returns
None on Streamlit Cloud (every Claude call fails with "API key not set"). If
it only calls st.secrets, it works on Cloud but crashes locally — and crashes
the CLI (ingest.py), which has no Streamlit runtime at all.

get_secret() resolves both with one rule: try Streamlit secrets first, fall
back to the environment. That ordering is deliberate — on Cloud st.secrets is
authoritative; locally st.secrets is empty/absent so we fall through to .env.

Why a shared helper instead of the try/except inlined in every module?
Because extractor, validator, answerer, and slack all need the same logic, and
they're also imported by the CLI where Streamlit isn't running. One tested
helper beats four subtly-different copies.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load .env into the environment once, at import. Harmless on Streamlit Cloud
# (no .env there) — it just does nothing and we fall through to st.secrets.
load_dotenv()


def get_secret(name: str, default: str | None = None) -> str | None:
    """
    Resolve a secret by name: Streamlit secrets first, then environment.

    Accessing st.secrets when no secrets.toml exists (local dev without the
    file, or the CLI) raises — that's expected, and we swallow it and fall
    back to os.getenv. We import streamlit lazily inside the try so that a
    pure-CLI run that never touches Streamlit doesn't pay for it up front.
    """
    try:
        import streamlit as st

        # `name in st.secrets` triggers the secrets file load; if there's no
        # file and we're not on Cloud, this raises and we fall through.
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass

    return os.getenv(name, default)


def running_on_cloud() -> bool:
    """
    Best-effort detection of a deployed (headless server) environment.

    Used to gate features that need a local machine — specifically Google
    OAuth, which opens a browser via flow.run_local_server() and reads
    credentials.json from disk. Neither works on a server.

    Detection, in order:
      1. Explicit override — set RUNNING_ON_CLOUD in secrets/env to force it
         (useful for testing the cloud code path locally).
      2. Streamlit Community Cloud mounts the repo under /mount/src.

    This is a heuristic, not a guarantee. The Google sections also gate on
    credentials.json actually existing, so a wrong answer here degrades to a
    clear message, never a crash.
    """
    override = get_secret("RUNNING_ON_CLOUD")
    if override is not None:
        return str(override).strip().lower() in ("1", "true", "yes")

    return os.path.isdir("/mount/src")
