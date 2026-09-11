from __future__ import annotations

from pathlib import Path

from .indexer import load_index
from .intent import classify_task
from .retrieval import retrieve_context


def create_server():
    """Create the MCP server lazily so the core library works without MCP installed."""
    try:
        from mcp.server import MCPServer
    except ImportError as error:
        raise RuntimeError("Install the mcp package to run the Context Forge MCP server.") from error

    server = MCPServer("Context Forge", version="0.1.0")

    @server.tool()
    def retrieve_repository_context(index_path: str, query: str, budget: int = 8000, mode: str = "hybrid") -> dict:
        """Return explainable, token-budgeted repository context for a coding task."""
        if mode not in {"bm25", "semantic", "hybrid"}:
            raise ValueError("mode must be bm25, semantic, or hybrid")
        index = load_index(Path(index_path))
        intent = classify_task(query)
        result = retrieve_context(query, index, mode=mode, budget=budget, evidence_types=intent.evidence_types)
        result["intent"] = {"kind": intent.kind, "confidence": intent.confidence, "evidence_types": list(intent.evidence_types)}
        return result

    return server


if __name__ == "__main__":
    create_server().run()
