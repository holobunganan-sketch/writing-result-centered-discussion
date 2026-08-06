from __future__ import annotations

import re
from dataclasses import dataclass

TRACE_RE = re.compile(r"<!--\s*D:(D\d+)\s+R:([R\d, -]+)\s*-->")
CLAIM_RE = re.compile(r"\[(REF-\d{3,}-C\d+)\]")
SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s*")


@dataclass
class Paragraph:
    number: int
    raw: str
    contract_id: str
    result_ids: list[str]
    claims: list[str]
    body: str
    sentences: list[str]


def blocks(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip() and not x.lstrip().startswith("#")]


def parse_paragraphs(text: str) -> tuple[list[Paragraph], list[str]]:
    paragraphs: list[Paragraph] = []
    errors: list[str] = []
    for number, raw in enumerate(blocks(text), 1):
        match = TRACE_RE.search(raw)
        if not match:
            errors.append(f"Paragraph {number} has no trace header <!-- D:D1 R:R1 -->")
            continue
        contract_id = match.group(1)
        result_ids = [x.strip() for x in match.group(2).split(",") if x.strip()]
        body = TRACE_RE.sub("", raw).strip()
        sentences = [x.strip() for x in SENTENCE_RE.split(body) if x.strip()]
        paragraphs.append(Paragraph(number, raw, contract_id, result_ids, CLAIM_RE.findall(body), body, sentences))
    return paragraphs, errors
