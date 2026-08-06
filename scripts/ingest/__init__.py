from __future__ import annotations

from pathlib import Path

from .base import ExtractedUnit
from .docx import extract_docx
from .pdf import extract_pdf
from .pptx import extract_pptx
from .text import extract_plain
from .xlsx import extract_xlsx

PLAIN = {".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml", ".html", ".htm", ".tex", ".bib", ".ris"}


def extract_file(path: Path, config: dict | None = None) -> tuple[list[ExtractedUnit], str | None]:
    try:
        suffix = path.suffix.lower()
        if suffix in PLAIN:
            units = extract_plain(path)
        elif suffix == ".docx":
            units = extract_docx(path)
        elif suffix == ".xlsx":
            units = extract_xlsx(path)
        elif suffix == ".pptx":
            units = extract_pptx(path)
        elif suffix == ".pdf":
            ocr = (config or {}).get("ocr", {})
            units = extract_pdf(path, bool(ocr.get("enabled")), str(ocr.get("language", "eng")))
        else:
            return [], "unsupported file type"
        if not units:
            return [], "no extractable text"
        return units, None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"

__all__ = ["ExtractedUnit", "extract_file"]
