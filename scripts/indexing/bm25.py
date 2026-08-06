from __future__ import annotations

import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    lower = text.casefold()
    latin = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", lower)
    han_runs = re.findall(r"[\u4e00-\u9fff]+", lower)
    han: list[str] = []
    for run in han_runs:
        han.extend(run)
        han.extend(run[i:i+2] for i in range(len(run)-1))
    return latin + han


def scores(documents: list[str], query: str) -> list[float]:
    docs = [tokenize(x) for x in documents]
    q = tokenize(query)
    if not docs or not q:
        return [0.0] * len(docs)
    avgdl = sum(len(d) for d in docs) / max(1, len(docs))
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    n = len(docs)
    result: list[float] = []
    for doc in docs:
        tf = Counter(doc)
        value = 0.0
        for term in q:
            if not tf[term]:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + 1.5 * (1 - 0.75 + 0.75 * len(doc) / max(avgdl, 1))
            value += idf * tf[term] * 2.5 / denom
        result.append(value)
    maximum = max(result, default=0.0)
    return [x / maximum if maximum else 0.0 for x in result]
