from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from app import cli
from app.artifacts import build_artifact_report, classify_artifacts, collect_weekly_artifact_paths, render_artifact_report_markdown
from app.store.files import write_json, write_markdown


def _decision_by_path(root: Path, paths: list[Path]) -> dict[str, object]:
    decisions = classify_artifacts(root, [(path, "??") for path in paths])
    return {decision.path: decision for decision in decisions}


def test_classifies_raw_normalized_and_packets_by_documentation_rubric(tmp_path) -> None:
    root = tmp_path
    raw = root / "data/raw/lab-posts/source_2026-07-24_example_abcd1234.html"
    normalized = root / "data/normalized/source_2026-07-24_example_abcd1234.md"
    packet = root / "data/extraction-packets/source_2026-07-24_example_abcd1234.md"
    for path in [raw, normalized, packet]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content")

    decisions = _decision_by_path(root, [raw, normalized, packet])

    assert decisions["data/raw/lab-posts/source_2026-07-24_example_abcd1234.html"].lifecycle == "evidence"
    assert decisions["data/raw/lab-posts/source_2026-07-24_example_abcd1234.html"].recommendation == "commit"
    assert decisions["data/normalized/source_2026-07-24_example_abcd1234.md"].recommendation == "commit"
    assert decisions["data/extraction-packets/source_2026-07-24_example_abcd1234.md"].recommendation == "delete"


def test_extracted_json_with_mock_or_legacy_provenance_is_disposable(tmp_path) -> None:
    root = tmp_path
    mock_path = root / "data/extracted/mock.json"
    legacy_path = root / "data/rejected/legacy.json"
    write_json(mock_path, [{"extraction_method": "mock", "status": "accepted"}])
    write_json(legacy_path, [{"status": "rejected"}])

    decisions = _decision_by_path(root, [mock_path, legacy_path])

    assert decisions["data/extracted/mock.json"].recommendation == "delete"
    assert decisions["data/extracted/mock.json"].lifecycle == "disposable"
    assert decisions["data/rejected/legacy.json"].recommendation == "delete"


def test_real_extracted_json_is_retained_as_reviewed_knowledge(tmp_path) -> None:
    root = tmp_path
    path = root / "data/extracted/codex.json"
    write_json(path, [{"extraction_method": "codex_packet", "status": "accepted"}])

    decision = _decision_by_path(root, [path])["data/extracted/codex.json"]

    assert decision.lifecycle == "reviewed-knowledge"
    assert decision.recommendation == "commit"
    assert "codex_packet" in decision.evidence[0]


def test_briefs_require_real_extraction_provenance(tmp_path) -> None:
    root = tmp_path
    missing = root / "data/briefs/2026-W30.md"
    risky = root / "data/briefs/2026-W31.md"
    real = root / "data/briefs/2026-W32.md"
    write_markdown(missing, {"week": "2026-W30"}, "# Brief")
    write_markdown(risky, {"week": "2026-W31", "extraction_provenance": {"mock": 2}}, "# Brief")
    write_markdown(real, {"week": "2026-W32", "extraction_provenance": {"codex_packet": 2}}, "# Brief")

    decisions = _decision_by_path(root, [missing, risky, real])

    assert decisions["data/briefs/2026-W30.md"].recommendation == "delete"
    assert decisions["data/briefs/2026-W31.md"].recommendation == "delete"
    assert decisions["data/briefs/2026-W32.md"].recommendation == "commit"


def test_beliefs_runs_and_sqlite_have_distinct_retention_rules(tmp_path) -> None:
    root = tmp_path
    belief = root / "data/beliefs/llm-mental-models.md"
    run_file = root / "data/runs/run-1/summary.json"
    sqlite = root / "data/state.sqlite3"
    belief.parent.mkdir(parents=True, exist_ok=True)
    belief.write_text("# Beliefs")
    write_json(run_file, {"outcome": "unexpected_failure", "source_outcomes": {"blocked_auth": 1}})
    (run_file.parent / "failure_report.md").write_text("# Failure")
    sqlite.parent.mkdir(parents=True, exist_ok=True)
    sqlite.write_text("sqlite")

    decisions = _decision_by_path(root, [belief, run_file, sqlite])

    assert decisions["data/beliefs/llm-mental-models.md"].recommendation == "commit"
    assert decisions["data/runs/run-1/summary.json"].recommendation == "attach-to-issue"
    assert decisions["data/state.sqlite3"].recommendation == "keep-local"


def test_untracked_rerun_siblings_are_recommended_for_deletion(tmp_path, monkeypatch) -> None:
    root = tmp_path
    tracked = root / "data/raw/lab-posts/source_2026-07-24_same-title_11111111.html"
    changed = root / "data/raw/lab-posts/source_2026-07-24_same-title_22222222.html"
    for path in [tracked, changed]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content")

    monkeypatch.setattr("app.artifacts._tracked_data_paths", lambda root: [tracked])
    decision = classify_artifacts(root, [(changed, "??")])[0]

    assert decision.recommendation == "delete"
    assert decision.lifecycle == "disposable"
    assert "regenerated duplicate" in decision.reason
    assert any("11111111" in evidence for evidence in decision.evidence)


def test_clean_rerun_replacements_are_commit_eligible(tmp_path, monkeypatch) -> None:
    root = tmp_path
    stale = root / "data/raw/lab-posts/source_2026-07-24_same-title_11111111.html"
    fresh = root / "data/raw/lab-posts/source_2026-07-24_same-title_22222222.html"
    for path in [stale, fresh]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content")

    monkeypatch.setattr("app.artifacts._tracked_data_paths", lambda root: [stale])

    decisions = classify_artifacts(root, [(stale, "D"), (fresh, "??")])
    by_path = {decision.path: decision for decision in decisions}

    assert by_path["data/raw/lab-posts/source_2026-07-24_same-title_11111111.html"].recommendation == "commit"
    assert by_path["data/raw/lab-posts/source_2026-07-24_same-title_22222222.html"].recommendation == "commit"
    assert any("clean-rerun replacement" in evidence for evidence in by_path["data/raw/lab-posts/source_2026-07-24_same-title_22222222.html"].evidence)


def test_artifact_report_can_render_json_and_markdown(tmp_path) -> None:
    root = tmp_path
    raw = root / "data/raw/lab-posts/source_2026-07-24_example_abcd1234.html"
    mock = root / "data/extracted/mock.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("raw")
    write_json(mock, [{"extraction_method": "mock"}])

    report = build_artifact_report(root, changed_paths=[(raw, "??"), (mock, "??")])
    markdown = render_artifact_report_markdown(report)

    assert report.recommendations == {"commit": 1, "delete": 1}
    assert "| `delete` | `disposable` | `data/extracted/mock.json` |" in markdown


def test_artifact_report_cli_uses_classifier(tmp_path, monkeypatch) -> None:
    raw = tmp_path / "data/raw/lab-posts/source_2026-07-24_example_abcd1234.html"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("raw")

    monkeypatch.setattr(cli, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cli, "build_artifact_report", lambda root, data_dir: build_artifact_report(tmp_path, changed_paths=[(raw, "??")], data_dir=data_dir))

    result = CliRunner().invoke(cli.app, ["artifact-report", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["recommendations"] == {"commit": 1}


def test_collect_expands_untracked_run_directories(tmp_path, monkeypatch) -> None:
    run_dir = tmp_path / "data/runs/run-1"
    write_json(run_dir / "summary.json", {"outcome": "unexpected_failure"})
    (run_dir / "failure_report.md").write_text("# Failure")

    class Result:
        stdout = "?? data/runs/\n"

    monkeypatch.setattr("app.artifacts.subprocess.run", lambda *args, **kwargs: Result())

    paths = collect_weekly_artifact_paths(tmp_path, tmp_path / "data")

    assert (run_dir / "summary.json", "??") in paths
    assert (run_dir / "failure_report.md", "??") in paths
