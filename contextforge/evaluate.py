from __future__ import annotations

import math
from statistics import mean
from .retrieval import retrieve_context


def evaluate(index: dict, cases: list[dict], mode: str = "hybrid", k: int = 10, budget: int = 8000) -> dict:
    rows = []
    for case in cases:
        result = retrieve_context(case["query"], index, mode=mode, limit=k, budget=budget)
        retrieved = [item["path"] for item in result["results"]]
        relevant = set(case.get("relevant", []))
        hits = [path for path in retrieved if path in relevant]
        recall = len(set(hits)) / len(relevant) if relevant else 0.0
        precision = len(hits) / len(retrieved) if retrieved else 0.0
        reciprocal_rank = next((1 / (position + 1) for position, path in enumerate(retrieved) if path in relevant), 0.0)
        dcg = sum((1 / math.log2(position + 2)) for position, path in enumerate(retrieved) if path in relevant)
        ideal = sum((1 / math.log2(position + 2)) for position in range(min(len(relevant), k)))
        rows.append({"query": case["query"], "recall": recall, "precision": precision, "mrr": reciprocal_rank, "ndcg": dcg / ideal if ideal else 0.0, "tokens": result["tokens"], "latency_ms": result["latency_ms"]})
    return {"mode": mode, "cases": len(rows), "metrics": {key: round(mean(row[key] for row in rows), 4) for key in ("recall", "precision", "mrr", "ndcg", "tokens", "latency_ms")} if rows else {}, "rows": rows}


def evaluate_all(index: dict, cases: list[dict], k: int = 10, budget: int = 8000) -> dict:
    reports = [evaluate(index, cases, mode=mode, k=k, budget=budget) for mode in ("bm25", "semantic", "hybrid")]
    return {"reports": reports, "comparison": [{"mode": report["mode"], **report["metrics"]} for report in reports]}
