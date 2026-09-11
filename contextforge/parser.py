from __future__ import annotations

import ast
import importlib
from pathlib import Path

LANGUAGE_PACKAGES = {
    ".py": ("tree_sitter_python", "language"),
    ".js": ("tree_sitter_javascript", "language"),
    ".jsx": ("tree_sitter_javascript", "language"),
    ".ts": ("tree_sitter_typescript", "language_typescript"),
    ".tsx": ("tree_sitter_typescript", "language_tsx"),
    ".java": ("tree_sitter_java", "language"),
    ".go": ("tree_sitter_go", "language"),
    ".rs": ("tree_sitter_rust", "language"),
}

SYMBOL_NODES = {
    "function_definition", "async_function_definition", "class_definition",
    "function_declaration", "method_definition", "class_declaration",
    "interface_declaration", "struct_item", "function_item", "method_declaration",
}


def _node_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _tree_sitter_chunks(path: Path, text: str) -> list[dict] | None:
    package_config = LANGUAGE_PACKAGES.get(path.suffix.lower())
    if not package_config:
        return None
    try:
        tree_sitter = importlib.import_module("tree_sitter")
        language_package = importlib.import_module(package_config[0])
        language = tree_sitter.Language(getattr(language_package, package_config[1])())
        parser = tree_sitter.Parser(language)
        source = text.encode("utf-8")
        tree = parser.parse(source)
    except (ImportError, AttributeError, TypeError, ValueError):
        return None

    chunks = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in SYMBOL_NODES:
            name_node = node.child_by_field_name("name")
            name = _node_text(name_node, source) if name_node else f"{path.stem}:{node.start_point[0] + 1}"
            chunks.append({
                "symbol": name,
                "kind": node.type,
                "start": node.start_point[0] + 1,
                "end": node.end_point[0] + 1,
                "text": _node_text(node, source),
            })
        stack.extend(reversed(node.children))
    return chunks


def _python_ast_chunks(path: Path, text: str) -> list[dict]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines()
    chunks = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        chunks.append({
            "symbol": getattr(node, "name", path.stem),
            "kind": type(node).__name__,
            "start": start,
            "end": end,
            "text": "\n".join(lines[start - 1:end]),
        })
    return chunks


def generic_chunks(path: Path, text: str, step: int = 80) -> list[dict]:
    lines = text.splitlines()
    return [
        {
            "symbol": f"{path.stem}:lines-{offset + 1}-{min(offset + step, len(lines))}",
            "kind": "text",
            "start": offset + 1,
            "end": min(offset + step, len(lines)),
            "text": "\n".join(lines[offset:offset + step]),
        }
        for offset in range(0, len(lines), step)
    ]


def extract_chunks(path: Path, text: str) -> list[dict]:
    """Prefer Tree-sitter, then Python AST, then line chunks."""
    parsed = _tree_sitter_chunks(path, text)
    if parsed:
        return parsed
    if path.suffix.lower() == ".py":
        parsed = _python_ast_chunks(path, text)
        if parsed:
            return parsed
    return generic_chunks(path, text)
