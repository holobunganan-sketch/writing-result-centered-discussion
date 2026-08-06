from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.argument.contracts import create_paragraph_contract
from scripts.audit.runner import audit_draft, initialize_semantic_audit
from scripts.compiler import GateError, compile_draft
from scripts.docx_writeback import write_discussion_to_docx
from scripts.evidence.citations import build_citation_registry
from scripts.evidence.exports import export_comparability_matrix, export_evidence_matrix
from scripts.evidence.models import create_evidence_card, seal_evidence_card
from scripts.evidence.validation import validate_workspace
from scripts.indexing.search import build_index, index_is_fresh, search_for_result, search_index
from scripts.migration import migrate_v1
from scripts.revision import prepare_revision
from scripts.workspace import init_workspace, load_json


def _print(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2) if not isinstance(data, Path) else data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Result-centered Discussion v2 local evidence workflow")
    parser.add_argument("--project", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("index")
    sub.add_parser("freshness")
    search = sub.add_parser("search"); search.add_argument("--query", required=True); search.add_argument("--top-k", type=int, default=10); search.add_argument("--pool", choices=["external-evidence", "study-evidence", "context-only"])
    result = sub.add_parser("search-result"); result.add_argument("--result-id", required=True); result.add_argument("--top-k", type=int, default=12)
    card = sub.add_parser("new-card"); card.add_argument("--id", required=True); card.add_argument("--source", required=True)
    seal = sub.add_parser("seal-card"); seal.add_argument("--id", required=True)
    contract = sub.add_parser("new-contract"); contract.add_argument("--id", required=True); contract.add_argument("--results", required=True)
    sub.add_parser("validate")
    sub.add_parser("semantic-audit-init")
    sub.add_parser("audit")
    compile_p = sub.add_parser("compile"); compile_p.add_argument("--citation-mode", choices=["key", "rendered", "keep"], default="key")
    sub.add_parser("export-matrix")
    sub.add_parser("export-comparability")
    sub.add_parser("citation-registry")
    sub.add_parser("migrate-v1")
    revision = sub.add_parser("revision-intake"); revision.add_argument("--draft", required=True)
    docx = sub.add_parser("write-docx"); docx.add_argument("--manuscript", required=True); docx.add_argument("--output"); docx.add_argument("--heading", default="Discussion")
    sub.add_parser("selftest")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = Path(args.project).resolve()
    try:
        if args.command == "init": _print(init_workspace(project))
        elif args.command == "index": _print(build_index(project))
        elif args.command == "freshness":
            report = index_is_fresh(project); _print(report); return 0 if report["fresh"] else 1
        elif args.command == "search": _print(search_index(project, args.query, args.top_k, args.pool))
        elif args.command == "search-result": _print(search_for_result(project, args.result_id, args.top_k))
        elif args.command == "new-card": _print(create_evidence_card(project, args.id, args.source))
        elif args.command == "seal-card": _print(seal_evidence_card(project, args.id))
        elif args.command == "new-contract": _print(create_paragraph_contract(project, args.id, [x.strip() for x in args.results.split(",") if x.strip()]))
        elif args.command == "validate":
            report = validate_workspace(project); _print(report); return 1 if report["errors"] else 0
        elif args.command == "semantic-audit-init": _print(initialize_semantic_audit(project))
        elif args.command == "audit":
            report = audit_draft(project); _print(report); return 1 if report["errors"] else 0
        elif args.command == "compile": _print(compile_draft(project, args.citation_mode))
        elif args.command == "export-matrix": _print(export_evidence_matrix(project))
        elif args.command == "export-comparability": _print(export_comparability_matrix(project))
        elif args.command == "citation-registry": _print(build_citation_registry(project))
        elif args.command == "migrate-v1": _print(migrate_v1(project))
        elif args.command == "revision-intake": _print(prepare_revision(project, args.draft))
        elif args.command == "write-docx": _print(write_discussion_to_docx(project, args.manuscript, args.output, args.heading))
        elif args.command == "selftest":
            import unittest
            root = Path(__file__).resolve().parent.parent
            suite = unittest.defaultTestLoader.discover(str(root / "tests"))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if result.wasSuccessful() else 1
    except (FileNotFoundError, FileExistsError, ValueError, GateError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0
