from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = Path(".github/workflows/ci.yml")


def _load_workflow() -> dict[str, object]:
    return yaml.load(WORKFLOW_PATH.read_text(), Loader=yaml.BaseLoader)


def test_ci_workflow_runs_for_prs_master_pushes_and_manual_dispatch() -> None:
    workflow = _load_workflow()

    triggers = workflow["on"]

    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["master"]
    assert "workflow_dispatch" in triggers


def test_ci_workflow_uses_minimum_permissions_and_locked_dependency_install() -> None:
    workflow = _load_workflow()
    workflow_text = WORKFLOW_PATH.read_text()

    assert workflow["permissions"] == {"contents": "read"}
    assert "actions/setup-node@v4" in workflow_text
    assert 'node-version: "22"' in workflow_text
    assert "uv sync --locked" in workflow_text
    assert "uv run pytest" in workflow_text


def test_ci_workflow_validates_product_specs_receipts_and_graph_warnings() -> None:
    workflow_text = WORKFLOW_PATH.read_text()

    assert "productspec validate \"$spec\"" in workflow_text
    assert "productspec validate-run \"$receipt\"" in workflow_text
    assert "productspec graph docs/product-specs --json" in workflow_text
    assert "ProductSpec graph warnings are treated as CI failures" in workflow_text


def test_ci_workflow_does_not_run_live_or_credentialed_pipeline_steps() -> None:
    workflow_text = WORKFLOW_PATH.read_text()
    forbidden_fragments = [
        "OPENAI_API_KEY",
        "USETRANSCRIBE",
        "useTranscribe",
        "run-weekly",
        " aic ingest",
        " aic discover",
        " aic transcribe",
        " transcribe?",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in workflow_text
