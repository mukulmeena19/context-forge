import json
from pathlib import Path

from contextforge.evaluate import evaluate
from contextforge.indexer import build_index
from contextforge.retrieval import retrieve_context


ROOT = Path(__file__).resolve().parents[1]


def test_index_contains_python_symbols():
    index = build_index(ROOT / "contextforge")
    paths = {doc["path"] for doc in index["documents"]}
    assert "indexer.py" in paths
    assert any(doc["symbol"] == "build_index" for doc in index["documents"])


def test_hybrid_retrieval_returns_relevant_code():
    index = build_index(ROOT / "contextforge")
    result = retrieve_context("calculate Recall MRR nDCG benchmark", index, budget=500)
    assert result["results"]
    assert result["results"][0]["path"] == "evaluate.py"
    assert result["tokens"] <= 500


def test_evaluation_reports_metrics():
    index = build_index(ROOT / "contextforge")
    cases = json.loads((ROOT / "benchmarks" / "demo.json").read_text(encoding="utf-8"))
    report = evaluate(index, cases)
    assert report["cases"] == 2
    assert set(("recall", "precision", "mrr", "ndcg", "tokens", "latency_ms")) <= set(report["metrics"])
