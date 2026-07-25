---
spec_format_version: "0.1"
title: "OpenAI Research Discovery Fallback"
artifact_type: "prd"
spec_revision: 1
status: accepted
owner: akshay
author: "Codex"
created_at: "2026-07-25T23:00:00Z"
updated_at: "2026-07-25T23:20:00Z"
applies_to:
  - path: app/ingest/discovery.py
  - path: app/cli.py
  - path: sources.yaml
  - path: tests/test_discovery.py
  - path: tests/test_observability.py
---

# OpenAI Research Discovery Fallback

## Problem

`openai_research` currently fetches `https://openai.com/news/research/` as an HTML index. The 2026-W30 run received HTTP 403 before it could discover candidates. Issue #8 fixed blocked *OpenAI News article* fetches, not Research discovery.

Investigation found that the official `https://openai.com/news/rss.xml` feed is reachable to the pipeline client and exposes first-party entry tags. It currently contains 193 entries tagged `Research`. The official Research Index is also blocked to the pipeline client, so it is not a usable runtime path.

This affects source discovery, weekly-run coverage, and observability. The solution must not bypass access controls or silently admit generic News items.

## Hypothesis

If `openai_research` uses the official News RSS feed and admits only entries whose category metadata includes `Research`, then weekly runs recover Research coverage without accessing the blocked HTML index.

## Product Summary

`openai_research` uses a deterministic, source-specific RSS adapter. It records the selected feed, outcome, category-filter result, and candidate count, and emits only dated Research-tagged OpenAI entries that satisfy existing title and URL admission rules.

## Scope

```productspec-scope
in:
  - Replace the blocked OpenAI Research HTML-index path with the validated official News RSS feed.
  - Add a deterministic source-specific Research-tag filter.
  - Preserve existing OpenAI title/date and URL admission rules.
  - Record the selected RSS path, category-filter result, candidate count, and failure reason in run diagnostics.
  - Add regression tests for Research-tag filtering, malformed RSS, and RSS failure.
out:
  - Bypassing Cloudflare, authentication, robots rules, or access controls.
  - Browser automation, cookies, or authenticated scraping.
  - Changing OpenAI News item-fetch behavior from Issue #8.
  - Broad changes to unrelated source adapters.
cut:
  - LLM-based source classification.
  - Third-party news aggregators.
  - General-purpose multi-site fallback infrastructure.
```

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: openai_research uses https://openai.com/news/rss.xml through an explicit source-specific adapter and does not fetch the blocked HTML index during normal discovery.
- id: AC-2
  criterion: The adapter emits only dated feed entries whose first-party category metadata includes Research.
- id: AC-3
  criterion: Discovered candidates retain OpenAI Research title cleanup, URL filtering, publication dates, and RSS provenance.
- id: AC-4
  criterion: Run diagnostics record the selected RSS path, response outcome, category-filter result, candidate count, and terminal failure reason when the feed is unavailable.
- id: AC-5
  criterion: A malformed or unavailable official feed marks the source degraded with operator-action guidance and makes no unauthorized retry or bypass attempt.
- id: AC-6
  criterion: Fixture tests cover Research-tag filtering, non-Research exclusion, malformed RSS, and RSS failure.
- id: AC-7
  criterion: uv run pytest passes locally and in CI.
```

## AI Evals

- `EVAL-1`: Given an official RSS payload containing Research and generic News entries, deterministic admission retains only dated Research entries and preserves title/date provenance.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Weekly runs with official RSS entries tagged Research produce at least one admissible openai_research candidate.
  target: 100% of eligible weekly runs
  window: Four weekly runs
  target_status: provisional
  target_owner: akshay
- id: SM-2
  metric: OpenAI Research source attempts ending in blocked_auth from the retired HTML-index path.
  target: 0
  window: Every weekly run
  target_status: provisional
  target_owner: akshay
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/13
- Prior spec: `docs/product-specs/source-discovery-hygiene.product-spec.md`
- Source configuration: `sources.yaml`
- Discovery implementation: `app/ingest/discovery.py`
- Live evidence: `data/runs/20260725T155223Z-run-weekly-c6d2c2/failure_report.md`
- Existing OpenAI News fix: Issue #8

## Execution Notes

- Planned implementation approach: configure the official RSS feed and add a source-specific adapter that filters entry categories before applying the current title/date rules. Do not call the retired blocked index.
- Test plan: fixture tests for category filtering and RSS failure observability; live `aic discover --source openai_research` validation; full suite and CI.
- Known risks: the feed category schema may change. The adapter must fail observably rather than silently admitting generic News entries.
