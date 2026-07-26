---
spec_format_version: "0.1"
title: "Historical Weekly Replay"
artifact_type: "prd"
spec_revision: 1
status: accepted
owner: akshay
author: "Codex"
created_at: "2026-07-25T23:30:00Z"
updated_at: "2026-07-25T23:40:00Z"
applies_to:
  - path: app/time.py
  - path: app/cli.py
  - path: tests/test_observability.py
  - path: tests/test_time.py
---

# Historical Weekly Replay

## Problem

`aic run-weekly` always derives its window from the current local week. A request to replay an earlier week silently fetches current material instead of the intended historical corpus. The CLI has no bounded historical mode, and its diagnostics do not record a target ISO week.

## Hypothesis

If `run-weekly` accepts a validated `--week YYYY-Www` option and uses the exact local-week start plus next-week boundary for discovery, operators can replay an earlier weekly corpus without admitting newer source items or changing normal current-week behavior.

## Product Summary

Add a deterministic historical-week option to the weekly run. The command records the target week and exact discovery window in its run manifest, preserves all existing quality gates and extraction modes, and rejects invalid or future weeks.

## Scope

```productspec-scope
in:
  - Add validated ISO-week parsing and local-week bounds.
  - Add `run-weekly --week YYYY-Www`.
  - Pass both the historical start and end boundary into discovery and ingest.
  - Record target week and bounded window in run diagnostics.
  - Add deterministic tests for the boundary and CLI orchestration.
out:
  - Replaying a prior run from a saved manifest.
  - Changing source-specific historical availability or RSS retention.
  - Automatic LLM extraction or automatic generation of a historical brief in Codex-packet mode.
  - Changing current-week default behavior.
cut:
  - Backfill scheduling.
  - Timezone configuration beyond the existing America/Los_Angeles convention.
```

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: `aic run-weekly --week 2026-W29` uses a bounded local discovery window beginning Monday July 13, 2026 and ending before Monday July 20, 2026.
- id: AC-2
  criterion: The target week and both window boundaries are present in the run manifest/options and source discovery receives the same boundaries.
- id: AC-3
  criterion: Invalid ISO weeks and weeks after the current week fail before any source fetch.
- id: AC-4
  criterion: Omitting `--week` preserves the current-week behavior and diagnostics contract.
- id: AC-5
  criterion: Existing quality gates, source attempts, and Codex packet behavior remain unchanged for historical runs.
- id: AC-6
  criterion: Focused regression tests and the full pytest suite pass.
```

## AI Evals

- `EVAL-1`: Given dated discovery candidates on either side of the W29 end boundary, only candidates published during W29 are admitted.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Operator can identify the exact target week and source window from one historical run manifest.
  target: 100% of historical runs
  window: Four historical replays
  target_status: provisional
  target_owner: akshay
```

## Related Artifacts

- Weekly runner: `app/cli.py`
- Discovery window: `app/ingest/discovery.py`
- Time utilities: `app/time.py`
- Observability tests: `tests/test_observability.py`
