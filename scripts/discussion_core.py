from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

WORKSPACE_NAME = ".discussion-workspace"
SUPPORTED_PLAIN = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json",
    ".yaml", ".yml", ".xml", ".html", ".htm", ".tex", ".bib", ".ris",
}
SUPPORTED_OFFICE = {".docx", ".pptx", ".xlsx"}
SUPPORTED_PDF = {".pdf"}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "__pycache__",
    WORKSPACE_NAME,
}
ALLOWED_ROLES = {
    "benchmark", "support", "contrast", "difference-explanation", "mechanism",
    "methodology", "implication", "boundary", "limitation",
}
ALLOWED_PRIORITIES = {"primary", "key-secondary", "secondary", "exploratory", "safety"}
ALLOWED_CAUSAL = {"causal", "associational", "descriptive"}
ALLOWED_CONTRACT_STATUS = {"approved", "draft"}
TRACE_RE = re.compile(r"<!--\s*D:(D[\w-]+)\s+R:([R\w, -]+)\s*-->")
REF_RE = re.compile(r"\[(REF-\d{3,})\]")


@dataclass
class ExtractedUnit:
    locator: str
    text: str


def _json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_load(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def workspace_path(project: Path | str) -> Path:
    return Path(project).resolve() / WORKSPACE_NAME


def init_workspace(project: Path | str, force: bool = False) -> Path:
    project_path = Path(project).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    workspace = workspace_path(project_path)
    workspace.mkdir(parents=True, exist_ok=True)
    for sub in ("index", "evidence_cards", "paragraph_contracts", "candidate_searches"):
        (workspace / sub).mkdir(parents=True, exist_ok=True)

    defaults: dict[str, Any] = {
        "config.json": {
            "version": 1,
            "project_root": str(project_path),
            "workspace": WORKSPACE_NAME,
            "chunk_chars": 1400,
            "chunk_overlap": 220,
            "citation_mode": "key",
            "max_candidate_hits": 12,
            "reference_roots": ["references", "reference", "literature", "papers", "文献", "参考文献"],
            "excluded_globs": [],
        },
        "result_ledger.json": {"study_title": "", "study_design": "", "results": []},
        "argument_map.json": {"global_main_line": "", "paragraph_order": []},
        "project_inventory.json": {"files": [], "unreadable_files": []},
        "audit_report.json": {"errors": [], "warnings": [], "metrics": {}},
    }
    for name, payload in defaults.items():
        path = workspace / name
        if force or not path.exists():
            _json_dump(path, payload)

    for name in ("discussion_trace.md", "discussion_final.md"):
        path = workspace / name
        if force or not path.exists():
            path.write_text("", encoding="utf-8")
    return workspace


def _iter_project_files(project: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(project):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            path = Path(root) / filename
            if path.suffix.lower() in SUPPORTED_PLAIN | SUPPORTED_OFFICE | SUPPORTED_PDF:
                yield path


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_plain(path: Path) -> list[ExtractedUnit]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [ExtractedUnit("document", _clean_text(text))]


def _xml_text(blob: bytes) -> str:
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        return ""
    chunks: list[str] = []
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag in {"t", "v"} and elem.text:
            chunks.append(elem.text)
        elif tag in {"p", "tr"}:
            chunks.append("\n")
    return _clean_text(" ".join(chunks).replace(" \n ", "\n"))


def _extract_docx(path: Path) -> list[ExtractedUnit]:
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n == "word/document.xml" or n.startswith("word/header") or n.startswith("word/footer")]
        units = []
        for name in sorted(names):
            text = _xml_text(archive.read(name))
            if text:
                units.append(ExtractedUnit(name, text))
        return units


def _extract_pptx(path: Path) -> list[ExtractedUnit]:
    with zipfile.ZipFile(path) as archive:
        slides = sorted(
            (n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n).group(1)),
        )
        units = []
        for name in slides:
            text = _xml_text(archive.read(name))
            if text:
                number = re.search(r"slide(\d+)\.xml", name).group(1)
                units.append(ExtractedUnit(f"slide {number}", text))
        return units


def _extract_xlsx(path: Path) -> list[ExtractedUnit]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root.iter():
                if si.tag.rsplit("}", 1)[-1] == "si":
                    shared.append(" ".join(t.text or "" for t in si.iter() if t.tag.rsplit("}", 1)[-1] == "t"))
        sheets = sorted(n for n in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        units: list[ExtractedUnit] = []
        for sheet in sheets:
            root = ET.fromstring(archive.read(sheet))
            values: list[str] = []
            for cell in root.iter():
                if cell.tag.rsplit("}", 1)[-1] != "c":
                    continue
                cell_type = cell.attrib.get("t")
                value_node = next((x for x in cell if x.tag.rsplit("}", 1)[-1] in {"v", "is"}), None)
                if value_node is None:
                    continue
                if cell_type == "s" and value_node.text and value_node.text.isdigit():
                    idx = int(value_node.text)
                    if 0 <= idx < len(shared):
                        values.append(shared[idx])
                else:
                    text = " ".join(t.text or "" for t in value_node.iter() if t.text)
                    if text:
                        values.append(text)
            text = _clean_text("\n".join(values))
            if text:
                number = re.search(r"sheet(\d+)\.xml", sheet).group(1)
                units.append(ExtractedUnit(f"sheet {number}", text))
        return units


def _extract_pdf_pypdf(path: Path) -> list[ExtractedUnit]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return []
    reader = PdfReader(str(path))
    units: list[ExtractedUnit] = []
    for idx, page in enumerate(reader.pages, 1):
        try:
            text = _clean_text(page.extract_text() or "")
        except Exception:
            text = ""
        if text:
            units.append(ExtractedUnit(f"page {idx}", text))
    return units


def _extract_pdf_pdftotext(path: Path) -> list[ExtractedUnit]:
    executable = shutil.which("pdftotext")
    if not executable:
        return []
    with tempfile.TemporaryDirectory(prefix="discussion-pdf-") as tmp:
        output = Path(tmp) / "out.txt"
        proc = subprocess.run(
            [executable, "-layout", str(path), str(output)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not output.exists():
            return []
        pages = output.read_text(encoding="utf-8", errors="replace").split("\f")
        return [
            ExtractedUnit(f"page {idx}", cleaned)
            for idx, page in enumerate(pages, 1)
            if (cleaned := _clean_text(page))
        ]


def extract_file(path: Path) -> tuple[list[ExtractedUnit], str | None]:
    suffix = path.suffix.lower()
    try:
        if suffix in SUPPORTED_PLAIN:
            units = _extract_plain(path)
        elif suffix == ".docx":
            units = _extract_docx(path)
        elif suffix == ".pptx":
            units = _extract_pptx(path)
        elif suffix == ".xlsx":
            units = _extract_xlsx(path)
        elif suffix == ".pdf":
            units = _extract_pdf_pypdf(path) or _extract_pdf_pdftotext(path)
            if not units:
                return [], "PDF text extraction unavailable or produced no text; install pypdf or pdftotext, or provide a text-searchable PDF"
        else:
            return [], "unsupported file type"
        units = [u for u in units if u.text.strip()]
        if not units:
            return [], "no extractable text"
        return units, None
    except (OSError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
        return [], f"{type(exc).__name__}: {exc}"


def _chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(start + max_chars, len(paragraph))
                chunks.append(paragraph[start:end])
                if end == len(paragraph):
                    break
                start = max(end - overlap, start + 1)
            continue
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            prefix = current[-overlap:] if overlap else ""
            current = (prefix + "\n\n" + paragraph).strip()
    if current:
        chunks.append(current)
    return chunks


def build_index(project: Path | str) -> dict[str, Any]:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    config = _json_load(workspace / "config.json", {})
    max_chars = int(config.get("chunk_chars", 1400))
    overlap = int(config.get("chunk_overlap", 220))
    records: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []

    for path in _iter_project_files(project_path):
        rel = path.relative_to(project_path).as_posix()
        units, error = extract_file(path)
        if error:
            unreadable.append({"path": rel, "reason": error})
            inventory.append({"path": rel, "status": "unreadable", "reason": error})
            continue
        file_chunks = 0
        for unit in units:
            for idx, chunk in enumerate(_chunk_text(unit.text, max_chars, overlap), 1):
                digest = hashlib.sha1(f"{rel}|{unit.locator}|{idx}|{chunk}".encode("utf-8")).hexdigest()[:16]
                records.append({
                    "chunk_id": digest,
                    "path": rel,
                    "locator": unit.locator,
                    "chunk_number": idx,
                    "text": chunk,
                })
                file_chunks += 1
        inventory.append({"path": rel, "status": "indexed", "chunks": file_chunks})

    index_path = workspace / "index" / "chunks.jsonl"
    with index_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    manifest = {
        "version": 1,
        "indexed_files": sum(1 for item in inventory if item["status"] == "indexed"),
        "unreadable_files": len(unreadable),
        "chunks": len(records),
        "documents": inventory,
    }
    _json_dump(workspace / "index" / "manifest.json", manifest)
    _json_dump(workspace / "project_inventory.json", {"files": inventory, "unreadable_files": unreadable})
    return manifest


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    latin = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", lowered)
    han_runs = re.findall(r"[\u3400-\u9fff]+", lowered)
    han_tokens: list[str] = []
    for run in han_runs:
        han_tokens.extend(list(run))
        han_tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return latin + han_tokens


def _load_chunks(project: Path) -> list[dict[str, Any]]:
    index_path = workspace_path(project) / "index" / "chunks.jsonl"
    if not index_path.exists():
        raise FileNotFoundError("Index missing. Run the index command first.")
    chunks = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunks.append(json.loads(line))
    return chunks


def search_index(project: Path | str, query: str, top_k: int = 10) -> list[dict[str, Any]]:
    project_path = Path(project).resolve()
    chunks = _load_chunks(project_path)
    if not chunks:
        return []
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    tokenized = [_tokenize(item["text"]) for item in chunks]
    lengths = [len(tokens) or 1 for tokens in tokenized]
    avgdl = sum(lengths) / len(lengths)
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    n_docs = len(chunks)
    k1, b = 1.5, 0.75
    scores: list[tuple[float, int]] = []
    q_counts = Counter(query_tokens)
    for idx, tokens in enumerate(tokenized):
        counts = Counter(tokens)
        score = 0.0
        for term, qtf in q_counts.items():
            tf = counts.get(term, 0)
            if not tf:
                continue
            df = document_frequency.get(term, 0)
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            denom = tf + k1 * (1 - b + b * lengths[idx] / avgdl)
            score += idf * (tf * (k1 + 1) / denom) * (1 + math.log(qtf))
        if score > 0:
            scores.append((score, idx))
    scores.sort(key=lambda item: (-item[0], chunks[item[1]]["path"], chunks[item[1]]["chunk_number"]))
    hits = []
    for score, idx in scores[:top_k]:
        item = dict(chunks[idx])
        item["score"] = round(score, 6)
        item["snippet"] = re.sub(r"\s+", " ", item["text"])[:500]
        hits.append(item)
    return hits


def search_for_result(project: Path | str, result_id: str, top_k: int = 12) -> list[dict[str, Any]]:
    project_path = Path(project).resolve()
    workspace = workspace_path(project_path)
    ledger = _json_load(workspace / "result_ledger.json", {})
    result = next((r for r in ledger.get("results", []) if r.get("id") == result_id), None)
    if result is None:
        raise ValueError(f"Unknown result id: {result_id}")
    query_parts = [result.get("finding", ""), result.get("effect_size", "")]
    query_parts.extend(result.get("discussion_questions", []))
    config = _json_load(workspace / "config.json", {})
    reference_roots = [str(root).strip("/\\") for root in config.get("reference_roots", []) if str(root).strip()]
    raw_hits = search_index(
        project_path,
        " ".join(str(x) for x in query_parts if x),
        top_k=max(top_k * 4, top_k),
    )
    reference_hits = [
        hit for hit in raw_hits
        if any(hit["path"] == root or hit["path"].startswith(root + "/") for root in reference_roots)
    ]
    hits = (reference_hits or raw_hits)[:top_k]
    output = workspace / "candidate_searches" / f"{result_id}.md"
    lines = [f"# Candidate evidence for {result_id}", "", f"Query source: {result.get('finding', '')}", ""]
    for idx, hit in enumerate(hits, 1):
        lines.extend([
            f"## {idx}. `{hit['path']}` — {hit['locator']}",
            f"Score: {hit['score']}",
            "",
            hit["snippet"],
            "",
        ])
    output.write_text("\n".join(lines), encoding="utf-8")
    return hits


def _load_cards(workspace: Path) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for path in sorted((workspace / "evidence_cards").glob("*.json")):
        try:
            card = _json_load(path, {})
        except json.JSONDecodeError:
            continue
        card_id = card.get("id")
        if card_id:
            cards[card_id] = card
    return cards


def _load_contracts(workspace: Path) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path in sorted((workspace / "paragraph_contracts").glob("*.json")):
        try:
            contract = _json_load(path, {})
        except json.JSONDecodeError:
            continue
        contract_id = contract.get("id")
        if contract_id:
            contracts[contract_id] = contract
    return contracts


def _required_string(obj: dict[str, Any], field: str, context: str, errors: list[str]) -> None:
    if not isinstance(obj.get(field), str) or not obj[field].strip():
        errors.append(f"{context}.{field} must be a non-empty string")


def _required_list(obj: dict[str, Any], field: str, context: str, errors: list[str]) -> None:
    if not isinstance(obj.get(field), list) or len(obj[field]) == 0:
        errors.append(f"{context}.{field} must be a non-empty list")


def validate_workspace(project: Path | str) -> dict[str, Any]:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    errors: list[str] = []
    warnings: list[str] = []

    try:
        ledger = _json_load(workspace / "result_ledger.json", {})
    except json.JSONDecodeError as exc:
        return {"errors": [f"result_ledger.json invalid JSON: {exc}"], "warnings": [], "metrics": {}}
    results = ledger.get("results")
    if not isinstance(results, list) or not results:
        errors.append("result_ledger.results must contain at least one result")
        results = []
    result_ids: set[str] = set()
    for idx, result in enumerate(results):
        context = f"result_ledger.results[{idx}]"
        _required_string(result, "id", context, errors)
        result_id = result.get("id")
        if result_id in result_ids:
            errors.append(f"Duplicate result id: {result_id}")
        if isinstance(result_id, str):
            result_ids.add(result_id)
        for field in ("finding", "effect_direction", "effect_size", "uncertainty", "analysis_status", "causal_ceiling", "importance"):
            _required_string(result, field, context, errors)
        source = result.get("source")
        if not isinstance(source, dict):
            errors.append(f"{context}.source must be an object")
        else:
            _required_string(source, "file", f"{context}.source", errors)
            _required_string(source, "locator", f"{context}.source", errors)
            source_file = source.get("file")
            if isinstance(source_file, str) and source_file and not (project_path / source_file).exists():
                warnings.append(f"{context}.source.file does not exist: {source_file}")
        _required_list(result, "discussion_questions", context, errors)
        if result.get("priority") not in ALLOWED_PRIORITIES:
            errors.append(f"{context}.priority must be one of {sorted(ALLOWED_PRIORITIES)}")
        if result.get("causal_ceiling") not in ALLOWED_CAUSAL:
            errors.append(f"{context}.causal_ceiling must be one of {sorted(ALLOWED_CAUSAL)}")

    cards: dict[str, dict[str, Any]] = {}
    card_paths = sorted((workspace / "evidence_cards").glob("*.json"))
    for path in card_paths:
        context = f"evidence_cards/{path.name}"
        try:
            card = _json_load(path, {})
        except json.JSONDecodeError as exc:
            errors.append(f"{context} invalid JSON: {exc}")
            continue
        card_id = card.get("id")
        _required_string(card, "id", context, errors)
        if card_id in cards:
            errors.append(f"Duplicate evidence card id: {card_id}")
        if isinstance(card_id, str):
            cards[card_id] = card
        for field in ("citation_key", "source_file", "locator", "population", "design", "sample_size", "exposure_or_intervention", "outcome", "main_finding", "relevance_reason"):
            _required_string(card, field, context, errors)
        _required_list(card, "linked_results", context, errors)
        _required_list(card, "evidence_roles", context, errors)
        _required_list(card, "usable_claims", context, errors)
        for linked in card.get("linked_results", []):
            if linked not in result_ids:
                errors.append(f"{context}.linked_results contains unknown result: {linked}")
        roles = card.get("evidence_roles", [])
        invalid_roles = sorted(set(roles) - ALLOWED_ROLES) if isinstance(roles, list) else []
        if invalid_roles:
            errors.append(f"{context}.evidence_roles contains invalid roles: {invalid_roles}")
        if card.get("verified_full_text") is not True:
            errors.append(f"{context}.verified_full_text must be true before drafting")
        source_file = card.get("source_file")
        if isinstance(source_file, str) and source_file and not (project_path / source_file).exists():
            errors.append(f"{context}.source_file does not exist: {source_file}")
        for claim_idx, claim in enumerate(card.get("usable_claims", [])):
            claim_context = f"{context}.usable_claims[{claim_idx}]"
            if not isinstance(claim, dict):
                errors.append(f"{claim_context} must be an object")
                continue
            _required_string(claim, "claim", claim_context, errors)
            _required_string(claim, "locator", claim_context, errors)

    contracts: dict[str, dict[str, Any]] = {}
    contract_paths = sorted((workspace / "paragraph_contracts").glob("*.json"))
    for path in contract_paths:
        context = f"paragraph_contracts/{path.name}"
        try:
            contract = _json_load(path, {})
        except json.JSONDecodeError as exc:
            errors.append(f"{context} invalid JSON: {exc}")
            continue
        contract_id = contract.get("id")
        _required_string(contract, "id", context, errors)
        if contract_id in contracts:
            errors.append(f"Duplicate paragraph contract id: {contract_id}")
        if isinstance(contract_id, str):
            contracts[contract_id] = contract
        for field in ("discussion_question", "central_claim", "closing_message", "claim_strength"):
            _required_string(contract, field, context, errors)
        _required_list(contract, "linked_results", context, errors)
        _required_list(contract, "argument_steps", context, errors)
        if not isinstance(contract.get("allowed_references"), list):
            errors.append(f"{context}.allowed_references must be a list")
        for linked in contract.get("linked_results", []):
            if linked not in result_ids:
                errors.append(f"{context}.linked_results contains unknown result: {linked}")
        allowed_refs = set(contract.get("allowed_references", []))
        for ref in allowed_refs:
            if ref not in cards:
                errors.append(f"{context}.allowed_references contains unknown evidence card: {ref}")
            elif not (set(contract.get("linked_results", [])) & set(cards[ref].get("linked_results", []))):
                errors.append(f"{context}: {ref} is not linked to any result used by the paragraph")
        step_refs: set[str] = set()
        for step_idx, step in enumerate(contract.get("argument_steps", [])):
            step_context = f"{context}.argument_steps[{step_idx}]"
            if not isinstance(step, dict):
                errors.append(f"{step_context} must be an object")
                continue
            _required_string(step, "type", step_context, errors)
            _required_string(step, "content", step_context, errors)
            refs = step.get("references", [])
            if not isinstance(refs, list):
                errors.append(f"{step_context}.references must be a list")
                continue
            step_refs.update(refs)
        undeclared = sorted(step_refs - allowed_refs)
        if undeclared:
            errors.append(f"{context} uses references outside allowed_references: {undeclared}")
        unused = sorted(allowed_refs - step_refs)
        if unused:
            warnings.append(f"{context} allows references that no argument step uses: {unused}")
        if contract.get("status") not in ALLOWED_CONTRACT_STATUS:
            errors.append(f"{context}.status must be one of {sorted(ALLOWED_CONTRACT_STATUS)}")
        elif contract.get("status") != "approved":
            errors.append(f"{context}.status must be approved before drafting")

    argument_map = _json_load(workspace / "argument_map.json", {})
    order = argument_map.get("paragraph_order", [])
    if contract_paths and not order:
        errors.append("argument_map.paragraph_order must list approved paragraph contracts")
    if not isinstance(order, list):
        errors.append("argument_map.paragraph_order must be a list")
        order = []
    for contract_id in order:
        if contract_id not in contracts:
            errors.append(f"argument_map.paragraph_order contains unknown contract: {contract_id}")
    missing_from_map = sorted(set(contracts) - set(order))
    if missing_from_map:
        warnings.append(f"Contracts missing from argument_map.paragraph_order: {missing_from_map}")

    metrics = {
        "results": len(results),
        "evidence_cards": len(cards),
        "paragraph_contracts": len(contracts),
        "approved_contracts": sum(1 for c in contracts.values() if c.get("status") == "approved"),
    }
    report = {"errors": errors, "warnings": warnings, "metrics": metrics}
    _json_dump(workspace / "validation_report.json", report)
    return report


def _paragraph_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def audit_draft(project: Path | str) -> dict[str, Any]:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    draft_path = workspace / "discussion_trace.md"
    text = draft_path.read_text(encoding="utf-8") if draft_path.exists() else ""
    cards = _load_cards(workspace)
    contracts = _load_contracts(workspace)
    errors: list[str] = []
    warnings: list[str] = []
    cited_refs: Counter[str] = Counter()
    covered_results: Counter[str] = Counter()
    audited_paragraphs = 0

    for idx, block in enumerate(_paragraph_blocks(text), 1):
        if block.startswith("#"):
            continue
        audited_paragraphs += 1
        trace = TRACE_RE.search(block)
        if not trace:
            errors.append(f"Paragraph {idx} has no trace header <!-- D:D# R:R# -->")
            continue
        contract_id = trace.group(1)
        result_ids = [part.strip() for part in trace.group(2).split(",") if part.strip()]
        for result_id in result_ids:
            covered_results[result_id] += 1
        if contract_id not in contracts:
            errors.append(f"Paragraph {idx} references unknown contract {contract_id}")
            continue
        contract = contracts[contract_id]
        contract_results = set(contract.get("linked_results", []))
        if set(result_ids) != contract_results:
            errors.append(
                f"Paragraph {idx} trace results {sorted(result_ids)} do not match {contract_id} linked_results {sorted(contract_results)}"
            )
        refs = REF_RE.findall(block)
        allowed = set(contract.get("allowed_references", []))
        for ref in refs:
            cited_refs[ref] += 1
            if ref not in cards:
                errors.append(f"Paragraph {idx} cites unknown evidence card {ref}")
            if ref not in allowed:
                errors.append(f"Paragraph {idx} cites {ref} outside {contract_id}.allowed_references")
            elif not (set(result_ids) & set(cards.get(ref, {}).get("linked_results", []))):
                errors.append(f"Paragraph {idx} cites {ref}, which is not linked to traced results {result_ids}")
        missing_allowed = sorted(allowed - set(refs))
        if missing_allowed:
            warnings.append(f"Paragraph {idx} does not use contracted references: {missing_allowed}")
        word_count = len(re.findall(r"\b\w+\b", re.sub(r"<!--.*?-->", "", block, flags=re.S)))
        if word_count > 450:
            warnings.append(f"Paragraph {idx} is long ({word_count} words); verify that it contains one central claim")
        sentence_count = len([s for s in re.split(r"(?<=[.!?。！？])\s+", block) if s.strip()])
        if refs and sentence_count >= 2:
            reference_only_sentences = 0
            for sentence in re.split(r"(?<=[.!?。！？])\s+", block):
                if len(REF_RE.findall(sentence)) >= 2 and not re.search(r"\b(therefore|because|whereas|which|suggest|indicat|explain|consistent|contrast|difference|可能|因此|提示|解释|一致|差异|限制)\b", sentence, flags=re.I):
                    reference_only_sentences += 1
            if reference_only_sentences:
                warnings.append(f"Paragraph {idx} contains citation-dense sentences; verify that each citation advances the argument")

    for ref_id in cards:
        if cited_refs[ref_id] == 0:
            warnings.append(f"Evidence card {ref_id} is unused in the draft")
    for contract_id in contracts:
        if not re.search(rf"<!--\s*D:{re.escape(contract_id)}\b", text):
            warnings.append(f"Approved contract {contract_id} has no draft paragraph")

    validation = validate_workspace(project_path)
    if validation["errors"]:
        errors.extend(f"Workspace validation: {item}" for item in validation["errors"])
    metrics = {
        "paragraphs": audited_paragraphs,
        "unique_references_cited": len(cited_refs),
        "total_reference_mentions": sum(cited_refs.values()),
        "results_covered": sorted(covered_results),
        "contracts_available": len(contracts),
    }
    report = {"errors": errors, "warnings": warnings, "metrics": metrics}
    _json_dump(workspace / "audit_report.json", report)
    return report


def compile_draft(project: Path | str, citation_mode: str = "key") -> Path:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    source = workspace / "discussion_trace.md"
    if not source.exists():
        raise FileNotFoundError(f"Missing draft: {source}")
    text = source.read_text(encoding="utf-8")
    cards = _load_cards(workspace)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    def replace(match: re.Match[str]) -> str:
        ref_id = match.group(1)
        card = cards.get(ref_id)
        if not card:
            return match.group(0)
        if citation_mode == "keep":
            return match.group(0)
        if citation_mode == "rendered":
            return card.get("rendered_citation") or f"[@{card.get('citation_key', ref_id)}]"
        if citation_mode == "key":
            return f"[@{card.get('citation_key', ref_id)}]"
        raise ValueError("citation_mode must be one of: key, rendered, keep")

    text = REF_RE.sub(replace, text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    output = workspace / "discussion_final.md"
    output.write_text(text, encoding="utf-8")
    return output


def create_evidence_card(project: Path | str, ref_id: str, source_file: str, locator: str = "") -> Path:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    if not re.fullmatch(r"REF-\d{3,}", ref_id):
        raise ValueError("ref_id must use REF-001 format")
    path = workspace / "evidence_cards" / f"{ref_id}.json"
    if path.exists():
        raise FileExistsError(path)
    payload = {
        "id": ref_id,
        "citation_key": "",
        "rendered_citation": "",
        "source_file": source_file,
        "locator": locator,
        "population": "",
        "design": "",
        "sample_size": "",
        "exposure_or_intervention": "",
        "outcome": "",
        "main_finding": "",
        "effect_size": "not reported",
        "limitations": [],
        "linked_results": [],
        "evidence_roles": [],
        "relevance_reason": "",
        "usable_claims": [],
        "forbidden_inferences": [],
        "verified_full_text": False,
    }
    _json_dump(path, payload)
    return path


def create_paragraph_contract(project: Path | str, contract_id: str, linked_results: list[str]) -> Path:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    if not re.fullmatch(r"D\d+", contract_id):
        raise ValueError("contract_id must use D1 format")
    path = workspace / "paragraph_contracts" / f"{contract_id}.json"
    if path.exists():
        raise FileExistsError(path)
    payload = {
        "id": contract_id,
        "linked_results": linked_results,
        "discussion_question": "",
        "central_claim": "",
        "claim_strength": "",
        "argument_steps": [],
        "allowed_references": [],
        "closing_message": "",
        "status": "draft",
    }
    _json_dump(path, payload)
    return path


def export_evidence_matrix(project: Path | str) -> Path:
    project_path = Path(project).resolve()
    workspace = init_workspace(project_path)
    cards = _load_cards(workspace)
    output = workspace / "evidence_matrix.csv"
    fields = [
        "id", "citation_key", "source_file", "locator", "design", "population",
        "sample_size", "outcome", "main_finding", "effect_size", "linked_results",
        "evidence_roles", "relevance_reason", "verified_full_text",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for ref_id in sorted(cards):
            card = cards[ref_id]
            row = {field: card.get(field, "") for field in fields}
            row["linked_results"] = ";".join(card.get("linked_results", []))
            row["evidence_roles"] = ";".join(card.get("evidence_roles", []))
            writer.writerow(row)
    return output
