"""Compatibility surface for v1 imports. New code should import focused v2 modules."""
from scripts.audit.runner import audit_draft, initialize_semantic_audit
from scripts.compiler import GateError, compile_draft
from scripts.evidence.exports import export_evidence_matrix
from scripts.evidence.models import create_evidence_card
from scripts.evidence.validation import validate_workspace
from scripts.argument.contracts import create_paragraph_contract
from scripts.indexing.search import build_index, index_is_fresh, search_for_result, search_index
from scripts.ingest import ExtractedUnit, extract_file
from scripts.workspace import init_workspace, workspace_path

__all__ = [
    "ExtractedUnit", "GateError", "audit_draft", "build_index", "compile_draft", "create_evidence_card",
    "create_paragraph_contract", "export_evidence_matrix", "extract_file", "index_is_fresh", "init_workspace",
    "initialize_semantic_audit", "search_for_result", "search_index", "validate_workspace", "workspace_path",
]
