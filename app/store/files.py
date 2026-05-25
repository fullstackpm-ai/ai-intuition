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
        "data/rejected",
        "data/briefs",
        "data/beliefs",
        "data/golden",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)


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
