from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore

from scripts.workspace import SKILL_ROOT, dump_json, load_json, text_hash
from .parsing import Paragraph


def initialize_semantic_audit(workspace: Path, draft_text: str, paragraphs: list[Paragraph]) -> Path:
    draft_hash = text_hash(draft_text)
    tasks = {
        "draft_hash": draft_hash,
        "instructions": [
            "Summarize each paragraph in one sentence.",
            "Judge whether it has exactly one central claim and stays focused on its linked study result.",
            "For every claim citation, state the supported proposition, whether it advances the argument, and what is lost if deleted.",
            "Identify topic drift, failure to return to the study, and evidence-strength overclaiming.",
            "Set status to pass only when no revision is needed."
        ],
        "paragraphs": [{"contract_id": p.contract_id, "result_ids": p.result_ids, "text": p.body, "claim_ids": p.claims} for p in paragraphs]
    }
    dump_json(workspace / "semantic_audit" / "tasks.json", tasks)
    pending = {
        "draft_hash": draft_hash,
        "reviewer": "pending-codex-semantic-audit",
        "paragraphs": [{
            "contract_id": p.contract_id, "central_summary": "Pending semantic review", "one_central_claim": False,
            "linked_result_focus": False, "sentence_functions": [{"sentence": 1, "function": "pending"}],
            "citation_assessments": [], "topic_drift": False, "return_to_study": False,
            "overclaiming": [], "revision_instructions": ["Complete the semantic audit."], "status": "pending"
        } for p in paragraphs],
        "overall_status": "pending"
    }
    path = workspace / "semantic_audit_report.json"
    dump_json(path, pending)
    return path


def validate_semantic_report(workspace: Path, draft_text: str, paragraphs: list[Paragraph]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = workspace / "semantic_audit_report.json"
    if not path.exists():
        return ["semantic audit report is missing; run semantic-audit-init and complete the review"], []
    report = load_json(path, {})
    schema = load_json(SKILL_ROOT / "schemas" / "semantic-audit.schema.json", {})
    for issue in Draft202012Validator(schema).iter_errors(report):
        location = ".".join(str(x) for x in issue.absolute_path)
        errors.append(f"semantic audit{'.' + location if location else ''}: {issue.message}")
    expected_hash = text_hash(draft_text)
    if report.get("draft_hash") != expected_hash:
        errors.append("semantic audit is stale: draft_hash does not match discussion_trace.md")
    expected_contracts = [p.contract_id for p in paragraphs]
    paragraph_by_contract = {p.contract_id: p for p in paragraphs}
    reviewed = [p.get("contract_id") for p in report.get("paragraphs", [])]
    if sorted(expected_contracts) != sorted(reviewed):
        errors.append("semantic audit paragraphs do not match drafted paragraph contracts")
    if str(report.get("reviewer", "")).startswith("pending"):
        errors.append("semantic audit reviewer is still pending")
    if report.get("overall_status") != "pass":
        errors.append("semantic audit overall_status must be pass")
    for item in report.get("paragraphs", []):
        cid = item.get("contract_id", "unknown")
        if item.get("status") != "pass":
            errors.append(f"semantic audit {cid} status is not pass")
        if not item.get("one_central_claim"):
            errors.append(f"semantic audit {cid}: paragraph does not have one central claim")
        if not item.get("linked_result_focus"):
            errors.append(f"semantic audit {cid}: paragraph drifts from the linked result")
        if item.get("topic_drift"):
            errors.append(f"semantic audit {cid}: topic drift detected")
        if not item.get("return_to_study"):
            errors.append(f"semantic audit {cid}: paragraph does not return to the study result")
        if item.get("overclaiming"):
            errors.append(f"semantic audit {cid}: overclaiming detected: {item.get('overclaiming')}")
        if item.get("status") == "pass" and item.get("revision_instructions"):
            errors.append(f"semantic audit {cid}: pass status cannot contain revision instructions")
        expected_paragraph = paragraph_by_contract.get(cid)
        expected_claims = set(expected_paragraph.claims if expected_paragraph else [])
        assessed_claims = {x.get("claim_id") for x in item.get("citation_assessments", [])}
        if expected_claims != assessed_claims:
            errors.append(f"semantic audit {cid}: citation assessments must cover exactly {sorted(expected_claims)}; found {sorted(x for x in assessed_claims if x)}")
        expected_sentences = set(range(1, len(expected_paragraph.sentences) + 1)) if expected_paragraph else set()
        assessed_sentences = {x.get("sentence") for x in item.get("sentence_functions", [])}
        if expected_sentences != assessed_sentences:
            errors.append(f"semantic audit {cid}: sentence functions must cover every sentence")
        for citation in item.get("citation_assessments", []):
            if not str(citation.get("supported_statement", "")).strip():
                errors.append(f"semantic audit {cid}: {citation.get('claim_id')} lacks a supported-statement mapping")
            if not citation.get("advances_argument"):
                errors.append(f"semantic audit {cid}: {citation.get('claim_id')} does not advance the argument")
            if not str(citation.get("deletion_consequence", "")).strip():
                errors.append(f"semantic audit {cid}: {citation.get('claim_id')} lacks a deletion-consequence test")
    return errors, warnings
