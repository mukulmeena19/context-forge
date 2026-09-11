from __future__ import annotations

import json
import re
from pathlib import Path

from .history import git_history_documents
from .github import github_documents
from .parser import extract_chunks

IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".next", ".pytest_cache", ".contextforge"}
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h"}
TEXT_EXTENSIONS = {".md", ".mdx", ".rst", ".txt", ".yaml", ".yml", ".json"}
IMPORT_RE = re.compile(r"(?:from\s+([\w.]+)\s+import|import\s+([\w.]+)|require\(['\"]([^'\"]+))")


def _readable_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS | TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if len(text) <= 1_000_000:
            yield path, text


def _imports(text: str) -> list[str]:
    found = []
    for match in IMPORT_RE.finditer(text):
        value = next((item for item in match.groups() if item), "")
        found.append(value.split(".")[0].replace("/", "\\"))
    return sorted(set(found))


def build_index(root: str | Path, include_history: bool = False, history_limit: int = 100, github_repo: str | None = None, github_token: str | None = None, github_limit: int = 50) -> dict:
    root_path = Path(root).resolve()
    documents = []
    files = []
    file_texts = {}
    for path, text in _readable_files(root_path):
        relative = path.relative_to(root_path).as_posix()
        files.append(relative)
        file_texts[relative] = text
        chunks = extract_chunks(path, text)
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
    history = git_history_documents(root_path, limit=history_limit) if include_history else []
    documents.extend(history)
    external = github_documents(github_repo, token=github_token, limit=github_limit) if github_repo else []
    documents.extend(external)
    return {"version": 1, "root": str(root_path), "files": sorted(files), "documents": documents, "edges": edges, "history_documents": len(history), "github_documents": len(external)}


def save_index(index: dict, output: str | Path) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def load_index(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
