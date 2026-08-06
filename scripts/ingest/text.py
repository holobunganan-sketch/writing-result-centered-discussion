from pathlib import Path
from .base import ExtractedUnit, unit


def extract_plain(path: Path) -> list[ExtractedUnit]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found = unit("document", text, format="plain")
    return [found] if found else []
