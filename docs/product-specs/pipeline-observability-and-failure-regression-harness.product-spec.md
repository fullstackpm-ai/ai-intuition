---
spec_format_version: "0.1"
title: "Pipeline Observability and Failure Regression Harness"
artifact_type: "prd"
spec_revision: 2
status: proposed
owner: akshay
author: "akshay"
created_at: "2026-07-25T06:21:49Z"
updated_at: "2026-07-25T15:21:00Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/4
applies_to:
  - path: app/cli.py
  - path: app/ingest/
  - path: app/normalize/
  - path: app/llm/
  - path: app/store/db.py
  - path: app/store/files.py
  - path: tests/
  - path: data/runs/
---

# Pipeline Observability and Failure Regression Harness

## Problem

The AI Intuition Compiler can discover, ingest, normalize, packet, import, edit, brief, and update beliefs, but a weekly run still behaves like a mostly opaque script.

When a source fails, the operator often sees a transient terminal line such as `Skipped openai_research: 403 Forbidden`, but the durable project state does not preserve enough detail to answer:

- Which sources were attempted?
- Which stage failed: discovery, fetch, transcript, normalize, extraction packet, import, edit, brief, or belief update?
- Was the failure expected, retryable, permanent, or a likely adapter regression?
- Did the source produce zero items because there was no new material, or because discovery silently broke?
- Did fallback behavior run, such as podcast YouTube transcript first and Substack transcript fallback second?
- What artifact counts changed in this run?
- Can a future Codex session diagnose the problem without re-running live network calls?

This is now higher priority because Issue #6 made weekly runs safer: the default run stops after Codex extraction packets instead of generating mock-derived briefs. The next bottleneck is run diagnosis. If discovery, ingestion, or transcript paths fail, the system needs structured evidence that explains where and why.

## Critical Review of Existing Spec

The original Issue #4 direction is correct, but it needs a tighter v1 boundary:

- It says "observability" but does not define the durable file contract a run must produce.
- It asks for broad failure tests, but does not separate source discovery failures from transcript-provider failures and pipeline-stage failures.
- It mentions retryability but does not define a classification vocabulary or mapping rules.
- It risks turning into a retry/repair project. V1 should classify and preserve failures, not retry or self-heal them.
- It does not explicitly address partial success, which is the common weekly-run case: one source fails while other sources produce useful artifacts.
- It does not say how this interacts with repo hygiene. Run diagnostics are operational artifacts, not belief artifacts, and should be committed only when useful for a bug/spec/fixture.

## Hypothesis

If each pipeline invocation creates a durable run folder with structured event logs, source attempt records, artifact counts, and a human-readable failure report, then the system can be debugged and improved without depending on terminal scrollback or repeated live fetches.

If the failure taxonomy is covered by deterministic regression tests, then source-adapter fixes can be made without accidentally breaking podcast transcripts, RSS discovery, HTML discovery, normalization, or the safe extraction-packet workflow.

## Product Summary

The weekly pipeline will emit a durable, structured run record that explains what was attempted, what succeeded, what failed, why each failure was classified that way, and which artifacts were written or left unchanged.

The implementation will add a small observability layer around the existing repo-first pipeline. It will not add hosted monitoring, auto-repair, retries, or a dashboard. Its job is to make every weekly run inspectable by a future Codex session and regression-testable by maintainers.

## Scope

```productspec-scope
in:
  - Create a run observability module with typed models for run metadata, events, source attempts, stage results, and failure classifications.
  - Create per-run folders under data/runs/<run_id>/.
  - Write manifest.json, events.jsonl, summary.json, and conditional failure_report.md.
  - Record per-source discovery and ingestion attempts with outcome and retryability classification.
  - Record stage-level outcomes for normalize, extract packet, import extraction, edit, brief, and belief update.
  - Preserve partial success when independent sources fail.
  - Persist compact run/source/stage summaries in SQLite.
  - Add deterministic regression tests for common source, transcript, and pipeline failures.
  - Update artifact policy for data/runs/**.
out:
  - Hosted monitoring, dashboards, alerts, email, or push notifications.
  - Automatic source repair.
  - New retry policy beyond existing library behavior.
  - LLM-based diagnosis.
  - Live network integration tests.
  - Full source adapter rewrite.
  - Full OpenTelemetry integration.
cut:
  - Retry scheduling.
  - Event-driven weekly automation.
  - Browser UI for run inspection.
  - Source quality scoring beyond outcome/status labels.
  - Historical run analytics beyond compact SQLite summaries.
```

### In

- Create a run observability module with typed Pydantic models for run metadata, events, source attempts, stage results, and failure classifications.
- Create a per-run directory under `data/runs/<run_id>/`.
- Write a machine-readable `manifest.json` for each run.
- Write append-only `events.jsonl` for stage/source/artifact events.
- Write `summary.json` for final counts and outcome.
- Write `failure_report.md` when any source or stage has a non-success outcome.
- Record per-source attempts for discovery and ingestion, including adapter, URL, item counts, artifact counts, elapsed time, and outcome classification.
- Record stage-level outcomes for normalize, extract packet, import extraction, edit, brief, and belief update.
- Preserve partial success: one failed source must not prevent unrelated sources from completing where the current pipeline already allows continuation.
- Add SQLite tables for durable run summaries and source/stage attempt summaries, while keeping verbose details file-based.
- Add deterministic regression tests for common failure modes without requiring network or LLM credentials.
- Update artifact policy to explain when `data/runs/**` should be committed.

### Out

- Hosted monitoring, dashboards, alerts, email, or push notifications.
- Automatic source repair.
- Automatic retries beyond existing library behavior.
- LLM-based diagnosis.
- Live network integration tests.
- Full rewrite of source adapters.
- Full OpenTelemetry integration.

### Cut

- Retry scheduling.
- Event-driven weekly automation.
- Browser UI for run inspection.
- Source quality scoring beyond outcome/status labels.
- Historical run analytics beyond listing and reading current SQLite summaries.

## Run Artifact Contract

Each `run-weekly` invocation creates:

```text
data/runs/<run_id>/
  manifest.json
  events.jsonl
  summary.json
  failure_report.md        # only when failures, warnings, or unhealthy-empty outcomes exist
```

`run_id` should be stable enough for local inspection and unique enough to avoid collisions:

```text
YYYYMMDDTHHMMSSZ-<command>-<short_random_or_hash>
```

The run folder is operational evidence. It is not automatically durable knowledge.

## Event Model

Every event should include:

- `run_id`
- `timestamp`
- `command`
- `stage`
- `event_type`
- `level`
- `source_id` when applicable
- `adapter` when applicable
- `url` when applicable
- `artifact_id` or `artifact_path` when applicable
- `elapsed_ms` when a bounded operation completes
- `message`
- `metadata`

Required event types:

- `run_started`
- `run_finished`
- `stage_started`
- `stage_finished`
- `source_attempt_started`
- `source_attempt_finished`
- `source_skipped`
- `source_failed`
- `artifact_written`
- `artifact_unchanged`
- `fallback_attempted`
- `fallback_succeeded`
- `fallback_failed`

## Outcome and Failure Taxonomy

Source and stage outcomes should use this vocabulary:

- `success`: completed and produced expected output or confirmed no changes.
- `healthy_empty`: completed successfully but found no items in the requested window.
- `skipped_config`: intentionally skipped because source type/adapter does not apply.
- `blocked_auth`: missing credentials, paid feed unavailable, login wall, or explicit 401/403 that requires access changes.
- `blocked_provider`: upstream provider does not support the request, such as useTranscribe not creating new Spotify transcripts.
- `rate_limited`: HTTP 429 or provider quota response.
- `not_found`: HTTP 404 or missing cached transcript.
- `malformed_source`: parseable request succeeded, but RSS/HTML/SSE payload shape was invalid or unusable.
- `adapter_regression`: source responded, but local extraction/discovery logic failed or returned clearly invalid candidates.
- `network_failure`: DNS, timeout, connection reset, TLS, or transient transport issue.
- `unexpected_failure`: uncategorized exception.

Retryability classification:

- `retryable`: network failure, 429, timeout, transient 5xx.
- `permanent`: unsupported URL, too long, not found, disabled source, missing transcript cache.
- `operator_action_required`: auth/paywall, credentials, missing env var, provider policy change.
- `bug_likely`: malformed parsing, adapter regression, schema mismatch, unexpected exception.
- `not_applicable`: success, healthy empty, skipped config.

## Stage Coverage

`run-weekly` should record these stage boundaries:

- `ingest`
- `normalize`
- `extract`
- `edit` when extraction mode is not `codex_packet`
- `brief` when extraction mode is not `codex_packet`
- `belief_update` when extraction mode is not `codex_packet`
- `send` when requested

The default `codex_packet` mode should explicitly record that edit, brief, and belief update were skipped because real extraction imports are required first.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: uv run aic run-weekly creates data/runs/<run_id>/manifest.json, events.jsonl, and summary.json.
- id: AC-2
  criterion: manifest.json includes command, args/options, git commit when available, start time, data directory, Python version, extraction mode, and source filter/window when applicable.
- id: AC-3
  criterion: events.jsonl contains structured events for run start/finish, stage start/finish, source attempt start/finish, source skip/failure, fallback attempt/result, and artifact write/unchanged.
- id: AC-4
  criterion: Every source attempt records source id, source name, source type, lane, adapter, URLs attempted, item count, artifact count, elapsed time, outcome, retryability, and error details when applicable.
- id: AC-5
  criterion: Error details include exception class, message, HTTP status when available, provider error code when available, and enough context to reproduce the failing URL/adapter step.
- id: AC-6
  criterion: summary.json includes total sources attempted, source outcomes by class, artifact counts by stage, extraction mode, run outcome, and paths to any failure report.
- id: AC-7
  criterion: failure_report.md is written when any outcome is not success, healthy_empty, or skipped_config; it groups failures by source/stage and recommends the next diagnostic action.
- id: AC-8
  criterion: healthy_empty is not treated as a failure, but is visible in summary.json and the event log.
- id: AC-9
  criterion: run-weekly --extraction-mode codex_packet records intentional skips for edit, brief, and belief update without marking the run failed.
- id: AC-10
  criterion: A single source failure does not prevent other independent sources from completing, and the partial success is visible in the run summary.
- id: AC-11
  criterion: SQLite records compact run summaries and source/stage attempt summaries; verbose event payloads remain file-based.
- id: AC-12
  criterion: Pipeline idempotency is preserved. Re-running a weekly job must not duplicate raw, normalized, extracted, rejected, brief, or belief artifacts.
- id: AC-13
  criterion: Tests cover event serialization, failure classification, run artifact writing, SQLite persistence, failure report rendering, and partial-success weekly orchestration.
- id: AC-14
  criterion: Tests cover representative source failures including HTTP 403, HTTP 429, 404 cached transcript miss, malformed RSS, malformed HTML/no article candidates, useTranscribe SSE error, unsupported Spotify transcription, and Substack transcript fallback.
- id: AC-15
  criterion: uv run pytest passes without network access or LLM credentials.
```

- `AC-1`: `uv run aic run-weekly` creates `data/runs/<run_id>/manifest.json`, `events.jsonl`, and `summary.json`.
- `AC-2`: `manifest.json` includes command, args/options, git commit when available, start time, data directory, Python version, extraction mode, and source filter/window when applicable.
- `AC-3`: `events.jsonl` contains structured events for run start/finish, stage start/finish, source attempt start/finish, source skip/failure, fallback attempt/result, and artifact write/unchanged.
- `AC-4`: Every source attempt records source id, source name, source type, lane, adapter, URLs attempted, item count, artifact count, elapsed time, outcome, retryability, and error details when applicable.
- `AC-5`: Error details include exception class, message, HTTP status when available, provider error code when available, and enough context to reproduce the failing URL/adapter step.
- `AC-6`: `summary.json` includes total sources attempted, source outcomes by class, artifact counts by stage, extraction mode, run outcome, and paths to any failure report.
- `AC-7`: `failure_report.md` is written when any outcome is not `success`, `healthy_empty`, or `skipped_config`; it groups failures by source/stage and recommends the next diagnostic action.
- `AC-8`: `healthy_empty` is not treated as a failure, but is visible in `summary.json` and the event log.
- `AC-9`: `run-weekly --extraction-mode codex_packet` records intentional skips for edit, brief, and belief update without marking the run failed.
- `AC-10`: A single source failure does not prevent other independent sources from completing, and the partial success is visible in the run summary.
- `AC-11`: SQLite records compact run summaries and source/stage attempt summaries; verbose event payloads remain file-based.
- `AC-12`: Pipeline idempotency is preserved. Re-running a weekly job must not duplicate raw, normalized, extracted, rejected, brief, or belief artifacts.
- `AC-13`: Tests cover event serialization, failure classification, run artifact writing, SQLite persistence, failure report rendering, and partial-success weekly orchestration.
- `AC-14`: Tests cover representative source failures: HTTP 403, HTTP 429, 404 cached transcript miss, malformed RSS, malformed HTML/no article candidates, useTranscribe SSE error, unsupported Spotify transcription, and Substack transcript fallback.
- `AC-15`: `uv run pytest` passes without network access or LLM credentials.

## Regression Fixtures

Add fixture-driven tests rather than live source tests:

- RSS feed with valid dated entries.
- RSS response that is HTTP 403.
- RSS response that is HTTP 429.
- RSS payload that is syntactically valid XML but not a usable feed.
- HTML index with valid article cards.
- HTML index that returns only archive/team/navigation links.
- HTML article fetch that returns HTTP 403.
- useTranscribe cached YouTube hit.
- useTranscribe SSE `error` event.
- useTranscribe legacy Spotify cached miss.
- Substack podcast page with YouTube embed.
- Substack podcast page with no YouTube embed but transcript section available.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: After a live weekly run, the operator can identify every failed or quiet source from a single run folder.
  target: One run folder is sufficient for diagnosis without terminal scrollback.
  window: Per weekly run.
  target_status: provisional
  target_owner: akshay
- id: SM-2
  metric: A future Codex session can diagnose the latest run failure by reading summary.json and failure_report.md.
  target: No live rerun is required for first-pass diagnosis.
  window: During the first debugging pass after a failed or degraded run.
  target_status: provisional
  target_owner: akshay
- id: SM-3
  metric: Source-adapter fixes add or update regression fixtures instead of relying on repeated live requests.
  target: Every source failure fix references a deterministic fixture or test.
  window: Per source-adapter bug fix.
  target_status: provisional
  target_owner: akshay
- id: SM-4
  metric: No weekly run produces a misleading all-good terminal state when one or more sources failed.
  target: Failed or degraded sources are visible in summary and failure report.
  window: Per weekly run.
  target_status: provisional
  target_owner: akshay
```

- `SM-1`: After a live weekly run, the operator can identify every failed or quiet source from a single run folder.
- `SM-2`: A future Codex session can diagnose the latest run failure by reading `data/runs/<latest>/summary.json` and `failure_report.md`.
- `SM-3`: Source-adapter fixes add or update regression fixtures instead of relying on repeated live requests.
- `SM-4`: No weekly run produces a misleading "all good" terminal state when one or more sources failed.

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/4
- Product intent: `AGENTS.md`
- Source registry: `sources.yaml`
- CLI orchestration: `app/cli.py`
- Discovery adapters: `app/ingest/discovery.py`
- Podcast ingestion: `app/ingest/rss.py`
- Transcript client: `app/ingest/transcript.py`
- State store: `app/store/db.py`
- Artifact helpers: `app/store/files.py`
- Existing tests: `tests/test_discovery.py`, `tests/test_transcript.py`, `tests/test_podcast_ingest.py`
- Artifact policy: `docs/living/project/processes/artifact-commit-policy.md`
- Real extraction workflow: `docs/product-specs/real-sensemaking-extraction-workflow.product-spec.md`

## Execution Notes

- Planned implementation approach:
  - Add `app/observability/` with event models, run context, failure classification, file writers, and report rendering.
  - Thread an optional `RunContext` through CLI orchestration first; avoid invasive adapter rewrites in the first pass.
  - Wrap source-level discovery/ingestion calls in attempt contexts.
  - Wrap stage-level commands in stage contexts.
  - Add small `StateStore` methods for run summaries and attempt summaries.
- Test plan:
  - Start with unit tests for the event/failure models.
  - Add fixture tests for classification and report rendering.
  - Add CLI orchestration tests with monkeypatched source functions.
  - Extend discovery/transcript tests with structured failure assertions once adapters emit attempts.
- Known risks:
  - Passing run context too deeply can make simple adapters noisy. Keep the event API small.
  - Over-classification can become brittle. Unknowns should fall back to `unexpected_failure` with complete error context.
  - Run artifacts can pollute git history. Update artifact policy before committing any live `data/runs/**` outputs.
