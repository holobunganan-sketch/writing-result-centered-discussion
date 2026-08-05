#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "SKILL.md",
    "README.md",
    "scripts/discussion.py",
    "scripts/discussion_core.py",
    "schemas/result-ledger.schema.json",
    "schemas/evidence-card.schema.json",
    "schemas/paragraph-contract.schema.json",
    "workflows/02-result-ledger.md",
    "workflows/03-evidence-selection.md",
    "workflows/04-argument-design.md",
    "workflows/05-drafting.md",
    "workflows/06-audit-revision.md",
]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            errors.append(f"Missing required file: {rel}")

    skill_path = root / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
        if not match:
            errors.append("SKILL.md has no YAML frontmatter")
        else:
            frontmatter = match.group(1)
            name = re.search(r"^name:\s*(.+)$", frontmatter, flags=re.M)
            description = re.search(r"^description:\s*(.+)$", frontmatter, flags=re.M)
            if not name or name.group(1).strip() != "writing-result-centered-discussion":
                errors.append("SKILL.md name is invalid")
            if not description or not description.group(1).strip().startswith("Use when"):
                errors.append("SKILL.md description must start with 'Use when'")
            if len(frontmatter) > 1024:
                errors.append("SKILL.md frontmatter exceeds 1024 characters")

    for schema in (root / "schemas").glob("*.json"):
        try:
            data = json.loads(schema.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON schema {schema.name}: {exc}")
            continue
        if data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"Schema {schema.name} does not declare draft 2020-12")

    for template in (root / "templates").glob("*.json"):
        try:
            json.loads(template.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON template {template.name}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Package structure, frontmatter, schemas, and JSON templates are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
