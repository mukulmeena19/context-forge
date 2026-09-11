from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import blake2b
import math
import re
import time

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_+#.-]{1,}")
STOP_WORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "with"}
DIMENSIONS = 1024


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOP_WORDS]


def _vector(text: str) -> Counter[int]:
    vector = Counter()
    for token in tokenize(text):
        index = int.from_bytes(blake2b(token.encode(), digest_size=4).digest(), "big") % DIMENSIONS
        vector[index] += 1
    return vector


def _cosine(left: Counter[int], right: Counter[int]) -> float:
    numerator = sum(value * right.get(key, 0) for key, value in left.items())
    denominator = math.sqrt(sum(v * v for v in left.values()) * sum(v * v for v in right.values()))
    return numerator / denominator if denominator else 0.0


def _bm25(query: list[str], documents: list[dict]) -> list[float]:
    tokenized = [tokenize(doc["path"] + " " + doc["symbol"] + " " + doc["text"]) for doc in documents]
    df = Counter(token for terms in tokenized for token in set(terms))
    average_length = sum(map(len, tokenized)) / max(len(tokenized), 1)
    scores = []
    for terms in tokenized:
        counts = Counter(terms)
        score = 0.0
        for token in query:
            if not counts[token]:
                continue
            idf = math.log(1 + (len(documents) - df[token] + 0.5) / (df[token] + 0.5))
            length_norm = 1 - 0.75 + 0.75 * len(terms) / max(average_length, 1)
            score += idf * (counts[token] * 2.2 / (counts[token] + length_norm))
        scores.append(score)
    maximum = max(scores, default=0.0)
    return [score / maximum if maximum else 0.0 for score in scores]


def _graph_boost(document: dict, documents: list[dict], seed_paths: set[str]) -> float:
    if document["path"] in seed_paths:
        return 1.0
    stem = document["path"].rsplit("/", 1)[-1].split(".")[0].lower()
    related = 0
    for seed in seed_paths:
        seed_stem = seed.rsplit("/", 1)[-1].split(".")[0].lower()
        if stem in seed_stem or seed_stem in stem:
            related += 1
    import_names = {item.lower() for item in document.get("imports", [])}
    if any(part.lower() in import_names for part in stem.split("_")):
        related += 1
    return min(0.18, related * 0.06)


def _graph_neighbors(index: dict, seed_paths: set[str]) -> set[str]:
    neighbors = set()
    for edge in index.get("edges", []):
        if edge["source"] in seed_paths:
            neighbors.add(edge["target"])
        if edge["target"] in seed_paths:
            neighbors.add(edge["source"])
    return neighbors


def _reason(document: dict, lexical: float, semantic: float, graph: float, query_tokens: set[str]) -> list[str]:
    reasons = []
    if lexical >= 0.35:
        reasons.append("keyword match")
    if semantic >= 0.35:
        reasons.append("semantic match")
    if graph:
        reasons.append("repository relationship")
    if "test" in query_tokens and (document["path"].startswith("test") or "/test" in document["path"]):
        reasons.append("test evidence")
    return reasons or ["weak supporting match"]


def retrieve_context(query: str, index: dict, mode: str = "hybrid", limit: int = 20, budget: int = 8000) -> dict:
    started = time.perf_counter()
    documents = index.get("documents", [])
    query_tokens = tokenize(query)
    lexical = _bm25(query_tokens, documents)
    semantic_query = _vector(query)
    semantic = [_cosine(semantic_query, _vector(doc["path"] + " " + doc["symbol"] + " " + doc["text"])) for doc in documents]
    maximum = max(semantic, default=0.0)
    semantic = [score / maximum if maximum else 0.0 for score in semantic]
    if mode == "bm25":
        raw_scores = lexical
    elif mode == "semantic":
        raw_scores = semantic
    else:
        raw_scores = [0.55 * left + 0.35 * right for left, right in zip(lexical, semantic)]
    query_token_set = set(query_tokens)
    seed_paths = {documents[i]["path"] for i, score in enumerate(raw_scores) if score >= 0.65 * max(raw_scores, default=1.0)}
    graph_neighbors = _graph_neighbors(index, seed_paths)
    ranked = []
    for i, document in enumerate(documents):
        graph_score = _graph_boost(document, documents, seed_paths) if mode == "hybrid" else 0.0
        if document["path"] in graph_neighbors:
            graph_score = max(graph_score, 0.12)
        score = raw_scores[i] + (0.10 * graph_score if mode == "hybrid" else 0.0)
        if score:
            ranked.append({**document, "score": round(score, 5), "lexical_score": round(lexical[i], 5), "semantic_score": round(semantic[i], 5), "graph_score": round(graph_score, 5), "reasons": _reason(document, lexical[i], semantic[i], graph_score, query_token_set)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    selected = []
    token_count = 0
    for item in ranked[:limit]:
        item_tokens = len(tokenize(item["text"]))
        if selected and token_count + item_tokens > budget:
            continue
        item["token_count"] = item_tokens
        selected.append(item)
        token_count += item_tokens
    context = "\n\n".join(
        f"## {item['path']}:{item['start']}-{item['end']} ({item['symbol']})\n```{item['language']}\n{item['text']}\n```"
        for item in selected
    )
    return {"query": query, "mode": mode, "results": selected, "context": context, "tokens": token_count, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
