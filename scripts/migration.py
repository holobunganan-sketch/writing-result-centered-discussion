from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workspace import dump_json, file_hash, init_workspace, load_json


def migrate_v1(project: Path | str) -> dict[str, Any]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    backup = ws / "v1-backup"
    backup.mkdir(exist_ok=True)
    changed: list[str] = []
    warnings: list[str] = []

    ledger_path = ws / "result_ledger.json"
    ledger = load_json(ledger_path, {})
    if "study_profile" not in ledger:
        shutil.copy2(ledger_path, backup / ledger_path.name)
        ledger["study_profile"] = {"population": "", "exposure_or_intervention": "", "comparator": "", "outcomes": [], "setting": "", "follow_up": ""}
        dump_json(ledger_path, ledger)
        changed.append("result_ledger.json")
        warnings.append("Complete study_profile before validation.")

    ref_claims: dict[str, list[str]] = {}
    for path in sorted((ws / "evidence_cards").glob("*.json")):
        card = load_json(path, {})
        if "claims" in card:
            ref_claims[card.get("id", path.stem)] = [c.get("id") for c in card.get("claims", [])]
            continue
        shutil.copy2(path, backup / path.name)
        ref_id = card.get("id", path.stem)
        source = root / card.get("source_file", "")
        claims = []
        for idx, old in enumerate(card.get("usable_claims", []), 1):
            claims.append({
                "id": f"{ref_id}-C{idx}", "linked_results": card.get("linked_results", []),
                "role": (card.get("evidence_roles") or ["support"])[0], "statement": old.get("claim", ""),
                "locator": old.get("locator") or card.get("locator", ""), "verified_excerpt": "",
                "excerpt_hash": "0" * 64, "directness": "direct", "certainty": "not-assessed",
                "effect_size": card.get("effect_size") or "not reported", "analysis_level": "not-applicable",
                "forbidden_inferences": card.get("forbidden_inferences", []),
                "comparability": {"population": "not-applicable", "design": "not-applicable", "intervention_or_exposure": "not-applicable", "outcome": "not-applicable", "follow_up": "not-applicable", "setting": "not-applicable", "overall": "not-comparable", "impact_on_interpretation": "Requires manual v2 assessment."}
            })
        converted = {
            "id": ref_id, "citation_key": card.get("citation_key", ""), "rendered_citation": card.get("rendered_citation", ""),
            "source_file": card.get("source_file", ""), "source_hash": file_hash(source) if source.exists() else "0" * 64,
            "publication": {"title": card.get("main_finding", "Untitled legacy reference"), "authors": ["Unknown"], "year": "", "doi": "", "pmid": "", "status": "other"},
            "claims": claims,
        }
        dump_json(path, converted)
        ref_claims[ref_id] = [c["id"] for c in claims]
        changed.append(f"evidence_cards/{path.name}")
        warnings.append(f"{ref_id}: paste exact verified excerpts and recompute excerpt_hash before use.")

    for path in sorted((ws / "paragraph_contracts").glob("*.json")):
        contract = load_json(path, {})
        if "allowed_claims" in contract:
            continue
        shutil.copy2(path, backup / ("contract-" + path.name))
        allowed = [claim for ref in contract.pop("allowed_references", []) for claim in ref_claims.get(ref, [])]
        contract["allowed_claims"] = allowed
        for step in contract.get("argument_steps", []):
            refs = step.pop("references", [])
            step["claims"] = [claim for ref in refs for claim in ref_claims.get(ref, [])]
        dump_json(path, contract)
        changed.append(f"paragraph_contracts/{path.name}")

    report = {"migrated_at": datetime.now(timezone.utc).isoformat(), "changed": changed, "warnings": warnings, "backup": str(backup)}
    dump_json(ws / "migration_report.json", report)
    return report
