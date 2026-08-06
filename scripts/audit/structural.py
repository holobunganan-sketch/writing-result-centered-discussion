from __future__ import annotations

import re
from typing import Any

from scripts.indexing.bm25 import tokenize
from .parsing import Paragraph


def sentence_function(sentence: str) -> str:
    lower = sentence.casefold()
    if re.search(r"\b(our study|we found|this study|本研究|我们的研究)\b", lower):
        return "study-result"
    if re.search(r"\b(compared|consistent|similar|contrast|whereas|prior|previous|既往|一致|差异|相反|相比)\b", lower):
        return "comparison"
    if re.search(r"\b(because|may reflect|may be explained|mechanism|由于|可能源于|机制|解释)\b", lower):
        return "explanation"
    if re.search(r"\b(limit|cannot|uncertain|caution|局限|不能|谨慎|尚不)\b", lower):
        return "boundary"
    if re.search(r"\b(therefore|thus|suggest|implication|因此|提示|意义|支持)\b", lower):
        return "interpretation"
    return "supporting-detail"


def lexical_focus(paragraph: Paragraph, central_claim: str, result_findings: list[str]) -> float:
    target = set(tokenize(" ".join([central_claim, *result_findings])))
    body = set(tokenize(paragraph.body))
    return len(target & body) / max(1, len(target))


def return_to_study(paragraph: Paragraph, result_findings: list[str]) -> bool:
    if not paragraph.sentences:
        return False
    last = paragraph.sentences[-1].casefold()
    explicit = ["our study", "our finding", "this result", "this finding", "r1", "本研究", "该结果", "这一结果", "本研究结果"]
    if any(marker in last for marker in explicit):
        return True
    result_tokens = set(tokenize(" ".join(result_findings)))
    last_tokens = set(tokenize(last))
    return bool(result_tokens) and len(result_tokens & last_tokens) / len(result_tokens) >= 0.18


def reverse_outline(paragraphs: list[Paragraph], contracts: dict[str, dict[str, Any]], results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for paragraph in paragraphs:
        contract = contracts.get(paragraph.contract_id, {})
        findings = [results[x].get("finding", "") for x in paragraph.result_ids if x in results]
        rows.append({
            "paragraph": paragraph.number,
            "contract_id": paragraph.contract_id,
            "result_ids": paragraph.result_ids,
            "contract_central_claim": contract.get("central_claim", ""),
            "sentence_functions": [{"sentence": i, "function": sentence_function(s), "text": s} for i, s in enumerate(paragraph.sentences, 1)],
            "lexical_focus": round(lexical_focus(paragraph, contract.get("central_claim", ""), findings), 4),
            "returns_to_study": return_to_study(paragraph, findings),
        })
    return {"paragraphs": rows}
