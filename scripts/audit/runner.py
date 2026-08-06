from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from scripts.argument.contracts import load_contracts
from scripts.evidence.models import claim_index, load_cards
from scripts.evidence.validation import validate_workspace
from scripts.workspace import dump_json, init_workspace, load_json
from .causality import causal_overclaims
from .parsing import parse_paragraphs
from .semantic import initialize_semantic_audit as _initialize, validate_semantic_report
from .structural import reverse_outline


def initialize_semantic_audit(project: Path | str) -> Path:
    root = Path(project).resolve()
    ws = init_workspace(root)
    text = (ws / "discussion_trace.md").read_text(encoding="utf-8")
    paragraphs, errors = parse_paragraphs(text)
    if errors or not paragraphs:
        raise ValueError("Cannot initialize semantic audit until every paragraph has a valid trace header")
    return _initialize(ws, text, paragraphs)


def audit_draft(project: Path | str) -> dict[str, Any]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    draft_path = ws / "discussion_trace.md"
    text = draft_path.read_text(encoding="utf-8") if draft_path.exists() else ""
    errors: list[str] = []
    warnings: list[str] = []
    if not text.strip():
        errors.append("discussion_trace.md is empty")
    paragraphs, parse_errors = parse_paragraphs(text)
    errors.extend(parse_errors)

    ledger = load_json(ws / "result_ledger.json", {})
    results = {x.get("id"): x for x in ledger.get("results", []) if x.get("id")}
    cards = load_cards(ws)
    claims = claim_index(cards)
    contracts = load_contracts(ws)
    contract_counts: Counter[str] = Counter()
    cited: Counter[str] = Counter()

    for paragraph in paragraphs:
        contract_counts[paragraph.contract_id] += 1
        contract = contracts.get(paragraph.contract_id)
        if not contract:
            errors.append(f"Paragraph {paragraph.number} references unknown contract {paragraph.contract_id}")
            continue
        if set(paragraph.result_ids) != set(contract.get("linked_results", [])):
            errors.append(f"Paragraph {paragraph.number} trace results do not match {paragraph.contract_id}.linked_results")
        allowed = set(contract.get("allowed_claims", []))
        for claim_id in paragraph.claims:
            cited[claim_id] += 1
            if claim_id not in claims:
                errors.append(f"Paragraph {paragraph.number} cites unknown claim {claim_id}")
                continue
            if claim_id not in allowed:
                errors.append(f"Paragraph {paragraph.number} cites {claim_id} outside {paragraph.contract_id}.allowed_claims")
            if not set(paragraph.result_ids).intersection(claims[claim_id].get("linked_results", [])):
                errors.append(f"Paragraph {paragraph.number} cites {claim_id}, which is not linked to traced results")
        missing = sorted(allowed - set(paragraph.claims))
        if missing:
            warnings.append(f"Paragraph {paragraph.number} does not use contracted claims: {missing}")
        ceilings = [results[x].get("causal_ceiling", "descriptive") for x in paragraph.result_ids if x in results]
        for issue in causal_overclaims(paragraph.body, ceilings):
            errors.append(f"Paragraph {paragraph.number} causal audit: {issue}")

    for contract_id, contract in contracts.items():
        if contract.get("status") == "approved" and contract_counts[contract_id] != 1:
            errors.append(f"Approved contract {contract_id} must have exactly one draft paragraph; found {contract_counts[contract_id]}")
    outline = reverse_outline(paragraphs, contracts, results)
    dump_json(ws / "reverse_outline.json", outline)
    for row in outline["paragraphs"]:
        if row["lexical_focus"] < 0.08:
            warnings.append(f"Paragraph {row['paragraph']} has weak lexical focus on its contracted claim/result")
        if not row["returns_to_study"]:
            warnings.append(f"Paragraph {row['paragraph']} may not return to the study result; semantic review must confirm closure")

    config = load_json(ws / "config.json", {})
    constraints = config.get("journal_constraints", {})
    def count_words(value: str) -> int:
        import re
        english = len(re.findall(r"\b[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*\b", value))
        chinese = len(re.findall(r"[\u4e00-\u9fff]", value))
        return english + chinese
    max_total = int(constraints.get("max_discussion_words") or 0)
    max_paragraph = int(constraints.get("max_paragraph_words") or 0)
    max_paragraphs = int(constraints.get("max_paragraphs") or 0)
    total_words = sum(count_words(p.body) for p in paragraphs)
    if max_total and total_words > max_total:
        errors.append(f"Journal word constraint exceeded: Discussion has {total_words} words; maximum is {max_total}")
    if max_paragraphs and len(paragraphs) > max_paragraphs:
        errors.append(f"Journal paragraph constraint exceeded: {len(paragraphs)} paragraphs; maximum is {max_paragraphs}")
    if max_paragraph:
        for paragraph in paragraphs:
            paragraph_words = count_words(paragraph.body)
            if paragraph_words > max_paragraph:
                errors.append(f"Journal paragraph word constraint exceeded in paragraph {paragraph.number}: {paragraph_words}; maximum is {max_paragraph}")

    validation = validate_workspace(root)
    errors.extend(f"Workspace validation: {item}" for item in validation["errors"])
    semantic_errors, semantic_warnings = validate_semantic_report(ws, text, paragraphs)
    errors.extend(semantic_errors)
    warnings.extend(semantic_warnings)

    metrics = {
        "paragraphs": len(paragraphs), "contracts": len(contracts), "unique_claims_cited": len(cited),
        "claim_mentions": sum(cited.values()), "results_covered": sorted({r for p in paragraphs for r in p.result_ids}),
        "semantic_audit_present": (ws / "semantic_audit_report.json").exists(), "discussion_words": total_words,
    }
    report = {"errors": list(dict.fromkeys(errors)), "warnings": list(dict.fromkeys(warnings)), "metrics": metrics}
    dump_json(ws / "audit_report.json", report)
    return report
