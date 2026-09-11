from __future__ import annotations

import argparse
import json
from pathlib import Path
from .evaluate import evaluate, evaluate_all
from .indexer import build_index, load_index, save_index
from .intent import classify_task
from .retrieval import retrieve_context


def main() -> None:
    parser = argparse.ArgumentParser(description="Context Forge repository retrieval lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="index a repository")
    index_parser.add_argument("root")
    index_parser.add_argument("--output", default=".contextforge/index.json")
    index_parser.add_argument("--history", action="store_true", help="include recent Git commit summaries")
    index_parser.add_argument("--history-limit", type=int, default=100)

    retrieve_parser = subparsers.add_parser("retrieve", help="retrieve a context package")
    retrieve_parser.add_argument("index")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument("--mode", choices=("bm25", "semantic", "hybrid"), default="hybrid")
    retrieve_parser.add_argument("--budget", type=int, default=8000)

    eval_parser = subparsers.add_parser("evaluate", help="run a retrieval benchmark")
    eval_parser.add_argument("index")
    eval_parser.add_argument("benchmark")
    eval_parser.add_argument("--mode", choices=("bm25", "semantic", "hybrid"), default="hybrid")
    eval_parser.add_argument("--budget", type=int, default=8000)

    compare_parser = subparsers.add_parser("compare", help="compare all retrieval modes")
    compare_parser.add_argument("index")
    compare_parser.add_argument("benchmark")
    compare_parser.add_argument("--budget", type=int, default=8000)

    args = parser.parse_args()
    if args.command == "index":
        index = build_index(args.root, include_history=args.history, history_limit=args.history_limit)
        save_index(index, args.output)
        print(json.dumps({"files": len(index["files"]), "chunks": len(index["documents"]), "edges": len(index["edges"]), "history_documents": index["history_documents"], "output": str(Path(args.output).resolve())}, indent=2))
    elif args.command == "retrieve":
        intent = classify_task(args.query)
        result = retrieve_context(args.query, load_index(args.index), mode=args.mode, budget=args.budget, evidence_types=intent.evidence_types)
        result["intent"] = {"kind": intent.kind, "confidence": intent.confidence, "evidence_types": list(intent.evidence_types)}
        print(json.dumps(result, indent=2))
    elif args.command == "evaluate":
        cases = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
        print(json.dumps(evaluate(load_index(args.index), cases, mode=args.mode, budget=args.budget), indent=2))
    else:
        cases = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_all(load_index(args.index), cases, budget=args.budget), indent=2))


if __name__ == "__main__":
    main()
