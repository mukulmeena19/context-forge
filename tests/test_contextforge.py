import json
from pathlib import Path

from contextforge.evaluate import evaluate
from contextforge.indexer import build_index
from contextforge.intent import classify_task
from contextforge.parser import extract_chunks
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


def test_task_intent_selects_test_and_history_evidence():
    intent = classify_task("Fix the authentication regression and add a regression test")
    assert intent.kind == "bug"
    assert "tests" in intent.evidence_types
    assert "history" in intent.evidence_types


def test_parser_returns_symbol_chunks_with_line_ranges():
    chunks = extract_chunks(Path("service.py"), "def reset_password(user_id):\n    return user_id\n")
    assert chunks[0]["symbol"] == "reset_password"
    assert chunks[0]["start"] == 1
    assert chunks[0]["end"] == 2


def test_index_metadata_tracks_external_evidence_counts():
    index = build_index(ROOT / "contextforge", include_history=False)
    assert index["history_documents"] == 0
    assert index["github_documents"] == 0
