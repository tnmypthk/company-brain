"""
Writes extracted process dicts to YAML skills files.

Why YAML and not JSON?
YAML is human-readable and editable. A skills file is meant to be reviewed,
corrected, and committed to a repo by a human. JSON requires escaping and
brackets that make manual editing error-prone. YAML reads like a document.

Why a separate module for writing?
The extractor returns a Python dict — a pure data structure with no I/O.
Writing to disk is a side effect that belongs in its own module. This keeps
the extractor unit-testable without touching the filesystem.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

SKILLS_DIR = Path("skills")


def process_to_yaml(process: dict[str, Any]) -> str:
    """
    Convert a process dict to a formatted YAML string.

    We build the YAML manually (not via yaml.dump) because yaml.dump's default
    ordering is alphabetical — which puts 'confidence' before 'steps' and looks
    wrong. Manual construction gives us a logical reading order:
    what → who → why → how → exceptions → provenance.
    """
    # yaml.dump handles proper escaping and multiline strings automatically.
    # We just control the key order by building an ordered dict.
    ordered = {
        "process": process["process"],
        "display_name": process.get("display_name", process["process"]),
        "owner": process.get("owner", "unknown"),
        "trigger": process.get("trigger", "unknown"),
        "steps": process.get("steps", []),
        "edge_cases": process.get("edge_cases", []),
        "sources": process.get("sources", []),
        "generated_at": process.get("generated_at", datetime.now().isoformat()),
        "confidence": process.get("confidence", "low"),
    }

    return yaml.dump(
        ordered,
        default_flow_style=False,   # block style (human-readable), not inline
        allow_unicode=True,          # don't escape unicode characters
        sort_keys=False,             # preserve our manually defined order
        width=80,                    # wrap long lines at 80 chars
    )


def save_skills_file(process: dict[str, Any]) -> Path:
    """
    Write a process dict to skills/{process_name}.yaml.
    Returns the path of the written file.

    File naming uses the process slug (snake_case) so filenames are
    predictable and can be version-controlled cleanly.
    """
    SKILLS_DIR.mkdir(exist_ok=True)

    filename = f"{process['process']}.yaml"
    path = SKILLS_DIR / filename

    yaml_content = process_to_yaml(process)
    path.write_text(yaml_content, encoding="utf-8")

    return path


def list_skills_files() -> list[dict[str, Any]]:
    """
    Return metadata for all saved skills files.
    Used by the dashboard to show the saved skills library.
    """
    SKILLS_DIR.mkdir(exist_ok=True)
    files = sorted(SKILLS_DIR.glob("*.yaml"))

    skills = []
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            skills.append({
                "filename": f.name,
                "display_name": data.get("display_name", data.get("process", f.stem)),
                "owner": data.get("owner", "unknown"),
                "confidence": data.get("confidence", "unknown"),
                "generated_at": data.get("generated_at", "unknown"),
                "path": f,
            })
        except Exception:
            # Corrupted YAML shouldn't crash the whole list
            skills.append({"filename": f.name, "display_name": f.stem,
                           "owner": "?", "confidence": "?", "generated_at": "?", "path": f})

    return skills
