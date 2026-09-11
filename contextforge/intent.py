from __future__ import annotations

from dataclasses import dataclass

from .retrieval import tokenize


@dataclass(frozen=True)
class TaskIntent:
    kind: str
    confidence: float
    evidence_types: tuple[str, ...]


RULES = {
    "bug": ({"fix", "bug", "broken", "fails", "failure", "error", "regression", "incorrect", "duplicate"}, ("source", "tests", "history")),
    "feature": ({"add", "build", "implement", "support", "feature", "create", "enable"}, ("source", "tests", "docs")),
    "refactor": ({"refactor", "cleanup", "simplify", "migrate", "rename", "restructure"}, ("source", "tests", "history")),
    "performance": ({"slow", "latency", "performance", "optimize", "memory", "timeout", "throughput"}, ("source", "tests", "history")),
    "security": ({"security", "vulnerability", "injection", "permission", "secret", "auth", "authentication", "authorization"}, ("source", "tests", "history", "docs")),
}


def classify_task(query: str) -> TaskIntent:
    tokens = set(tokenize(query))
    scores = {kind: len(tokens & keywords) for kind, (keywords, _) in RULES.items()}
    kind, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return TaskIntent("investigation", 0.35, ("source", "docs", "history"))
    confidence = min(0.98, 0.55 + score * 0.12)
    return TaskIntent(kind, round(confidence, 2), RULES[kind][1])
