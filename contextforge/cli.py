from __future__ import annotations

import argparse
import json
from pathlib import Path
from .evaluate import evaluate, evaluate_all
from .indexer import build_index, load_index, save_index
from .retrieval import retrieve_context


def main() -> None:
    parser = argparse.ArgumentParser(description="ContextForge repository retrieval lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="index a repository")
    index_parser.add_argument("root")
    index_parser.add_argument("--output", default=".contextforge/index.json")

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
        index = build_index(args.root)
        save_index(index, args.output)
        print(json.dumps({"files": len(index["files"]), "chunks": len(index["documents"]), "output": str(Path(args.output).resolve())}, indent=2))
    elif args.command == "retrieve":
        print(json.dumps(retrieve_context(args.query, load_index(args.index), mode=args.mode, budget=args.budget), indent=2))
    elif args.command == "evaluate":
        cases = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
        print(json.dumps(evaluate(load_index(args.index), cases, mode=args.mode, budget=args.budget), indent=2))
    else:
        cases = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_all(load_index(args.index), cases, budget=args.budget), indent=2))


if __name__ == "__main__":
    main()
