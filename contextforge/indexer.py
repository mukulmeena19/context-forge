from __future__ import annotations

import ast
import json
import re
from pathlib import Path

IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".next"}
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h"}
TEXT_EXTENSIONS = {".md", ".mdx", ".rst", ".txt", ".yaml", ".yml", ".json"}
IMPORT_RE = re.compile(r"(?:from\s+([\w.]+)\s+import|import\s+([\w.]+)|require\(['\"]([^'\"]+))")


def _readable_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS | TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if len(text) <= 1_000_000:
            yield path, text


def _python_chunks(path: Path, text: str) -> list[dict]:
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
        name = getattr(node, "name", path.stem)
        chunks.append({"symbol": name, "kind": type(node).__name__, "start": start, "end": end, "text": "\n".join(lines[start - 1:end])})
    return chunks


def _generic_chunks(path: Path, text: str) -> list[dict]:
    lines = text.splitlines()
    if not lines:
        return []
    chunks = []
    step = 80
    for offset in range(0, len(lines), step):
        end = min(offset + step, len(lines))
        chunks.append({"symbol": f"{path.stem}:lines-{offset + 1}-{end}", "kind": "text", "start": offset + 1, "end": end, "text": "\n".join(lines[offset:end])})
    return chunks


def _imports(text: str) -> list[str]:
    found = []
    for match in IMPORT_RE.finditer(text):
        value = next((item for item in match.groups() if item), "")
        found.append(value.split(".")[0].replace("/", "\\"))
    return sorted(set(found))


def build_index(root: str | Path) -> dict:
    root_path = Path(root).resolve()
    documents = []
    files = []
    file_texts = {}
    for path, text in _readable_files(root_path):
        relative = path.relative_to(root_path).as_posix()
        files.append(relative)
        file_texts[relative] = text
        chunks = _python_chunks(path, text) if path.suffix == ".py" else []
        if not chunks:
            chunks = _generic_chunks(path, text)
        for chunk in chunks:
            documents.append({
                "id": f"{relative}:{chunk['start']}",
                "path": relative,
                "language": path.suffix.lower().lstrip("."),
                "symbol": chunk["symbol"],
                "kind": chunk["kind"],
                "start": chunk["start"],
                "end": chunk["end"],
                "text": chunk["text"],
                "imports": _imports(chunk["text"]),
            })
    file_lookup = {Path(path).stem.lower(): path for path in files}
    edges = []
    for relative in files:
        source_stem = Path(relative).stem.lower()
        for imported in _imports(file_texts[relative]):
            target = file_lookup.get(imported.lower())
            if target and target != relative:
                edges.append({"source": relative, "target": target, "kind": "imports"})
        if source_stem.startswith("test_") or source_stem.endswith("_test"):
            candidate = source_stem.removeprefix("test_").removesuffix("_test")
            target = file_lookup.get(candidate)
            if target and target != relative:
                edges.append({"source": relative, "target": target, "kind": "tests"})
    return {"version": 1, "root": str(root_path), "files": sorted(files), "documents": documents, "edges": edges}


def save_index(index: dict, output: str | Path) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def load_index(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
