from __future__ import annotations


def expand_query(query: str, glossary: dict[str, list[str]] | None = None) -> list[str]:
    terms = [query.strip()]
    lower = query.casefold()
    for canonical, synonyms in (glossary or {}).items():
        family = [canonical, *synonyms]
        if any(item.casefold() in lower or lower in item.casefold() for item in family if item):
            terms.extend(family)
    seen: set[str] = set()
    return [x for x in terms if x and not (x.casefold() in seen or seen.add(x.casefold()))]
