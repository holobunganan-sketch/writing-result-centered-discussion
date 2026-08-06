from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.workspace import dump_json, init_workspace, load_json


def load_cards(workspace: Path) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for path in sorted((workspace / "evidence_cards").glob("*.json")):
        card = load_json(path, {})
        cards[card.get("id", path.stem)] = card
    return cards


def claim_index(cards: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    claims: dict[str, dict[str, Any]] = {}
    for ref_id, card in cards.items():
        for claim in card.get("claims", []):
            claims[claim.get("id", "")] = {**claim, "reference_id": ref_id, "card": card}
    return claims


def create_evidence_card(project: Path | str, ref_id: str, source_file: str) -> Path:
    ws = init_workspace(project)
    path = ws / "evidence_cards" / f"{ref_id}.json"
    if path.exists():
        raise FileExistsError(path)
    payload = {
        "id": ref_id, "citation_key": "", "rendered_citation": "", "source_file": source_file,
        "source_hash": "", "publication": {"title": "", "authors": [], "year": "", "doi": "", "pmid": "", "status": "other"},
        "claims": []
    }
    dump_json(path, payload)
    return path


def seal_evidence_card(project: Path | str, ref_id: str) -> Path:
    from scripts.ingest.base import clean_text
    from scripts.evidence.source_verification import load_units
    from scripts.workspace import file_hash, text_hash

    root = Path(project).resolve()
    ws = init_workspace(root)
    path = ws / "evidence_cards" / f"{ref_id}.json"
    card = load_json(path, None)
    if not isinstance(card, dict):
        raise FileNotFoundError(path)
    source = root / card.get("source_file", "")
    if not source.exists():
        raise ValueError(f"Source file does not exist: {card.get('source_file')}")
    units = [u for u in load_units(ws) if u.get("path") == card.get("source_file")]
    if not units:
        raise ValueError("Source has no indexed units; run index first")
    for claim in card.get("claims", []):
        excerpt = clean_text(str(claim.get("verified_excerpt", "")))
        if not excerpt:
            raise ValueError(f"{claim.get('id')} has no verified_excerpt")
        matching = [u for u in units if u.get("locator") == claim.get("locator")]
        if not matching or not any(excerpt.casefold() in clean_text(u.get("text", "")).casefold() for u in matching):
            raise ValueError(f"{claim.get('id')} excerpt is absent at locator {claim.get('locator')}")
        claim["verified_excerpt"] = excerpt
        claim["excerpt_hash"] = text_hash(excerpt)
    card["source_hash"] = file_hash(source)
    dump_json(path, card)
    return path
