from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from scripts.workspace import dump_json, init_workspace, iter_project_files, load_json
from .models import load_cards


def _bibtex(text: str, source: str) -> list[dict[str, Any]]:
    entries = []
    for match in re.finditer(r"@\w+\s*\{\s*([^,]+),(.*?)(?=\n@|\Z)", text, flags=re.S | re.I):
        key, body = match.group(1).strip(), match.group(2)
        fields = {m.group(1).lower(): m.group(2).strip().strip("{},\"") for m in re.finditer(r"(\w+)\s*=\s*[\{\"](.*?)[\}\"]\s*,?\s*(?=\w+\s*=|\Z)", body, flags=re.S)}
        entries.append({"key": key, "title": fields.get("title", ""), "doi": fields.get("doi", "").lower(), "year": fields.get("year", ""), "source": source, "format": "bibtex"})
    return entries


def _ris(text: str, source: str) -> list[dict[str, Any]]:
    entries = []
    current: dict[str, list[str]] = {}
    for line in text.splitlines() + ["ER  -"]:
        match = re.match(r"^([A-Z0-9]{2})\s*-\s*(.*)$", line)
        if not match:
            continue
        tag, value = match.groups()
        if tag == "ER":
            if current:
                title = (current.get("TI") or current.get("T1") or [""])[0]
                doi = (current.get("DO") or [""])[0].lower()
                year = (current.get("PY") or current.get("Y1") or [""])[0][:4]
                key = (current.get("ID") or [re.sub(r"\W+", "", title)[:40] or f"RIS{len(entries)+1}"])[0]
                entries.append({"key": key, "title": title, "doi": doi, "year": year, "source": source, "format": "ris"})
            current = {}
        else:
            current.setdefault(tag, []).append(value.strip())
    return entries


def _endnote_xml(text: str, source: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    entries = []
    for idx, record in enumerate(root.iter(), 1):
        if record.tag.rsplit("}", 1)[-1] != "record":
            continue
        values: dict[str, str] = {}
        for node in record.iter():
            tag = node.tag.rsplit("}", 1)[-1].lower()
            if node.text and node.text.strip() and tag in {"title", "year", "electronic-resource-num", "accession-num", "rec-number"}:
                values[tag] = node.text.strip()
        entries.append({
            "key": values.get("rec-number", f"ENDNOTE{idx}"), "title": values.get("title", ""),
            "doi": values.get("electronic-resource-num", "").lower(), "year": values.get("year", ""),
            "source": source, "format": "endnote-xml"
        })
    return entries


def build_citation_registry(project: Path | str) -> dict[str, Any]:
    root = Path(project).resolve()
    ws = init_workspace(root)
    config = load_json(ws / "config.json", {})
    entries: list[dict[str, Any]] = []
    for path, rel, role in iter_project_files(root, config):
        if path.suffix.lower() not in {".bib", ".ris", ".xml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".bib":
            entries.extend(_bibtex(text, rel))
        elif path.suffix.lower() == ".ris":
            entries.extend(_ris(text, rel))
        elif "<record" in text.casefold():
            entries.extend(_endnote_xml(text, rel))
    matches = []
    for ref_id, card in load_cards(ws).items():
        publication = card.get("publication", {})
        doi = str(publication.get("doi", "")).lower().strip()
        title = re.sub(r"\W+", "", str(publication.get("title", "")).casefold())
        candidates = [e for e in entries if doi and e.get("doi") == doi]
        if not candidates and title:
            candidates = [e for e in entries if re.sub(r"\W+", "", e.get("title", "").casefold()) == title]
        matches.append({"reference_id": ref_id, "matched_keys": [e["key"] for e in candidates], "status": "unique" if len(candidates) == 1 else "ambiguous" if candidates else "unmatched"})
    registry = {"entries": entries, "matches": matches}
    dump_json(ws / "citation_registry.json", registry)
    return registry
