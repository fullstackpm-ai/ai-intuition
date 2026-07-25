# Agent Handoff: Pipeline Observability and Failure Regression Harness

## Build Contract

Implement ProductSpec revision 2.
Source Product Spec: `docs/product-specs/pipeline-observability-and-failure-regression-harness.product-spec.md`.
Satisfy every acceptance criterion before claiming the work is done.
Stay inside scope. If implementation pressure changes product intent, stop and propose a Product Spec update or Decision Trace.

## Product Summary

The weekly pipeline will emit a durable, structured run record that explains what was attempted, what succeeded, what failed, why each failure was classified that way, and which artifacts were written or left unchanged.

The implementation will add a small observability layer around the existing repo-first pipeline. It will not add hosted monitoring, auto-repair, retries, or a dashboard. Its job is to make every weekly run inspectable by a future Codex session and regression-testable by maintainers.

## Scope Guardrails

- In: Create a run observability module with typed models for run metadata, events, source attempts, stage results, and failure classifications.
- In: Create per-run folders under data/runs/<run_id>/.
- In: Write manifest.json, events.jsonl, summary.json, and conditional failure_report.md.
- In: Record per-source discovery and ingestion attempts with outcome and retryability classification.
- In: Record stage-level outcomes for normalize, extract packet, import extraction, edit, brief, and belief update.
- In: Preserve partial success when independent sources fail.
- In: Persist compact run/source/stage summaries in SQLite.
- In: Add deterministic regression tests for common source, transcript, and pipeline failures.
- In: Update artifact policy for data/runs/**.
- Out: Hosted monitoring, dashboards, alerts, email, or push notifications.
- Out: Automatic source repair.
- Out: New retry policy beyond existing library behavior.
- Out: LLM-based diagnosis.
- Out: Live network integration tests.
- Out: Full source adapter rewrite.
- Out: Full OpenTelemetry integration.
- Cut if needed: Retry scheduling.
- Cut if needed: Event-driven weekly automation.
- Cut if needed: Browser UI for run inspection.
- Cut if needed: Source quality scoring beyond outcome/status labels.
- Cut if needed: Historical run analytics beyond compact SQLite summaries.

## Must Satisfy

- AC-1: uv run aic run-weekly creates data/runs/<run_id>/manifest.json, events.jsonl, and summary.json.
- AC-2: manifest.json includes command, args/options, git commit when available, start time, data directory, Python version, extraction mode, and source filter/window when applicable.
- AC-3: events.jsonl contains structured events for run start/finish, stage start/finish, source attempt start/finish, source skip/failure, fallback attempt/result, and artifact write/unchanged.
- AC-4: Every source attempt records source id, source name, source type, lane, adapter, URLs attempted, item count, artifact count, elapsed time, outcome, retryability, and error details when applicable.
- AC-5: Error details include exception class, message, HTTP status when available, provider error code when available, and enough context to reproduce the failing URL/adapter step.
- AC-6: summary.json includes total sources attempted, source outcomes by class, artifact counts by stage, extraction mode, run outcome, and paths to any failure report.
- AC-7: failure_report.md is written when any outcome is not success, healthy_empty, or skipped_config; it groups failures by source/stage and recommends the next diagnostic action.
- AC-8: healthy_empty is not treated as a failure, but is visible in summary.json and the event log.
- AC-9: run-weekly --extraction-mode codex_packet records intentional skips for edit, brief, and belief update without marking the run failed.
- AC-10: A single source failure does not prevent other independent sources from completing, and the partial success is visible in the run summary.
- AC-11: SQLite records compact run summaries and source/stage attempt summaries; verbose event payloads remain file-based.
- AC-12: Pipeline idempotency is preserved. Re-running a weekly job must not duplicate raw, normalized, extracted, rejected, brief, or belief artifacts.
- AC-13: Tests cover event serialization, failure classification, run artifact writing, SQLite persistence, failure report rendering, and partial-success weekly orchestration.
- AC-14: Tests cover representative source failures including HTTP 403, HTTP 429, 404 cached transcript miss, malformed RSS, malformed HTML/no article candidates, useTranscribe SSE error, unsupported Spotify transcription, and Substack transcript fallback.
- AC-15: uv run pytest passes without network access or LLM credentials.

## Suggested Verification

- Verification for AC-1: prove that "uv run aic run-weekly creates data/runs/<run_id>/manifest.json, events.jsonl, and summary.json." is true in the built product.
- Verification for AC-2: prove that "manifest.json includes command, args/options, git commit when available, start time, data directory, Python version, extraction mode, and source filter/window when applicable." is true in the built product.
- Verification for AC-3: prove that "events.jsonl contains structured events for run start/finish, stage start/finish, source attempt start/finish, source skip/failure, fallback attempt/result, and artifact write/unchanged." is true in the built product.
- Verification for AC-4: prove that "Every source attempt records source id, source name, source type, lane, adapter, URLs attempted, item count, artifact count, elapsed time, outcome, retryability, and error details when applicable." is true in the built product.
- Verification for AC-5: prove that "Error details include exception class, message, HTTP status when available, provider error code when available, and enough context to reproduce the failing URL/adapter step." is true in the built product.
- Verification for AC-6: prove that "summary.json includes total sources attempted, source outcomes by class, artifact counts by stage, extraction mode, run outcome, and paths to any failure report." is true in the built product.
- Verification for AC-7: prove that "failure_report.md is written when any outcome is not success, healthy_empty, or skipped_config; it groups failures by source/stage and recommends the next diagnostic action." is true in the built product.
- Verification for AC-8: prove that "healthy_empty is not treated as a failure, but is visible in summary.json and the event log." is true in the built product.
- Verification for AC-9: prove that "run-weekly --extraction-mode codex_packet records intentional skips for edit, brief, and belief update without marking the run failed." is true in the built product.
- Verification for AC-10: prove that "A single source failure does not prevent other independent sources from completing, and the partial success is visible in the run summary." is true in the built product.
- Verification for AC-11: prove that "SQLite records compact run summaries and source/stage attempt summaries; verbose event payloads remain file-based." is true in the built product.
- Verification for AC-12: prove that "Pipeline idempotency is preserved. Re-running a weekly job must not duplicate raw, normalized, extracted, rejected, brief, or belief artifacts." is true in the built product.
- Verification for AC-13: prove that "Tests cover event serialization, failure classification, run artifact writing, SQLite persistence, failure report rendering, and partial-success weekly orchestration." is true in the built product.
- Verification for AC-14: prove that "Tests cover representative source failures including HTTP 403, HTTP 429, 404 cached transcript miss, malformed RSS, malformed HTML/no article candidates, useTranscribe SSE error, unsupported Spotify transcription, and Substack transcript fallback." is true in the built product.
- Verification for AC-15: prove that "uv run pytest passes without network access or LLM credentials." is true in the built product.

## Success Metrics

- SM-1: After a live weekly run, the operator can identify every failed or quiet source from a single run folder. targets One run folder is sufficient for diagnosis without terminal scrollback. over Per weekly run. (provisional).
- SM-2: A future Codex session can diagnose the latest run failure by reading summary.json and failure_report.md. targets No live rerun is required for first-pass diagnosis. over During the first debugging pass after a failed or degraded run. (provisional).
- SM-3: Source-adapter fixes add or update regression fixtures instead of relying on repeated live requests. targets Every source failure fix references a deterministic fixture or test. over Per source-adapter bug fix. (provisional).
- SM-4: No weekly run produces a misleading all-good terminal state when one or more sources failed. targets Failed or degraded sources are visible in summary and failure report. over Per weekly run. (provisional).

## Evidence To Return

- Pull request URL.
- Verification result for each acceptance criterion.
- Eval run result for each AI eval.
- Screenshots or demo link if UI changed.
- Decision Trace if implementation changes product intent.
