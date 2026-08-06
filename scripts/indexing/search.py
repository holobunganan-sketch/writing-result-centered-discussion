from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.ingest import extract_file
from scripts.workspace import (
    current_source_snapshot, dump_json, file_hash, init_workspace, iter_project_files, load_json, snapshot_hash, text_hash,
)
from . import bm25, semantic
from .dedup import group_duplicates, identifiers
from .query_expansion import expand_query


def _chunk(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    result: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            split = max(text.rfind("。", start, end), text.rfind(". ", start, end), text.rfind("\n", start, end))
            if split > start + size // 2:
                end = split + 1
        result.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return [x for x in result if x]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_index(project: Path | str) -> dict[str, Any]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    config = load_json(ws / "config.json", {})
    index_dir = ws / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    previous_inventory = {x.get("path"): x for x in load_json(ws / "project_inventory.json", {}).get("files", [])}
    previous_units = _load_jsonl(index_dir / "units.jsonl")
    previous_chunks = _load_jsonl(index_dir / "chunks.jsonl")
    units_by_path: dict[str, list[dict[str, Any]]] = {}
    chunks_by_path: dict[str, list[dict[str, Any]]] = {}
    for row in previous_units:
        units_by_path.setdefault(row.get("path", ""), []).append(row)
    for row in previous_chunks:
        chunks_by_path.setdefault(row.get("path", ""), []).append(row)
    previous_state = load_json(index_dir / "state.json", {})
    index_config = {"chunk_chars": config.get("chunk_chars"), "chunk_overlap": config.get("chunk_overlap"), "ocr": config.get("ocr", {})}
    config_hash = text_hash(json.dumps(index_config, ensure_ascii=False, sort_keys=True))
    can_reuse = previous_state.get("index_config_hash") == config_hash

    inventory: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    units_rows: list[dict[str, Any]] = []
    chunks_rows: list[dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    source_snapshot: dict[str, str] = {}
    reused_files = 0
    reindexed_files = 0
    excluded_files: list[str] = []
    for path, rel, role in iter_project_files(root, config, include_excluded=True):
        if role == "excluded":
            excluded_files.append(rel)
            continue
        digest = file_hash(path)
        source_snapshot[rel] = digest
        previous = previous_inventory.get(rel)
        if can_reuse and previous and previous.get("sha256") == digest and previous.get("role") == role and rel in units_by_path:
            inventory.append(previous)
            units_rows.extend(units_by_path.get(rel, []))
            chunks_rows.extend(chunks_by_path.get(rel, []))
            role_counts[role] += 1
            reused_files += 1
            continue
        units, error = extract_file(path, config)
        reindexed_files += 1
        if error:
            unreadable.append({"path": rel, "role": role, "error": error, "sha256": digest})
            continue
        preview = "\n".join(u.text for u in units)[:5000]
        record = {
            "path": rel, "role": role, "sha256": digest, "size": path.stat().st_size,
            "units": len(units), "quality_score": round(sum(u.quality_score for u in units) / len(units), 4),
            "identifiers": identifiers(preview),
        }
        inventory.append(record)
        role_counts[role] += 1
        for u_idx, extracted in enumerate(units, 1):
            unit_id = f"{rel}::{u_idx}"
            units_rows.append({
                "unit_id": unit_id, "path": rel, "role": role, "source_hash": digest,
                "locator": extracted.locator, "text": extracted.text,
                "quality_score": extracted.quality_score, "metadata": extracted.metadata,
            })
            for c_idx, text in enumerate(_chunk(extracted.text, int(config["chunk_chars"]), int(config["chunk_overlap"])), 1):
                chunks_rows.append({
                    "chunk_id": f"{unit_id}::{c_idx}", "unit_id": unit_id, "path": rel, "role": role,
                    "source_hash": digest, "locator": extracted.locator, "text": text,
                    "quality_score": extracted.quality_score, "identifiers": record["identifiers"],
                })
    duplicate_data = group_duplicates(inventory)
    for name, rows in (("units.jsonl", units_rows), ("chunks.jsonl", chunks_rows)):
        with (index_dir / name).open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    dump_json(index_dir / "duplicate_groups.json", duplicate_data)
    state = {
        "version": 2, "built_at": datetime.now(timezone.utc).isoformat(), "source_snapshot": source_snapshot,
        "source_snapshot_hash": snapshot_hash(source_snapshot), "indexed_files": len(inventory), "chunks": len(chunks_rows),
        "index_config_hash": config_hash,
    }
    dump_json(index_dir / "state.json", state)
    dump_json(ws / "project_inventory.json", {"files": inventory, "unreadable_files": unreadable, "excluded_files": sorted(excluded_files)})
    return {
        "indexed_files": len(inventory), "unreadable_files": len(unreadable), "chunks": len(chunks_rows),
        "role_counts": dict(role_counts), "source_snapshot_hash": state["source_snapshot_hash"],
        "reused_files": reused_files, "reindexed_files": reindexed_files,
    }


def index_is_fresh(project: Path | str) -> dict[str, Any]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    state = load_json(ws / "index" / "state.json", {})
    old = state.get("source_snapshot", {}) if isinstance(state, dict) else {}
    current = current_source_snapshot(root)
    changed = sorted(path for path in set(old) | set(current) if old.get(path) != current.get(path))
    return {"fresh": bool(state) and not changed, "changed": changed, "expected_hash": state.get("source_snapshot_hash", ""), "current_hash": snapshot_hash(current)}


def _profile_terms(profile: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "population": [str(profile.get("population", ""))],
        "intervention_or_exposure": [str(profile.get("exposure_or_intervention", ""))],
        "comparator": [str(profile.get("comparator", ""))],
        "outcome": [str(x) for x in profile.get("outcomes", [])],
        "setting": [str(profile.get("setting", ""))],
        "follow_up": [str(profile.get("follow_up", ""))],
    }


def _comparability(text: str, profile: dict[str, Any] | None) -> float:
    if not profile:
        return 0.0
    dimensions = _profile_terms(profile)
    present = 0
    possible = 0
    for values in dimensions.values():
        values = [v for v in values if v]
        if not values:
            continue
        possible += 1
        tokens = set(bm25.tokenize(" ".join(values)))
        doc_tokens = set(bm25.tokenize(text.casefold()))
        if tokens and len(tokens & doc_tokens) / len(tokens) >= 0.25:
            present += 1
    return present / possible if possible else 0.0


def search_index(project: Path | str, query: str, top_k: int = 10, pool: str | None = None, profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    freshness = index_is_fresh(root)
    if not freshness["fresh"]:
        raise ValueError(f"Index is stale or missing; run index. Changed: {freshness['changed']}")
    config = load_json(ws / "config.json", {})
    rows = _load_jsonl(ws / "index" / "chunks.jsonl")
    if pool:
        rows = [x for x in rows if x.get("role") == pool]
    if not rows:
        return []
    expanded_terms = expand_query(query, config.get("glossary", {}))
    expanded = " ".join(expanded_terms)
    documents = [x["text"] for x in rows]
    bm = bm25.scores(documents, expanded)
    sem = semantic.scores(documents, expanded, config.get("retrieval", {}).get("semantic_backend", "tfidf"))
    weights = config.get("retrieval", {})
    w_bm = float(weights.get("bm25_weight", 0.5))
    w_sem = float(weights.get("semantic_weight", 0.25))
    w_comp = float(weights.get("comparability_weight", 0.25))
    duplicates = load_json(ws / "index" / "duplicate_groups.json", {"canonical_by_path": {}}).get("canonical_by_path", {})
    candidates: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        comp = _comparability(row["text"], profile)
        quality = float(row.get("quality_score", 1.0))
        total = (w_bm * bm[idx] + w_sem * sem[idx] + w_comp * comp) * (0.8 + 0.2 * quality)
        candidates.append({
            "path": row["path"], "locator": row["locator"], "role": row["role"], "text": row["text"],
            "source_hash": row["source_hash"], "score": round(total, 6),
            "score_components": {"bm25": round(bm[idx], 6), "semantic": round(float(sem[idx]), 6), "comparability": round(comp, 6), "quality": round(quality, 6)},
            "expanded_query": expanded, "identifiers": row.get("identifiers", {}),
            "canonical_path": duplicates.get(row["path"], row["path"]),
        })
    min_score = float(config.get("retrieval", {}).get("min_score", 0.05))
    candidates = [item for item in candidates if item["score"] >= min_score]
    candidates.sort(key=lambda x: (-x["score"], x["path"], x["locator"]))
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in candidates:
        canonical = item["canonical_path"]
        if canonical in seen:
            continue
        seen.add(canonical)
        output.append(item)
        if len(output) >= top_k:
            break
    return output


def search_for_result(project: Path | str, result_id: str, top_k: int = 12) -> list[dict[str, Any]]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    ledger = load_json(ws / "result_ledger.json", {})
    result = next((x for x in ledger.get("results", []) if x.get("id") == result_id), None)
    if not result:
        raise ValueError(f"Unknown result_id: {result_id}")
    profile = ledger.get("study_profile", {})
    query = " ".join([
        result.get("finding", ""), result.get("effect_direction", ""), result.get("effect_size", ""),
        " ".join(result.get("discussion_questions", [])), " ".join(str(v) for v in profile.values() if not isinstance(v, list)),
        " ".join(profile.get("outcomes", [])),
    ])
    hits = search_index(root, query, top_k=top_k, pool="external-evidence", profile=profile)
    dump_json(ws / "candidate_searches" / f"{result_id}.json", {"result_id": result_id, "query": query, "pool": "external-evidence", "hits": hits})
    return hits
