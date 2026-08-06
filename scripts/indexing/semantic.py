from __future__ import annotations

import math
import re
from collections import Counter


def _normalized_text(text: str) -> str:
    return " ".join(re.findall(r"[\w\u3400-\u9fff]+", text.casefold(), flags=re.UNICODE))


def _features(text: str) -> Counter[str]:
    """Build dependency-free multilingual word and character n-gram features."""
    normalized = _normalized_text(text)
    features: Counter[str] = Counter()
    for token in normalized.split():
        features[f"w:{token}"] += 2
    compact = normalized.replace(" ", "")
    for size in (2, 3, 4):
        if len(compact) < size:
            continue
        for index in range(len(compact) - size + 1):
            features[f"c{size}:{compact[index:index + size]}"] += 1
    return features


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return float(dot / (left_norm * right_norm))


def fallback_scores(documents: list[str], query: str) -> list[float]:
    query_features = _features(query)
    return [_cosine(query_features, _features(document)) for document in documents]


def scores(documents: list[str], query: str, backend: str = "tfidf") -> list[float]:
    if not documents:
        return []
    if backend == "sentence-transformers":
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
            model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", local_files_only=True)
            matrix = model.encode([query, *documents])
            return cosine_similarity(matrix[:1], matrix[1:])[0].tolist()
        except Exception:
            backend = "tfidf"
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        matrix = vectorizer.fit_transform([query, *documents])
        return cosine_similarity(matrix[0:1], matrix[1:])[0].tolist()
    except Exception:
        return fallback_scores(documents, query)
