from datetime import UTC, datetime

from app.models import RawArtifact
from app.store.db import StateStore


def _raw_artifact(artifact_id: str, raw_path: str, published_at: datetime | None) -> RawArtifact:
    return RawArtifact(
        id=artifact_id,
        source_id="lenny_podcast",
        source_name="Lenny's Podcast",
        lane="product_patterns",
        source_type="podcast_transcript",
        title="Episode",
        url="https://www.youtube.com/watch?v=t0GiTyz4syY",
        published_at=published_at,
        discovered_at=datetime(2026, 7, 24, tzinfo=UTC),
        raw_path=raw_path,
        content_hash="same-content",
    )


def test_upsert_raw_refreshes_metadata_for_same_content_hash(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite")
    try:
        old = _raw_artifact("episode_undated", "/tmp/episode_undated.md", None)
        new = _raw_artifact("episode_2026-07-19", "/tmp/episode_2026-07-19.md", datetime(2026, 7, 19, tzinfo=UTC))

        assert store.upsert_raw(old) is True
        assert store.upsert_raw(new) is True

        rows = store.list_raw()
    finally:
        store.close()

    assert len(rows) == 1
    assert rows[0].id == "episode_2026-07-19"
    assert rows[0].raw_path == "/tmp/episode_2026-07-19.md"
    assert rows[0].published_at == datetime(2026, 7, 19, tzinfo=UTC)
