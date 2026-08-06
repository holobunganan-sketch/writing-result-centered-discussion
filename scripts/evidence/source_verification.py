from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ingest.base import clean_text
from scripts.workspace import file_hash, text_hash


def load_units(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / "index" / "units.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_card(project: Path, workspace: Path, card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ref_id = card.get("id", "unknown")
    source_rel = card.get("source_file", "")
    source = project / source_rel
    if not source.exists():
        return [f"{ref_id}.source_file does not exist: {source_rel}"]
    actual_hash = file_hash(source)
    if card.get("source_hash") != actual_hash:
        errors.append(f"{ref_id}.source_hash does not match current source; verification is stale")
    units = [u for u in load_units(workspace) if u.get("path") == source_rel]
    if not units:
        errors.append(f"{ref_id}.source_file has no indexed units: {source_rel}")
        return errors
    for claim in card.get("claims", []):
        claim_id = claim.get("id", "unknown")
        excerpt = claim.get("verified_excerpt", "")
        if claim.get("excerpt_hash") != text_hash(excerpt):
            errors.append(f"{claim_id}.excerpt_hash does not match verified_excerpt")
        matching = [u for u in units if u.get("locator") == claim.get("locator")]
        if not matching:
            errors.append(f"{claim_id}.locator does not identify an indexed source unit: {claim.get('locator')}")
            continue
        normalized_excerpt = clean_text(excerpt).casefold()
        if not any(normalized_excerpt in clean_text(u.get("text", "")).casefold() for u in matching):
            errors.append(f"{claim_id}.verified_excerpt is not present at the declared locator")
    return errors
