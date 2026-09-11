from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .evaluate import evaluate, evaluate_all
from .indexer import build_index, load_index, save_index
from .intent import classify_task
from .retrieval import retrieve_context


class IndexRequest(BaseModel):
    root: str
    output: str = ".contextforge/index.json"
    include_history: bool = False
    history_limit: int = Field(default=100, ge=1, le=500)
    github_repo: str | None = None
    github_token: str | None = None
    github_limit: int = Field(default=50, ge=1, le=100)


class RetrieveRequest(BaseModel):
    index: str = ".contextforge/index.json"
    query: str = Field(min_length=3)
    mode: Literal["bm25", "semantic", "hybrid"] = "hybrid"
    limit: int = Field(default=20, ge=1, le=100)
    budget: int = Field(default=8000, ge=100, le=100000)


class EvaluateRequest(BaseModel):
    index: str = ".contextforge/index.json"
    benchmark: str
    mode: Literal["bm25", "semantic", "hybrid", "all"] = "all"
    budget: int = Field(default=8000, ge=100, le=100000)


app = FastAPI(title="Context Forge", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "contextforge-retrieval-lab"}


@app.post("/index")
def index_repository(request: IndexRequest) -> dict:
    root = Path(request.root)
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="Repository directory does not exist.")
    index = build_index(root, include_history=request.include_history, history_limit=request.history_limit, github_repo=request.github_repo, github_token=request.github_token, github_limit=request.github_limit)
    save_index(index, request.output)
    return {"files": len(index["files"]), "chunks": len(index["documents"]), "edges": len(index["edges"]), "history_documents": index["history_documents"], "github_documents": index["github_documents"], "output": str(Path(request.output).resolve())}


@app.post("/retrieve")
def retrieve(request: RetrieveRequest) -> dict:
    try:
        index = load_index(request.index)
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=404, detail="Index file could not be loaded.") from error
    intent = classify_task(request.query)
    result = retrieve_context(request.query, index, mode=request.mode, limit=request.limit, budget=request.budget, evidence_types=intent.evidence_types)
    result["intent"] = {"kind": intent.kind, "confidence": intent.confidence, "evidence_types": list(intent.evidence_types)}
    return result


@app.post("/evaluate")
def evaluate_benchmark(request: EvaluateRequest) -> dict:
    try:
        index = load_index(request.index)
        cases = json.loads(Path(request.benchmark).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=404, detail="Index or benchmark file could not be loaded.") from error
    if request.mode == "all":
        return evaluate_all(index, cases, budget=request.budget)
    return evaluate(index, cases, mode=request.mode, budget=request.budget)
