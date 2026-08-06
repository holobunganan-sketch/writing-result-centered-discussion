from __future__ import annotations

import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.audit.runner import audit_draft
from scripts.evidence.models import claim_index, load_cards
from scripts.evidence.validation import validate_workspace
from scripts.indexing.search import index_is_fresh
from scripts.workspace import SKILL_ROOT, dump_json, init_workspace, text_hash
from scripts.audit.parsing import CLAIM_RE


class GateError(RuntimeError):
    pass


def _version() -> str:
    return (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def compile_draft(project: Path | str, citation_mode: str = "key") -> Path:
    if citation_mode not in {"key", "rendered", "keep"}:
        raise ValueError("citation_mode must be key, rendered, or keep")
    root = Path(project).resolve()
    ws = init_workspace(root)
    source = ws / "discussion_trace.md"
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    gate = {
        "version": _version(), "started_at": datetime.now(timezone.utc).isoformat(), "draft_hash": text_hash(text),
        "status": "failed", "errors": [],
    }
    if not text.strip():
        gate["errors"] = ["discussion_trace.md is empty"]
        dump_json(ws / "release_gate.json", gate)
        raise GateError(gate["errors"][0])
    freshness = index_is_fresh(root)
    if not freshness["fresh"]:
        gate["errors"] = [f"Index/source state is stale: {freshness['changed']}"]
        dump_json(ws / "release_gate.json", gate)
        raise GateError(gate["errors"][0])

    validation = validate_workspace(root)
    audit = audit_draft(root)
    errors = [*validation["errors"], *audit["errors"]]
    if errors:
        gate["errors"] = errors
        gate["validation_metrics"] = validation["metrics"]
        gate["audit_metrics"] = audit["metrics"]
        dump_json(ws / "release_gate.json", gate)
        raise GateError("Release gate failed: " + " | ".join(errors[:5]))

    cards = load_cards(ws)
    claims = claim_index(cards)
    unknown = sorted(set(CLAIM_RE.findall(text)) - set(claims))
    if unknown:
        gate["errors"] = [f"Unknown claim citations: {unknown}"]
        dump_json(ws / "release_gate.json", gate)
        raise GateError(gate["errors"][0])

    def replace(match: re.Match[str]) -> str:
        claim_id = match.group(1)
        card = claims[claim_id]["card"]
        if citation_mode == "keep":
            return match.group(0)
        if citation_mode == "rendered":
            return card.get("rendered_citation") or f"[@{card.get('citation_key')}]"
        if citation_mode == "key":
            return f"[@{card.get('citation_key')}]"
        raise ValueError("citation_mode must be key, rendered, or keep")

    compiled = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    compiled = CLAIM_RE.sub(replace, compiled)
    compiled = re.sub(r"\n{3,}", "\n\n", compiled).strip() + "\n"
    if not compiled.strip():
        gate["errors"] = ["Compiled Discussion is empty"]
        dump_json(ws / "release_gate.json", gate)
        raise GateError(gate["errors"][0])
    output = ws / "discussion_final.md"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=ws, delete=False) as handle:
        handle.write(compiled)
        temp_path = Path(handle.name)
    temp_path.replace(output)
    gate.update({
        "status": "passed", "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot_hash": freshness["current_hash"], "final_hash": text_hash(compiled),
        "validation_metrics": validation["metrics"], "audit_metrics": audit["metrics"], "errors": [],
    })
    dump_json(ws / "release_gate.json", gate)
    return output
