# Context Forge

Context Forge is a local-first retrieval and evaluation system for coding agents.
It turns a bug report or feature request into a small, ranked, evidence-backed
context package instead of sending an entire repository to an LLM.

## What is included

- Repository indexer that creates symbol-sized chunks from source files.
- Import and test-to-source relationship graph.
- Three retrieval modes: lexical BM25, hashed semantic similarity, and hybrid
  retrieval with graph-aware reranking.
- Token-budgeted context packages with file paths, line ranges, and scores.
- Evaluation lab reporting Recall@K, MRR, nDCG, context precision, token count,
  and retrieval latency.
- FastAPI endpoints for indexing, retrieval, and benchmark comparison.
- Zero external services for the first run; the index is a portable JSON file.

## Quick start

From this directory:

```text
python -m contextforge.cli index ..\backend --history --output .contextforge\index.json
python -m contextforge.cli retrieve .contextforge\index.json "Fix duplicate notifications after profile update" --mode hybrid --budget 1800
python -m contextforge.cli compare .contextforge\index.json benchmarks\demo.json
```

On macOS/Linux, replace the backslashes in the example path with forward slashes.

Run the API after installing `requirements.txt`:

```text
uvicorn contextforge.api:app --reload --port 8001
```

## Benchmark format

```json
[
  {
    "query": "Fix duplicate notifications after profile update",
    "relevant": ["app/notifications.py", "tests/test_notifications.py"]
  }
]
```

The `relevant` paths are the ground truth used only by the evaluation lab. They
are never shown to the retriever during ranking.

## Research direction

The first experiment compares lexical, semantic, and hybrid retrieval under the
same corpus and token budget. Add real GitHub issues or SWE-bench examples to
`benchmarks/`, then compare retrieval quality with downstream agent success.

The repository is named `context-forge`. The product focuses on explainable
repository context retrieval and evaluation rather than acting as a general
purpose coding assistant.

## Build status

### Milestone 1 — Retrieval foundation

- [x] Symbol-aware repository index
- [x] Import and test relationship edges
- [x] BM25, semantic, and hybrid modes
- [x] Graph-aware reranking with result explanations
- [x] Token-budgeted Markdown context package
- [x] Task-aware evidence selection
- [x] CLI and FastAPI interfaces
- [ ] Tree-sitter multi-language extraction
- [x] Git history ingestion
- [ ] GitHub issue/PR ingestion
- [ ] Persistent PostgreSQL/pgvector store
- [ ] Agent replay evaluation
