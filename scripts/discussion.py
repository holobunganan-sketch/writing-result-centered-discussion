#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .discussion_core import (
        audit_draft,
        build_index,
        compile_draft,
        create_evidence_card,
        create_paragraph_contract,
        export_evidence_matrix,
        init_workspace,
        search_for_result,
        search_index,
        validate_workspace,
    )
except ImportError:
    from discussion_core import (  # type: ignore
        audit_draft,
        build_index,
        compile_draft,
        create_evidence_card,
        create_paragraph_contract,
        export_evidence_matrix,
        init_workspace,
        search_for_result,
        search_index,
        validate_workspace,
    )


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Local evidence and traceability tools for result-centred Discussion writing")
    p.add_argument("--project", default=".", help="Project directory containing manuscript files and references")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create .discussion-workspace")
    sub.add_parser("index", help="Extract and index project-local documents")

    search = sub.add_parser("search", help="Search the local BM25 index")
    search.add_argument("--query", required=True)
    search.add_argument("--top-k", type=int, default=10)

    result_search = sub.add_parser("search-result", help="Build a search query from one result ledger entry")
    result_search.add_argument("--result-id", required=True)
    result_search.add_argument("--top-k", type=int, default=12)

    card = sub.add_parser("new-card", help="Create a blank evidence card")
    card.add_argument("--id", required=True)
    card.add_argument("--source", required=True)
    card.add_argument("--locator", default="")

    contract = sub.add_parser("new-contract", help="Create a blank paragraph contract")
    contract.add_argument("--id", required=True)
    contract.add_argument("--results", required=True, help="Comma-separated result IDs")

    sub.add_parser("validate", help="Validate ledgers, evidence cards, contracts, and argument map")
    sub.add_parser("audit", help="Audit discussion_trace.md against contracts and evidence cards")

    compile_parser = sub.add_parser("compile", help="Strip trace comments and render citation markers")
    compile_parser.add_argument("--citation-mode", choices=["key", "rendered", "keep"], default="key")

    sub.add_parser("export-matrix", help="Export evidence cards to evidence_matrix.csv")
    sub.add_parser("selftest", help="Run the bundled unittest suite")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    project = Path(args.project).resolve()
    try:
        if args.command == "init":
            print(init_workspace(project))
        elif args.command == "index":
            _print_json(build_index(project))
        elif args.command == "search":
            _print_json(search_index(project, args.query, args.top_k))
        elif args.command == "search-result":
            _print_json(search_for_result(project, args.result_id, args.top_k))
        elif args.command == "new-card":
            print(create_evidence_card(project, args.id, args.source, args.locator))
        elif args.command == "new-contract":
            result_ids = [x.strip() for x in args.results.split(",") if x.strip()]
            print(create_paragraph_contract(project, args.id, result_ids))
        elif args.command == "validate":
            report = validate_workspace(project)
            _print_json(report)
            return 1 if report["errors"] else 0
        elif args.command == "audit":
            report = audit_draft(project)
            _print_json(report)
            return 1 if report["errors"] else 0
        elif args.command == "compile":
            print(compile_draft(project, args.citation_mode))
        elif args.command == "export-matrix":
            print(export_evidence_matrix(project))
        elif args.command == "selftest":
            import unittest
            root = Path(__file__).resolve().parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            suite = unittest.defaultTestLoader.discover(str(root / "tests"))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if result.wasSuccessful() else 1
    except (FileNotFoundError, FileExistsError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
