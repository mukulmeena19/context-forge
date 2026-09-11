from __future__ import annotations

import subprocess
from pathlib import Path


def git_history_documents(root: str | Path, limit: int = 100) -> list[dict]:
    """Return commit summaries as retrievable evidence without executing repo code."""
    command = [
        "git", "-C", str(Path(root).resolve()), "log", f"-{max(1, min(limit, 500))}",
        "--date=iso-strict", "--pretty=format:%H%x1f%ad%x1f%an%x1f%s%x1e", "--name-only",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    documents = []
    for raw_record in completed.stdout.split("\x1e"):
        record = raw_record.strip()
        if not record:
            continue
        lines = [line.strip() for line in record.splitlines() if line.strip()]
        if not lines:
            continue
        fields = lines[0].split("\x1f")
        if len(fields) != 4:
            continue
        sha, date, author, subject = fields
        changed = lines[1:40]
        text = "Commit: " + subject + "\nDate: " + date + "\nAuthor: " + author
        if changed:
            text += "\nChanged files:\n" + "\n".join(changed)
        documents.append({
            "id": f"git:commit:{sha}",
            "path": f".git/commits/{sha[:12]}",
            "language": "text",
            "symbol": subject[:160],
            "kind": "commit",
            "start": 1,
            "end": max(1, len(text.splitlines())),
            "text": text,
            "imports": [],
            "metadata": {"sha": sha, "date": date, "author": author, "changed_files": changed},
        })
    return documents
