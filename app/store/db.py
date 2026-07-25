from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from app.models import ExtractedInsight, NormalizedItem, RawArtifact, Source
from app.time import iso


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lane TEXT NOT NULL,
  type TEXT NOT NULL,
  enabled INTEGER NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_artifacts (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  published_at TEXT,
  discovered_at TEXT NOT NULL,
  raw_path TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS normalized_items (
  id TEXT PRIMARY KEY,
  raw_artifact_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  published_at TEXT,
  normalized_path TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS extracted_insights (
  id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  command TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL
);
"""


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_sources(self, sources: Iterable[Source]) -> None:
        with self.conn:
            for source in sources:
                self.conn.execute(
                    """
                    INSERT INTO sources (id, name, lane, type, enabled, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      name=excluded.name,
                      lane=excluded.lane,
                      type=excluded.type,
                      enabled=excluded.enabled,
                      payload_json=excluded.payload_json
                    """,
                    (
                        source.id,
                        source.name,
                        source.lane,
                        source.type,
                        int(source.enabled),
                        source.model_dump_json(),
                    ),
                )

    def raw_exists_hash(self, digest: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM raw_artifacts WHERE content_hash = ?", (digest,)).fetchone()
        return row is not None

    def upsert_raw(self, artifact: RawArtifact) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO raw_artifacts
                  (id, source_id, title, url, published_at, discovered_at, raw_path, content_hash, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                  id=excluded.id,
                  source_id=excluded.source_id,
                  title=excluded.title,
                  url=excluded.url,
                  published_at=excluded.published_at,
                  discovered_at=excluded.discovered_at,
                  raw_path=excluded.raw_path,
                  payload_json=excluded.payload_json
                WHERE raw_artifacts.id IS NOT excluded.id
                  OR raw_artifacts.source_id IS NOT excluded.source_id
                  OR raw_artifacts.title IS NOT excluded.title
                  OR raw_artifacts.url IS NOT excluded.url
                  OR raw_artifacts.published_at IS NOT excluded.published_at
                  OR raw_artifacts.raw_path IS NOT excluded.raw_path
                  OR raw_artifacts.payload_json IS NOT excluded.payload_json
                """,
                (
                    artifact.id,
                    artifact.source_id,
                    artifact.title,
                    artifact.url,
                    iso(artifact.published_at),
                    iso(artifact.discovered_at),
                    artifact.raw_path,
                    artifact.content_hash,
                    artifact.model_dump_json(),
                ),
            )
        return cursor.rowcount > 0

    def list_raw(self, item_id: str | None = None) -> list[RawArtifact]:
        sql = "SELECT payload_json FROM raw_artifacts"
        params: tuple[str, ...] = ()
        if item_id:
            sql += " WHERE id = ?"
            params = (item_id,)
        rows = self.conn.execute(sql, params).fetchall()
        return [RawArtifact.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_normalized(self, item: NormalizedItem) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO normalized_items
                  (id, raw_artifact_id, source_id, published_at, normalized_path, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  normalized_path=excluded.normalized_path,
                  payload_json=excluded.payload_json
                """,
                (
                    item.id,
                    item.raw_artifact_id,
                    item.source_id,
                    iso(item.published_at),
                    item.normalized_path,
                    item.model_dump_json(),
                ),
            )

    def list_normalized(self, item_id: str | None = None) -> list[NormalizedItem]:
        sql = "SELECT payload_json FROM normalized_items"
        params: tuple[str, ...] = ()
        if item_id:
            sql += " WHERE id = ?"
            params = (item_id,)
        rows = self.conn.execute(sql, params).fetchall()
        return [NormalizedItem.model_validate_json(row["payload_json"]) for row in rows]

    def upsert_insights(self, insights: Iterable[ExtractedInsight]) -> None:
        with self.conn:
            for insight in insights:
                self.conn.execute(
                    """
                    INSERT INTO extracted_insights (id, item_id, status, created_at, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      status=excluded.status,
                      payload_json=excluded.payload_json
                    """,
                    (
                        insight.id,
                        insight.item_id,
                        insight.status,
                        iso(insight.created_at),
                        insight.model_dump_json(),
                    ),
                )

    def list_insights(self, status: str | None = None) -> list[ExtractedInsight]:
        sql = "SELECT payload_json FROM extracted_insights"
        params: tuple[str, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        rows = self.conn.execute(sql, params).fetchall()
        deduped: dict[tuple[str, str, str], ExtractedInsight] = {}
        for row in rows:
            insight = ExtractedInsight.model_validate_json(row["payload_json"])
            key = (insight.item_id, insight.claim, insight.mechanism)
            existing = deduped.get(key)
            if existing is None or insight.created_at > existing.created_at:
                deduped[key] = insight
        return list(deduped.values())

    def log_run(self, command: str, metadata: dict[str, object]) -> None:
        from app.time import now_utc

        with self.conn:
            self.conn.execute(
                "INSERT INTO runs (command, created_at, metadata_json) VALUES (?, ?, ?)",
                (command, iso(now_utc()), json.dumps(metadata, default=str)),
            )
