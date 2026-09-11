from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def github_documents(repository: str, token: str | None = None, limit: int = 50) -> list[dict]:
    """Fetch public issue/PR metadata as evidence; never downloads source code."""
    owner_repo = repository.strip().strip("/").removesuffix(".git")
    url = f"https://api.github.com/repos/{owner_repo}/issues?state=all&per_page={max(1, min(limit, 100))}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "context-forge"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, headers=headers), timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return []
    documents = []
    for item in payload:
        number = item.get("number")
        title = str(item.get("title", "")).strip()
        body = str(item.get("body", "") or "").strip()
        if not number or not title:
            continue
        kind = "pull_request" if item.get("pull_request") else "issue"
        content = f"{kind.replace('_', ' ').title()}: {title}\n\n{body}".strip()
        documents.append({
            "id": f"github:{owner_repo}:{number}",
            "path": f".github/{kind}s/{number}",
            "language": "text",
            "symbol": title[:160],
            "kind": kind,
            "start": 1,
            "end": max(1, len(content.splitlines())),
            "text": content,
            "imports": [],
            "metadata": {"repository": owner_repo, "number": number, "url": item.get("html_url"), "state": item.get("state"), "labels": [label.get("name") for label in item.get("labels", [])]},
        })
    return documents
