from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import ExtractedUnit, unit


def _pypdf(path: Path) -> list[ExtractedUnit]:
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(str(path))
        units: list[ExtractedUnit] = []
        for idx, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if found := unit(f"page {idx}", text, format="pdf"):
                units.append(found)
        return units
    except Exception:
        return []


def _pdftotext(path: Path) -> list[ExtractedUnit]:
    executable = shutil.which("pdftotext")
    if not executable:
        return []
    with tempfile.TemporaryDirectory(prefix="wrcd-pdf-") as tmp:
        output = Path(tmp) / "out.txt"
        proc = subprocess.run([executable, "-layout", str(path), str(output)], capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not output.exists():
            return []
        units: list[ExtractedUnit] = []
        for idx, page in enumerate(output.read_text(encoding="utf-8", errors="replace").split("\f"), 1):
            if found := unit(f"page {idx}", page, format="pdf"):
                units.append(found)
        return units


def _ocr(path: Path, language: str) -> list[ExtractedUnit]:
    try:
        from pdf2image import convert_from_path  # type: ignore
        import pytesseract  # type: ignore
        pages = convert_from_path(str(path), dpi=220)
        units: list[ExtractedUnit] = []
        for idx, image in enumerate(pages, 1):
            text = pytesseract.image_to_string(image, lang=language)
            if found := unit(f"page {idx} OCR", text, format="pdf-ocr"):
                units.append(found)
        return units
    except Exception:
        return []


def extract_pdf(path: Path, ocr_enabled: bool = False, ocr_language: str = "eng") -> list[ExtractedUnit]:
    units = _pypdf(path) or _pdftotext(path)
    if units and sum(len(x.text) for x in units) >= 80:
        return units
    return (_ocr(path, ocr_language) if ocr_enabled else []) or units
