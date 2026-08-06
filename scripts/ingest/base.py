from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedUnit:
    locator: str
    text: str
    quality_score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def quality_score(text: str) -> float:
    if not text.strip():
        return 0.0
    length = len(text)
    replacement = text.count("�") / max(1, length)
    control = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\t") / max(1, length)
    alnum = sum(1 for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff") / max(1, length)
    score = 0.35 + min(0.45, alnum) + min(0.20, length / 5000)
    return max(0.0, min(1.0, score - 3 * replacement - 3 * control))


def unit(locator: str, text: str, **metadata: Any) -> ExtractedUnit | None:
    cleaned = clean_text(text)
    if not cleaned:
        return None
    return ExtractedUnit(locator=locator, text=cleaned, quality_score=quality_score(cleaned), metadata=metadata)
