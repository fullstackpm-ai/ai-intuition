---
spec_format_version: "0.1"
title: "Weekly Run Artifact Retention and Promotion Policy"
artifact_type: "prd"
spec_revision: 1
status: proposed
owner: akshay
author: "akshay"
created_at: "2026-07-25T15:45:00Z"
updated_at: "2026-07-25T15:45:00Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/9
applies_to:
  - path: data/raw/
  - path: data/normalized/
  - path: data/extraction-packets/
  - path: data/extracted/
  - path: data/rejected/
  - path: data/briefs/
  - path: data/runs/
  - path: data/beliefs/
  - path: docs/living/project/processes/artifact-commit-policy.md
  - path: app/cli.py
  - path: tests/
---

# Weekly Run Artifact Retention and Promotion Policy

## Problem

The weekly pipeline now produces several classes of artifacts:

- raw source captures
- normalized extraction inputs
- Codex extraction packets
- real extracted insight JSON
- rejected insight JSON
- weekly briefs
- belief updates
- run diagnostics under `data/runs/`
- local SQLite state

After a live run, the operator still has to decide manually what to commit, what to delete, what to keep locally for review, and what should only be promoted after real extraction.

The 2026-W30 rerun exposed the ambiguity. The pipeline correctly wrote raw, normalized, extraction-packet, and run diagnostic artifacts, but it is not yet deterministic whether those files should become durable repo history or be treated as disposable working output.

This ambiguity creates two risks:

- Knowledge pollution: mock, unreviewed, or low-signal artifacts get committed and make the repo history look more meaningful than it is.
- Evidence loss: useful raw source captures or run diagnostics are deleted even though they would help reproduce a source failure or future extraction.

## Hypothesis

If weekly run artifacts have a deterministic retention and promotion workflow, then the repo can stay clean while preserving the evidence needed for real synthesis, debugging, and future review.

If the CLI can summarize and classify post-run artifacts, then the operator can make commit/delete/promote decisions without inspecting dozens of files by hand.

## Product Summary

The project should have an explicit weekly artifact lifecycle: generated artifacts start as working output, then are either deleted, retained locally, committed as evidence, promoted into reviewed knowledge, or attached to a bug/spec as diagnostic evidence.

The output of this spec should be a policy and, if needed, CLI support that answers after each weekly run:

- What changed?
- Which artifacts are safe to commit?
- Which artifacts should be reviewed before commit?
- Which artifacts should be deleted?
- Which artifacts are diagnostic evidence for an issue?
- Which artifacts are durable knowledge?

## Scope

```productspec-scope
in:
  - Define artifact lifecycle states for weekly run outputs.
  - Define commit/delete/promote rules for raw, normalized, extraction packets, extracted JSON, rejected JSON, briefs, beliefs, run diagnostics, and SQLite state.
  - Decide whether run diagnostics should be committed by default, attached to issues, or kept local.
  - Add a CLI command or dry-run report that classifies current uncommitted weekly artifacts by recommended action.
  - Ensure summarized artifacts such as briefs are committed only when based on real/reviewed extraction provenance.
  - Add tests for artifact classification and policy enforcement.
  - Update artifact commit policy and AGENTS guidance.
out:
  - Cloud artifact storage.
  - Database-backed artifact repository.
  - Web UI for artifact review.
  - Automatic deletion without an explicit operator action.
  - Automatic insight extraction or synthesis quality review.
cut:
  - Long-term archive compression.
  - Per-source retention tuning beyond defaults.
  - Git LFS or external blob storage.
```

### In

- Define lifecycle states: working, retained-local, evidence, review-packet, reviewed-knowledge, diagnostic, disposable.
- Define policy for each `data/` path.
- Define how live `data/runs/**` diagnostics relate to GitHub issues.
- Define what happens to regenerated weekly artifacts when the same week is rerun.
- Provide a deterministic report of recommended actions after `run-weekly`.
- Add tests that prevent mock or unreviewed summaries from being recommended as durable knowledge.

### Out

- Hosted artifact store.
- Web dashboard.
- Automated cleanup without operator visibility.
- Changing source discovery or extraction quality directly.

### Cut

- Full content-addressed artifact store.
- Semantic deduplication across all raw sources.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: The repo has a documented lifecycle model for weekly artifacts, including working, evidence, review-packet, reviewed-knowledge, diagnostic, and disposable states.
- id: AC-2
  criterion: Each major data path has a deterministic default action: data/raw, data/normalized, data/extraction-packets, data/extracted, data/rejected, data/briefs, data/beliefs, data/runs, and data/state.sqlite3.
- id: AC-3
  criterion: A post-run command or report can classify uncommitted artifacts into commit, review, keep-local, attach-to-issue, or delete recommendations.
- id: AC-4
  criterion: The policy distinguishes raw evidence from summarized knowledge and prevents unreviewed/mock summaries from being recommended as durable knowledge.
- id: AC-5
  criterion: Run diagnostics are retained or promoted only when they explain failures, validate a regression fix, or document an operational incident.
- id: AC-6
  criterion: Rerunning the same week does not make stale artifacts look current; superseded artifacts are identified or recommended for cleanup.
- id: AC-7
  criterion: Tests cover classification for raw/normalized artifacts, extraction packets, real extracted JSON, mock extracted JSON, briefs, belief files, run diagnostics, and SQLite state.
- id: AC-8
  criterion: Observability events or run summaries capture enough metadata for the post-run artifact report to explain why a recommendation was made.
- id: AC-9
  criterion: uv run pytest passes.
```

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: After a weekly run, the operator can decide what to commit or delete from a single artifact report.
  target: No manual scan of all generated data paths is required for first-pass cleanup.
  window: Per weekly run.
- id: SM-2
  metric: Durable knowledge commits contain reviewed extraction or synthesis, not mock or unreviewed generated summaries.
  target: No mock-derived briefs or extracted JSON are committed outside fixtures.
  window: Per artifact commit.
- id: SM-3
  metric: Diagnostic run artifacts are linked to an issue or spec when committed.
  target: Every committed data/runs folder has a stated purpose.
  window: Per diagnostic artifact commit.
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/9
- Artifact policy: `docs/living/project/processes/artifact-commit-policy.md`
- Agent guidance: `AGENTS.md`
- Weekly observability: `docs/product-specs/pipeline-observability-and-failure-regression-harness.product-spec.md`
- Real extraction workflow: `docs/product-specs/real-sensemaking-extraction-workflow.product-spec.md`
- Current live run diagnostics: `data/runs/20260725T083648Z-run-weekly-0c61fd/`
- Generated weekly artifacts: `data/raw/`, `data/normalized/`, `data/extraction-packets/`

## Execution Notes

- Start with policy and classification tests before adding CLI behavior.
- Prefer a dry-run report before any destructive cleanup command.
- Do not make artifact volume the primary decision criterion. Commit semantics should be based on evidence value, review state, provenance, and reproducibility.
