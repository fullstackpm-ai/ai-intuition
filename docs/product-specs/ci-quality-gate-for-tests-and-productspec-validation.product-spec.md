---
spec_format_version: "0.1"
title: "CI Quality Gate for Tests and ProductSpec Validation"
artifact_type: "prd"
spec_revision: 2
status: proposed
owner: akshay
author: "akshay"
created_at: "2026-07-25T16:50:00Z"
updated_at: "2026-07-25T17:25:00Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/10
applies_to:
  - path: .github/workflows/
  - path: pyproject.toml
  - path: uv.lock
  - path: tests/
  - path: docs/product-specs/
  - path: docs/agent-runs/
  - path: docs/living/project/processes/
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

There is a second-order risk: if CI is added too broadly, it can become noisy or non-deterministic. This repo intentionally avoids live source fetches and LLM/API extraction in tests. CI should enforce the deterministic repo contract, not become a weekly ingestion runner.

## Critical Review

The original spec direction is correct, but it needs sharper implementation boundaries:

- It says "ProductSpec validation" but does not specify exact commands or whether to validate all specs or only changed specs.
- It says "agent-run receipt validation" but does not define how to handle an empty receipt set or existing receipts.
- It says "push to master" but does not define whether manual `workflow_dispatch` should exist for debugging.
- It does not specify GitHub Actions permissions. CI should need only repository read access.
- It does not define reproducibility strongly enough. Dependency installation should use `uv.lock` and fail if the lockfile is inconsistent.
- It does not distinguish hard gates from future nice-to-haves such as linting, coverage, branch protection, or scheduled runs.
- It does not define closing evidence: the implementer should prove both local commands and GitHub Actions execution.

## Hypothesis

If GitHub Actions runs the Python test suite and ProductSpec validation on pull requests and pushes to `master`, then regressions in pipeline behavior, observability, artifact policy, and ProductSpec structure will be caught before they become durable repo history.

## Product Summary

Add a lightweight CI workflow that treats tests and ProductSpec validation as required quality gates for consequential changes.

The workflow should install Python through `uv`, run the deterministic pytest suite, validate all repo ProductSpec files, validate committed agent-run receipts, and run the ProductSpec graph check. It should not run live network source discovery, live weekly ingestion, or LLM/API-backed extraction.

The first version should optimize for reliability over breadth. A small, deterministic CI gate that always runs is more valuable than a broad gate that flakes or requires credentials.

## Scope

```productspec-scope
in:
  - Add a GitHub Actions workflow under .github/workflows/.
  - Run on pull_request, push to master, and manual workflow_dispatch.
  - Use minimum necessary GitHub Actions permissions, preferably contents: read.
  - Install uv and Python 3.12 in CI.
  - Run uv sync --locked or an equivalent locked dependency installation.
  - Run uv run pytest.
  - Validate every docs/product-specs/*.product-spec.md file with @productspec/parser using npm exec.
  - Validate committed docs/agent-runs/*.agent-run.json receipts with @productspec/parser when present, and skip cleanly when none exist.
  - Run productspec graph docs/product-specs --json and fail on parser errors or graph warnings.
  - Keep CI deterministic and credential-free.
  - Document the CI gate in AGENTS.md or a living process doc.
out:
  - Live weekly source fetching in CI.
  - OpenAI/API-backed extraction in CI.
  - useTranscribe calls in CI.
  - Any CI step that requires repository secrets.
  - GitHub branch protection configuration that must be changed through repository settings.
  - Hosted observability dashboards.
cut:
  - Code coverage thresholds.
  - Matrix testing across multiple Python versions.
  - Scheduled weekly pipeline execution.
  - Linting or type checking unless a configured tool already exists.
```

### In

- Create `.github/workflows/ci.yml`.
- Trigger on `pull_request`, `push` to `master`, and `workflow_dispatch`.
- Run deterministic tests without network or LLM credentials.
- Validate ProductSpec files and agent-run receipts.
- Validate all ProductSpec files, not only changed files. Specs are few, and all-spec validation catches cross-file drift.
- Run the ProductSpec graph check after individual validation.
- Keep CI runtime small enough to stay useful on every PR/push.
- Update repo directives so future changes treat CI as the hard enforcement layer for tests/spec validity.

### Out

- Do not add live integration tests that depend on source websites.
- Do not add secret-dependent model/API calls.
- Do not change branch protection settings in this spec.
- Do not add scheduled weekly execution.
- Do not make CI responsible for artifact retention cleanup.

### Cut

- Coverage reporting.
- Lint/type-check adoption unless already configured.
- Scheduled Codex or weekly-run automation.

## Required CI Commands

The workflow should implement the equivalent of:

```bash
uv sync --locked
uv run pytest

for spec in docs/product-specs/*.product-spec.md; do
  npm exec --yes --package @productspec/parser -- productspec validate "$spec"
done

shopt -s nullglob
for receipt in docs/agent-runs/*.agent-run.json; do
  npm exec --yes --package @productspec/parser -- productspec validate-run "$receipt"
done

npm exec --yes --package @productspec/parser -- productspec graph docs/product-specs --json
```

Implementation can split these into clearer workflow steps. The important behavior is that failures stop the workflow and receipts are skipped cleanly if no matching files exist.

## CI Safety Requirements

- Set workflow permissions to the minimum needed for checks, normally:

```yaml
permissions:
  contents: read
```

- Do not reference OpenAI, useTranscribe, paid feed, or personal credentials.
- Do not run `uv run aic run-weekly`, `uv run aic ingest`, `uv run aic discover`, `uv run aic transcribe`, or API-backed extraction.
- Do not commit or mutate repo files from CI.
- Use locked dependency installation so CI catches dependency drift instead of silently rewriting lock state.
- Prefer explicit, named workflow steps so failures identify whether tests, spec validation, receipt validation, or graph validation broke.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: A GitHub Actions workflow runs on pull_request, push to master, and workflow_dispatch.
- id: AC-2
  criterion: CI uses minimum necessary GitHub Actions permissions and does not require repository secrets.
- id: AC-3
  criterion: CI installs uv and Python 3.12, then installs project dependencies reproducibly with uv.lock enforcement.
- id: AC-4
  criterion: CI runs uv run pytest and fails if tests fail.
- id: AC-5
  criterion: CI validates all docs/product-specs/*.product-spec.md files with @productspec/parser.
- id: AC-6
  criterion: CI validates committed docs/agent-runs/*.agent-run.json receipts with @productspec/parser when any exist, and skips cleanly when none exist.
- id: AC-7
  criterion: CI runs productspec graph docs/product-specs --json and fails on parser errors or graph warnings.
- id: AC-8
  criterion: CI does not run live weekly ingestion, source discovery, transcribe calls, useTranscribe calls, or LLM/API extraction.
- id: AC-9
  criterion: AGENTS.md or a living process doc states that CI is the hard gate for tests and ProductSpec validity.
- id: AC-10
  criterion: The implementation includes evidence from a local verification run of the same commands CI executes.
- id: AC-11
  criterion: After push, the implementer records the GitHub Actions run result or clearly states why remote CI could not be observed.
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
- id: SM-4
  metric: CI failures are diagnosable without reading the full raw log.
  target: Failed checks identify the failing gate by step name: tests, ProductSpec validation, agent-run validation, or graph validation.
  window: Every failed CI run.
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/10
- Test suite: `tests/`
- ProductSpec directive: `docs/living/project/processes/productspec-directive.md`
- ProductSpec implementation workflow: `docs/living/project/processes/productspec-implementation-workflow.md`
- Observability spec: `docs/product-specs/pipeline-observability-and-failure-regression-harness.product-spec.md`
- Artifact retention spec: `docs/product-specs/weekly-run-artifact-retention-and-promotion-policy.product-spec.md`
- Existing issue template: `.github/ISSUE_TEMPLATE/product-spec-work.md`

## Execution Notes

- Prefer a single workflow with separate named steps for tests, ProductSpec validation, receipt validation, and graph validation.
- Use shell loops carefully so an empty `docs/agent-runs/*.agent-run.json` set does not fail the workflow incorrectly.
- Keep the first CI version intentionally narrow; add linting or coverage later only if it starts catching real regressions.
- If the ProductSpec graph command emits warnings but exits successfully, the implementation should still fail the step when warnings are present. The repo should treat graph warnings as work that needs attention.
- If branch protection is desired later, handle it as a separate repo-settings task after this workflow exists and has produced at least one clean run.
