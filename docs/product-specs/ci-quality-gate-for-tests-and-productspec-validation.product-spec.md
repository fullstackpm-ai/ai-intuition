---
spec_format_version: "0.1"
title: "CI Quality Gate for Tests and ProductSpec Validation"
artifact_type: "prd"
spec_revision: 1
status: proposed
owner: akshay
author: "akshay"
created_at: "2026-07-25T16:50:00Z"
updated_at: "2026-07-25T16:50:00Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/10
applies_to:
  - path: .github/workflows/
  - path: pyproject.toml
  - path: uv.lock
  - path: tests/
  - path: docs/product-specs/
  - path: docs/agent-runs/
  - path: AGENTS.md
---

# CI Quality Gate for Tests and ProductSpec Validation

## Problem

Tests and observability are now first-class repo expectations, but they are enforced by local discipline rather than an automated GitHub gate.

Today a future change can be pushed without running:

- `uv run pytest`
- ProductSpec validation for changed or existing specs
- ProductSpec graph checks
- agent-run receipt validation for material ProductSpec implementations

That leaves a gap between the repo's stated process and the actual merge/push safety net.

## Hypothesis

If GitHub Actions runs the Python test suite and ProductSpec validation on pull requests and pushes to `master`, then regressions in pipeline behavior, observability, artifact policy, and ProductSpec structure will be caught before they become durable repo history.

## Product Summary

Add a lightweight CI workflow that treats tests and ProductSpec validation as required quality gates for consequential changes.

The workflow should install Python through `uv`, run the deterministic pytest suite, validate all repo ProductSpec files, validate committed agent-run receipts, and run the ProductSpec graph check. It should not run live network source discovery, live weekly ingestion, or LLM/API-backed extraction.

## Scope

```productspec-scope
in:
  - Add a GitHub Actions workflow under .github/workflows/.
  - Install uv and Python 3.12 in CI.
  - Run uv sync or equivalent dependency installation.
  - Run uv run pytest.
  - Validate every docs/product-specs/*.product-spec.md file with @productspec/parser.
  - Validate committed docs/agent-runs/*.agent-run.json receipts with @productspec/parser when present.
  - Run productspec graph docs/product-specs --json and fail on parser errors.
  - Document the CI gate in AGENTS.md or a living process doc.
out:
  - Live weekly source fetching in CI.
  - OpenAI/API-backed extraction in CI.
  - GitHub branch protection configuration that must be changed through repository settings.
  - Hosted observability dashboards.
cut:
  - Code coverage thresholds.
  - Matrix testing across multiple Python versions.
  - Scheduled weekly pipeline execution.
```

### In

- Create `.github/workflows/ci.yml`.
- Run deterministic tests without network or LLM credentials.
- Validate ProductSpec files and agent-run receipts.
- Keep CI runtime small enough to stay useful on every PR/push.
- Update repo directives so future changes treat CI as the hard enforcement layer for tests/spec validity.

### Out

- Do not add live integration tests that depend on source websites.
- Do not add secret-dependent model/API calls.
- Do not change branch protection settings in this spec.

### Cut

- Coverage reporting.
- Lint/type-check adoption unless already configured.
- Scheduled Codex or weekly-run automation.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: A GitHub Actions workflow runs on pull_request and push to master.
- id: AC-2
  criterion: CI installs uv and Python 3.12, then installs project dependencies reproducibly.
- id: AC-3
  criterion: CI runs uv run pytest and fails if tests fail.
- id: AC-4
  criterion: CI validates all docs/product-specs/*.product-spec.md files with @productspec/parser.
- id: AC-5
  criterion: CI validates committed docs/agent-runs/*.agent-run.json receipts with @productspec/parser when any exist.
- id: AC-6
  criterion: CI runs productspec graph docs/product-specs --json and fails on parser errors.
- id: AC-7
  criterion: CI does not run live weekly ingestion, source discovery, transcribe calls, or LLM/API extraction.
- id: AC-8
  criterion: AGENTS.md or a living process doc states that CI is the hard gate for tests and ProductSpec validity.
```

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Pull requests and pushes surface deterministic test or ProductSpec failures without relying on local memory.
  target: A failed test/spec blocks with a visible GitHub Actions failure.
  window: Per PR or push.
- id: SM-2
  metric: ProductSpec and agent-run receipt files remain parser-valid over time.
  target: CI catches invalid spec/receipt syntax before merge.
  window: Per committed spec change.
- id: SM-3
  metric: CI remains deterministic and credential-free.
  target: No workflow step requires live source websites, OpenAI credentials, or useTranscribe quota.
  window: Every CI run.
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/10
- Test suite: `tests/`
- ProductSpec directive: `docs/living/project/processes/productspec-directive.md`
- ProductSpec implementation workflow: `docs/living/project/processes/productspec-implementation-workflow.md`
- Observability spec: `docs/product-specs/pipeline-observability-and-failure-regression-harness.product-spec.md`
- Artifact retention spec: `docs/product-specs/weekly-run-artifact-retention-and-promotion-policy.product-spec.md`

## Execution Notes

- Prefer a single workflow with separate named steps for tests, ProductSpec validation, receipt validation, and graph validation.
- Use shell loops carefully so an empty `docs/agent-runs/*.agent-run.json` set does not fail the workflow incorrectly.
- Keep the first CI version intentionally narrow; add linting or coverage later only if it starts catching real regressions.
