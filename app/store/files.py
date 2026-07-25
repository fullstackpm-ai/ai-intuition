from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frontmatter


def ensure_data_dirs(root: Path) -> None:
    for relative in [
        "data/raw/podcasts",
        "data/raw/lab-posts",
        "data/raw/product-launches",
        "data/raw/strategy",
        "data/raw/manual",
        "data/normalized",
        "data/extracted",
        "data/extraction-packets",
        "data/rejected",
        "data/briefs",
        "data/beliefs",
        "data/beliefs/llm-mental-models.md",
        "data/beliefs/strategy-models.md",
        "data/beliefs/questions-to-investigate.md",
        "data/golden",
    ]:
        path = root / relative
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(f"# {path.stem.replace('-', ' ').title()}\n")
        else:
            path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_markdown(path: Path, metadata: dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body.strip() + "\n", **metadata)
    path.write_text(frontmatter.dumps(post))


def read_markdown(path: Path) -> tuple[dict[str, Any], str]:
    post = frontmatter.loads(path.read_text())
    return dict(post.metadata), post.content
