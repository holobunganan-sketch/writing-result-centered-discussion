from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore

from scripts.argument.contracts import load_contracts
from scripts.indexing.search import index_is_fresh
from scripts.indexing.semantic import scores as semantic_scores
from scripts.workspace import SKILL_ROOT, dump_json, init_workspace, load_json
from .models import claim_index, load_cards
from .source_verification import verify_card

SCHEMA_FILES = {
    "result_ledger": "result-ledger.schema.json",
    "evidence_card": "evidence-card.schema.json",
    "paragraph_contract": "paragraph-contract.schema.json",
    "argument_map": "argument-map.schema.json",
    "comparability_matrix": "comparability-matrix.schema.json",
    "evidence_tension_map": "evidence-tension-map.schema.json",
}


def _schema_errors(payload: Any, schema_name: str, context: str) -> list[str]:
    schema = load_json(SKILL_ROOT / "schemas" / SCHEMA_FILES[schema_name], {})
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(payload), key=lambda x: list(x.absolute_path)):
        location = ".".join(str(x) for x in error.absolute_path)
        errors.append(f"{context}{'.' + location if location else ''}: {error.message}")
    return errors


def validate_workspace(project: Path | str) -> dict[str, Any]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    errors: list[str] = []
    warnings: list[str] = []
    freshness = index_is_fresh(root)
    if not freshness["fresh"]:
        errors.append(f"index is stale or missing; changed files: {freshness['changed']}")

    ledger = load_json(ws / "result_ledger.json", {})
    errors.extend(_schema_errors(ledger, "result_ledger", "result_ledger"))
    results = {r.get("id"): r for r in ledger.get("results", []) if r.get("id")}
    if len(results) != len(ledger.get("results", [])):
        errors.append("result_ledger contains duplicate or missing result IDs")
    indexed_units_path = ws / "index" / "units.jsonl"
    indexed_units = []
    if indexed_units_path.exists():
        import json
        indexed_units = [json.loads(line) for line in indexed_units_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    inventory_roles = {x.get("path"): x.get("role") for x in load_json(ws / "project_inventory.json", {}).get("files", [])}
    for result_id, result in results.items():
        source = result.get("source", {})
        source_file, locator = source.get("file", ""), source.get("locator", "")
        if inventory_roles.get(source_file) != "study-evidence":
            errors.append(f"{result_id}.source.file must resolve to the study-evidence pool: {source_file}")
        matched_units = [u for u in indexed_units if u.get("path") == source_file and u.get("locator") == locator]
        if not matched_units:
            errors.append(f"{result_id}.source.locator does not identify an indexed study unit: {source_file} @ {locator}")
        elif result.get("finding"):
            support = float(semantic_scores([str(matched_units[0].get("text", ""))], str(result.get("finding", "")))[0])
            if support < 0.02:
                warnings.append(f"{result_id}.finding has weak semantic overlap with its indexed source unit; verify the paraphrase manually")

    cards = load_cards(ws)
    claims = claim_index(cards)
    claim_counts: Counter[str] = Counter()
    for ref_id, card in cards.items():
        if "claims" not in card and "usable_claims" in card:
            errors.append(f"{ref_id} uses legacy v1 evidence format; run migrate-v1 and verify every claim")
            continue
        errors.extend(_schema_errors(card, "evidence_card", ref_id))
        if card.get("id") != ref_id:
            errors.append(f"{ref_id} file ID does not match card.id {card.get('id')}")
        if inventory_roles.get(card.get("source_file")) != "external-evidence":
            errors.append(f"{ref_id}.source_file must resolve to the external-evidence pool: {card.get('source_file')}")
        errors.extend(verify_card(root, ws, card))
        for claim in card.get("claims", []):
            claim_id = claim.get("id", "")
            claim_counts[claim_id] += 1
            if not claim_id.startswith(ref_id + "-C"):
                errors.append(f"{claim_id} must be namespaced under {ref_id}")
            statement = str(claim.get("statement", ""))
            excerpt = str(claim.get("verified_excerpt", ""))
            if statement and excerpt:
                support_score = float(semantic_scores([excerpt], statement)[0])
                if support_score < 0.04:
                    errors.append(f"{claim_id}.statement has insufficient semantic support from verified_excerpt")
            for result_id in claim.get("linked_results", []):
                if result_id not in results:
                    errors.append(f"{claim_id} links unknown result {result_id}")
    for claim_id, count in claim_counts.items():
        if count > 1:
            errors.append(f"duplicate claim ID: {claim_id}")

    comparability = load_json(ws / "comparability_matrix.json", {})
    tension = load_json(ws / "evidence_tension_map.json", {})
    errors.extend(_schema_errors(comparability, "comparability_matrix", "comparability_matrix"))
    errors.extend(_schema_errors(tension, "evidence_tension_map", "evidence_tension_map"))
    matrix_pairs = {(r.get("result_id"), r.get("claim_id")) for r in comparability.get("rows", [])}
    matrix_by_pair = {(r.get("result_id"), r.get("claim_id")): r for r in comparability.get("rows", [])}
    for row in comparability.get("rows", []):
        result_id, claim_id = row.get("result_id"), row.get("claim_id")
        if result_id not in results:
            errors.append(f"comparability_matrix contains unknown result {result_id}")
        if claim_id not in claims:
            errors.append(f"comparability_matrix contains unknown claim {claim_id}")
        elif result_id not in claims[claim_id].get("linked_results", []):
            errors.append(f"comparability_matrix {result_id} × {claim_id} is not a declared claim-result link")
    tension_results = {r.get("result_id") for r in tension.get("results", [])}
    tension_fields = ["supporting_claims", "contrasting_claims", "partially_consistent_claims", "noncomparable_claims"]
    for row in tension.get("results", []):
        result_id = row.get("result_id")
        if result_id not in results:
            errors.append(f"evidence_tension_map contains unknown result {result_id}")
        category_claims: list[str] = []
        for field in tension_fields:
            for claim_id in row.get(field, []):
                category_claims.append(claim_id)
                if claim_id not in claims:
                    errors.append(f"evidence_tension_map {result_id}.{field} contains unknown claim {claim_id}")
                elif result_id not in claims[claim_id].get("linked_results", []):
                    errors.append(f"evidence_tension_map {result_id}.{field} contains unlinked claim {claim_id}")
                else:
                    role = claims[claim_id].get("role")
                    matrix_row = matrix_by_pair.get((result_id, claim_id), {})
                    if field == "contrasting_claims" and role != "contrast":
                        errors.append(f"evidence_tension_map {result_id}.{field} requires claim role contrast: {claim_id}")
                    if field == "noncomparable_claims" and matrix_row.get("overall") != "not-comparable":
                        errors.append(f"evidence_tension_map {result_id}.{field} requires a not-comparable matrix rating: {claim_id}")
        if len(category_claims) != len(set(category_claims)):
            errors.append(f"evidence_tension_map {result_id} assigns the same claim to multiple relationship categories")
    for result_id, result in results.items():
        if result.get("priority") in {"primary", "key-secondary"} and result_id not in tension_results:
            errors.append(f"evidence_tension_map is missing primary result {result_id}")
    for claim_id, claim in claims.items():
        if claim.get("role") in {"benchmark", "support", "contrast", "difference-explanation"}:
            for result_id in claim.get("linked_results", []):
                if (result_id, claim_id) not in matrix_pairs:
                    errors.append(f"comparability_matrix is missing {result_id} × {claim_id}")

    contracts = load_contracts(ws)
    for contract_id, contract in contracts.items():
        errors.extend(_schema_errors(contract, "paragraph_contract", contract_id))
        if contract.get("id") != contract_id:
            errors.append(f"{contract_id} file ID does not match contract.id")
        if contract.get("status") != "approved":
            errors.append(f"{contract_id}.status must be approved before drafting")
        linked = set(contract.get("linked_results", []))
        for result_id in linked:
            if result_id not in results:
                errors.append(f"{contract_id} links unknown result {result_id}")
        strength_rank = {"descriptive": 0, "associational": 1, "causal": 2}
        ceilings = [results[r].get("causal_ceiling", "descriptive") for r in linked if r in results]
        if ceilings and strength_rank.get(contract.get("claim_strength"), 99) > min(strength_rank.get(x, 0) for x in ceilings):
            errors.append(f"{contract_id}.claim_strength exceeds the causal ceiling of linked results {sorted(linked)}")
        allowed = set(contract.get("allowed_claims", []))
        used: set[str] = set()
        orders: list[int] = []
        for step in contract.get("argument_steps", []):
            orders.append(step.get("order"))
            for claim_id in step.get("claims", []):
                used.add(claim_id)
                if claim_id not in allowed:
                    errors.append(f"{contract_id}.argument_steps uses {claim_id} outside allowed_claims")
        if orders and sorted(orders) != list(range(1, len(orders) + 1)):
            errors.append(f"{contract_id}.argument_steps order must be consecutive from 1")
        steps = contract.get("argument_steps", [])
        if steps and steps[0].get("type") != "study-result":
            errors.append(f"{contract_id}.argument_steps must start with study-result")
        if steps and steps[-1].get("type") not in {"interpretation", "interpretation-and-boundary", "boundary", "implication"}:
            errors.append(f"{contract_id}.argument_steps must end with interpretation, boundary, or implication")
        for claim_id in allowed:
            if claim_id not in claims:
                errors.append(f"{contract_id}.allowed_claims contains unknown claim {claim_id}")
                continue
            if not linked.intersection(claims[claim_id].get("linked_results", [])):
                errors.append(f"{contract_id}.allowed_claims {claim_id} is not linked to contract results")
        unused = sorted(allowed - used)
        if unused:
            warnings.append(f"{contract_id} allows claims unused by argument steps: {unused}")

    argument_map = load_json(ws / "argument_map.json", {})
    errors.extend(_schema_errors(argument_map, "argument_map", "argument_map"))
    order = argument_map.get("paragraph_order", [])
    unknown = sorted(set(order) - set(contracts))
    if unknown:
        errors.append(f"argument_map contains unknown contracts: {unknown}")
    missing = sorted(set(contracts) - set(order))
    if missing:
        errors.append(f"argument_map is missing contracts: {missing}")

    metrics = {
        "results": len(results), "evidence_cards": len(cards), "claims": len(claims),
        "paragraph_contracts": len(contracts), "comparability_rows": len(comparability.get("rows", [])),
        "tension_results": len(tension.get("results", [])), "index_fresh": freshness["fresh"],
    }
    report = {"errors": errors, "warnings": warnings, "metrics": metrics, "source_snapshot_hash": freshness.get("current_hash", "")}
    dump_json(ws / "validation_report.json", report)
    return report
