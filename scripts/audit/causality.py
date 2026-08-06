from __future__ import annotations

import re

STRONG_EN_CAUSAL = [r"\bcaus(?:e|es|ed|ing)\b", r"\bled to\b", r"\bleads to\b", r"\bresulted in\b", r"\bproduced\b", r"\bdetermined\b", r"\bprevented\b"]
DIRECTIONAL_EN = re.compile(r"\b(intervention|treatment|therapy|drug|vaccine|counselling|counseling|program|programme|exposure)\b.{0,45}\b(improved|increased|reduced|lowered|raised)\b", re.I)
ZH_CAUSAL = ["证明", "证实", "导致", "造成", "引起", "使得", "决定", "提高了", "降低了", "改善了", "预防了"]


def causal_overclaims(text: str, ceilings: list[str]) -> list[str]:
    if ceilings and all(x == "causal" for x in ceilings):
        return []
    lower = text.casefold()
    findings: list[str] = []
    for pattern in STRONG_EN_CAUSAL:
        for match in re.finditer(pattern, lower):
            findings.append(f"causal language exceeds {sorted(set(ceilings))} ceiling: '{match.group(0)}'")
    for match in DIRECTIONAL_EN.finditer(text):
        findings.append(f"causal directional wording exceeds {sorted(set(ceilings))} ceiling: '{match.group(0)}'")
    for term in ZH_CAUSAL:
        if term in text:
            findings.append(f"因果措辞超过 {sorted(set(ceilings))} 证据上限：'{term}'")
    return sorted(set(findings))
