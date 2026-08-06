from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
PMID_RE = re.compile(r"\bPMID\s*[: ]\s*(\d{6,9})\b", re.I)


def identifiers(text: str) -> dict[str, str]:
    doi = DOI_RE.search(text)
    pmid = PMID_RE.search(text)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    title = lines[0][:300] if lines else ""
    lower = text.casefold()
    status = "preprint" if any(marker in lower for marker in ("preprint", "medrxiv", "biorxiv")) else "published"
    return {
        "doi": doi.group(0).rstrip(".,;").lower() if doi else "",
        "pmid": pmid.group(1) if pmid else "",
        "title": title,
        "publication_status": status,
    }


def group_duplicates(records: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[str]] = defaultdict(list)
    metadata: dict[str, dict[str, str]] = {}
    status_by_path: dict[str, str] = {}
    for record in records:
        ids = record.get("identifiers", {})
        key = f"hash:{record['sha256']}"
        if ids.get("doi"):
            key = f"doi:{ids['doi']}"
        elif ids.get("pmid"):
            key = f"pmid:{ids['pmid']}"
        buckets[key].append(record["path"])
        metadata[key] = ids
        status_by_path[record["path"]] = str(ids.get("publication_status", "published"))
    groups = []
    canonical_by_path: dict[str, str] = {}
    for key, members in sorted(buckets.items()):
        if len(members) < 2:
            canonical_by_path[members[0]] = members[0]
            continue
        canonical = sorted(members, key=lambda x: (status_by_path.get(x) == "preprint", "preprint" in x.casefold(), len(x), x))[0]
        for member in members:
            canonical_by_path[member] = canonical
        groups.append({"key": key, "canonical": canonical, "members": sorted(members), "identifiers": metadata[key]})
    return {"groups": groups, "canonical_by_path": canonical_by_path}
