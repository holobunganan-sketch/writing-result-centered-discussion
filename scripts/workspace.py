from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

WORKSPACE_NAME = ".discussion-workspace"
SKILL_ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".xml", ".html", ".htm", ".tex", ".bib", ".ris", ".docx", ".pptx", ".xlsx", ".pdf",
}
SKIP_DIRS = {".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "__pycache__", WORKSPACE_NAME, ".worktrees"}

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 2,
    "chunk_chars": 1400,
    "chunk_overlap": 220,
    "citation_mode": "key",
    "max_candidate_hits": 12,
    "excluded_globs": [],
    "file_pools": {
        "external-evidence": ["references/**", "reference/**", "literature/**", "papers/**", "文献/**", "参考文献/**"],
        "study-evidence": ["results/**", "result/**", "tables/**", "figures/**", "manuscript*", "results.*", "论文*"],
        "context-only": ["protocol/**", "notes/**", "background/**", "方案/**", "笔记/**"],
    },
    "glossary": {},
    "retrieval": {
        "bm25_weight": 0.50,
        "semantic_weight": 0.25,
        "comparability_weight": 0.25,
        "semantic_backend": "tfidf",
        "min_score": 0.05,
    },
    "ocr": {"enabled": False, "language": "eng"},
    "journal_constraints": {"max_discussion_words": 0, "max_paragraph_words": 0, "max_paragraphs": 0},
}


def workspace_path(project: Path | str) -> Path:
    return Path(project).resolve() / WORKSPACE_NAME


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _deep_merge(default: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(default))
    for key, value in current.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def init_workspace(project: Path | str, force: bool = False) -> Path:
    project_path = Path(project).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    ws = workspace_path(project_path)
    ws.mkdir(parents=True, exist_ok=True)
    for sub in ("index", "evidence_cards", "paragraph_contracts", "candidate_searches", "semantic_audit"):
        (ws / sub).mkdir(parents=True, exist_ok=True)

    config_path = ws / "config.json"
    current = {} if force else load_json(config_path, {})
    config = _deep_merge(DEFAULT_CONFIG, current if isinstance(current, dict) else {})
    config["project_root"] = str(project_path)
    config["workspace"] = WORKSPACE_NAME
    dump_json(config_path, config)

    defaults: dict[str, Any] = {
        "result_ledger.json": {"study_title": "", "study_design": "", "study_profile": {}, "results": []},
        "argument_map.json": {"global_main_line": "", "paragraph_order": []},
        "comparability_matrix.json": {"rows": []},
        "evidence_tension_map.json": {"results": []},
        "project_inventory.json": {"files": [], "unreadable_files": [], "excluded_files": []},
        "audit_report.json": {"errors": [], "warnings": [], "metrics": {}},
        "validation_report.json": {"errors": [], "warnings": [], "metrics": {}},
    }
    for name, payload in defaults.items():
        path = ws / name
        if force or not path.exists():
            dump_json(path, payload)
    for name in ("discussion_trace.md", "discussion_final.md"):
        path = ws / name
        if force or not path.exists():
            path.write_text("", encoding="utf-8")
    return ws


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _matches(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    p = PurePosixPath(path)
    return p.match(pattern) or fnmatch.fnmatch(path, pattern) or (pattern.endswith("/**") and path.startswith(pattern[:-3].rstrip("/") + "/"))


def file_role(relative_path: str, config: dict[str, Any]) -> str:
    rel = relative_path.replace("\\", "/")
    if any(_matches(rel, pattern) for pattern in config.get("excluded_globs", [])):
        return "excluded"
    for role in ("external-evidence", "study-evidence", "context-only"):
        if any(_matches(rel, pattern) for pattern in config.get("file_pools", {}).get(role, [])):
            return role
    return "context-only"


def iter_project_files(project: Path | str, config: dict[str, Any] | None = None, include_excluded: bool = False) -> Iterable[tuple[Path, str, str]]:
    root = Path(project).resolve()
    config = config or load_json(init_workspace(root) / "config.json", DEFAULT_CONFIG)
    for current_root, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(current_root) / name
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            rel = path.relative_to(root).as_posix()
            role = file_role(rel, config)
            if role == "excluded" and not include_excluded:
                continue
            yield path, rel, role


def current_source_snapshot(project: Path | str) -> dict[str, str]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    config = load_json(ws / "config.json", DEFAULT_CONFIG)
    return {rel: file_hash(path) for path, rel, role in iter_project_files(root, config) if role != "excluded"}


def snapshot_hash(snapshot: dict[str, str]) -> str:
    payload = "\n".join(f"{key}\t{snapshot[key]}" for key in sorted(snapshot))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
