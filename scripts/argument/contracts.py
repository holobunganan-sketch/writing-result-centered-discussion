from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.workspace import dump_json, init_workspace, load_json


def load_contracts(workspace: Path) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path in sorted((workspace / "paragraph_contracts").glob("*.json")):
        contract = load_json(path, {})
        contracts[contract.get("id", path.stem)] = contract
    return contracts


def create_paragraph_contract(project: Path | str, contract_id: str, linked_results: list[str]) -> Path:
    ws = init_workspace(project)
    path = ws / "paragraph_contracts" / f"{contract_id}.json"
    if path.exists():
        raise FileExistsError(path)
    payload = {
        "id": contract_id, "linked_results": linked_results, "discussion_question": "", "central_claim": "",
        "claim_strength": "descriptive", "argument_steps": [], "allowed_claims": [], "closing_message": "", "status": "draft"
    }
    dump_json(path, payload)
    return path
