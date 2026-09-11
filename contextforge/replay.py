from __future__ import annotations

from statistics import mean

from .intent import classify_task
from .retrieval import retrieve_context


def replay(index: dict, cases: list[dict], mode: str = "hybrid", budget: int = 8000, limit: int = 20) -> dict:
    """Replay labelled tasks and compute a deterministic context-coverage proxy.

    A real coding-agent runner can use the returned context package later. The
    proxy is deliberately conservative: it is successful only when every gold
    file appears in the selected package.
    """
    rows = []
    for case in cases:
        intent = classify_task(case["query"])
        result = retrieve_context(case["query"], index, mode=mode, limit=limit, budget=budget, evidence_types=intent.evidence_types)
        retrieved = {item["path"] for item in result["results"]}
        relevant = set(case.get("relevant", []))
        coverage = len(retrieved & relevant) / len(relevant) if relevant else 0.0
        rows.append({
            "query": case["query"],
            "intent": intent.kind,
            "required_files": sorted(relevant),
            "retrieved_files": sorted(retrieved),
            "coverage": round(coverage, 4),
            "context_ready": bool(relevant) and relevant <= retrieved,
            "tokens": result["tokens"],
            "latency_ms": result["latency_ms"],
        })
    return {
        "mode": mode,
        "cases": len(rows),
        "metrics": {
            "context_ready_rate": round(mean(row["context_ready"] for row in rows), 4) if rows else 0.0,
            "mean_coverage": round(mean(row["coverage"] for row in rows), 4) if rows else 0.0,
            "mean_tokens": round(mean(row["tokens"] for row in rows), 2) if rows else 0.0,
            "mean_latency_ms": round(mean(row["latency_ms"] for row in rows), 2) if rows else 0.0,
        },
        "rows": rows,
    }
