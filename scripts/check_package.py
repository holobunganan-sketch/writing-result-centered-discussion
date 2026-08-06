#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator  # type: ignore

REQUIRED = [
    "SKILL.md", "README.md", "VERSION", "requirements.txt", "requirements-test.txt", "scripts/discussion.py", "scripts/cli.py",
    "scripts/workspace.py", "scripts/compiler.py", "scripts/ingest/__init__.py", "scripts/indexing/search.py",
    "scripts/evidence/validation.py", "scripts/argument/contracts.py", "scripts/audit/runner.py",
    "schemas/result-ledger.schema.json", "schemas/evidence-card.schema.json", "schemas/paragraph-contract.schema.json",
    "schemas/argument-map.schema.json", "schemas/comparability-matrix.schema.json", "schemas/evidence-tension-map.schema.json",
    "schemas/semantic-audit.schema.json", "workflows/01-intake-and-index.md", "workflows/02-result-ledger.md",
    "workflows/03-evidence-selection.md", "workflows/04-argument-design.md", "workflows/05-drafting.md",
    "workflows/06-audit-revision.md", ".github/workflows/ci.yml",
]
EXAMPLES = {
    "result_ledger.example.json": "result-ledger.schema.json",
    "evidence_card.example.json": "evidence-card.schema.json",
    "paragraph_contract.example.json": "paragraph-contract.schema.json",
    "argument_map.example.json": "argument-map.schema.json",
    "comparability_matrix.example.json": "comparability-matrix.schema.json",
    "evidence_tension_map.example.json": "evidence-tension-map.schema.json",
    "semantic_audit.example.json": "semantic-audit.schema.json",
}


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            errors.append(f"Missing required file: {rel}")
    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").exists() else ""
    if version != "2.0.0":
        errors.append(f"VERSION must be 2.0.0 for this release, found {version!r}")

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
        if "[REF-001]" in text or "allowed_references" in text:
            errors.append("SKILL.md still contains v1 reference-level instructions")

    schemas = {}
    for schema_path in (root / "schemas").glob("*.json"):
        try:
            data = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(data)
            schemas[schema_path.name] = data
        except Exception as exc:
            errors.append(f"Invalid JSON Schema {schema_path.name}: {exc}")
    for template_name, schema_name in EXAMPLES.items():
        try:
            payload = json.loads((root / "templates" / template_name).read_text(encoding="utf-8"))
            issues = list(Draft202012Validator(schemas[schema_name]).iter_errors(payload))
            if issues:
                errors.append(f"Template {template_name} violates {schema_name}: {issues[0].message}")
        except Exception as exc:
            errors.append(f"Cannot validate template {template_name}: {exc}")

    for module in ["scripts.workspace", "scripts.ingest", "scripts.indexing.search", "scripts.evidence.validation", "scripts.audit.runner", "scripts.compiler", "scripts.cli"]:
        try:
            importlib.import_module(module)
        except Exception as exc:
            errors.append(f"Cannot import {module}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Package structure, Skill metadata, v2 Schemas, examples, and module imports are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
