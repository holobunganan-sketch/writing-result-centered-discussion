from __future__ import annotations

import csv
from pathlib import Path

from scripts.workspace import init_workspace, load_json
from .models import load_cards


def export_evidence_matrix(project: Path | str) -> Path:
    ws = init_workspace(project)
    output = ws / "evidence_matrix.csv"
    fields = ["reference_id", "claim_id", "citation_key", "source_file", "locator", "linked_results", "role", "statement", "effect_size", "directness", "certainty", "analysis_level", "comparability_overall"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for ref_id, card in sorted(load_cards(ws).items()):
            for claim in card.get("claims", []):
                writer.writerow({
                    "reference_id": ref_id, "claim_id": claim.get("id", ""), "citation_key": card.get("citation_key", ""),
                    "source_file": card.get("source_file", ""), "locator": claim.get("locator", ""),
                    "linked_results": ";".join(claim.get("linked_results", [])), "role": claim.get("role", ""),
                    "statement": claim.get("statement", ""), "effect_size": claim.get("effect_size", ""),
                    "directness": claim.get("directness", ""), "certainty": claim.get("certainty", ""),
                    "analysis_level": claim.get("analysis_level", ""), "comparability_overall": claim.get("comparability", {}).get("overall", ""),
                })
    return output


def export_comparability_matrix(project: Path | str) -> Path:
    ws = init_workspace(project)
    data = load_json(ws / "comparability_matrix.json", {"rows": []})
    output = ws / "comparability_matrix.csv"
    fields = ["result_id", "claim_id", "dimension", "study", "external", "rating", "impact", "overall", "interpretive_use"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in data.get("rows", []):
            for name, dimension in row.get("dimensions", {}).items():
                writer.writerow({"result_id": row.get("result_id"), "claim_id": row.get("claim_id"), "dimension": name, **dimension, "overall": row.get("overall"), "interpretive_use": row.get("interpretive_use")})
    return output
