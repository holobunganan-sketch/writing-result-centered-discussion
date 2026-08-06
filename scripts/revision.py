from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.ingest import extract_file
from scripts.workspace import dump_json, init_workspace, text_hash


def prepare_revision(project: Path | str, draft_path: Path | str) -> Path:
    root = Path(project).resolve()
    ws = init_workspace(root)
    source = Path(draft_path).resolve()
    if source.suffix.lower() in {".docx", ".pdf"}:
        units, error = extract_file(source)
        if error:
            raise ValueError(error)
        text = "\n\n".join(u.text for u in units)
    else:
        text = source.read_text(encoding="utf-8", errors="replace")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    payload: dict[str, Any] = {
        "source_file": str(source), "source_hash": text_hash(text),
        "instructions": "Bind each paragraph to one result and one paragraph contract; split paragraphs with multiple central claims before drafting.",
        "paragraphs": [{"legacy_id": f"L{idx}", "text": paragraph, "assigned_result_ids": [], "assigned_contract_id": "", "action": "review"} for idx, paragraph in enumerate(paragraphs, 1)]
    }
    output = ws / "revision_intake.json"
    dump_json(output, payload)
    return output
