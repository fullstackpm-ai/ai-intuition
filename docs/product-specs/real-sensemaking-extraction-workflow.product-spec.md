---
spec_format_version: "0.1"
title: "Real Sensemaking Extraction Workflow"
artifact_type: "prd"
spec_revision: 1
status: accepted
owner: akshay
author: "akshay"
created_at: "2026-07-25T14:51:22Z"
updated_at: "2026-07-25T15:25:00Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/6
applies_to:
  - path: app/llm/extract.py
  - path: app/llm/client.py
  - path: app/llm/synthesize.py
  - path: app/cli.py
  - path: app/models.py
  - path: tests/
---

# Real Sensemaking Extraction Workflow

## Problem

The weekly pipeline can discover, ingest, and normalize current articles and podcast transcripts, but the extraction stage currently defaults to deterministic mock behavior. That means the system is collecting useful source material without actually reading it deeply enough to produce durable mental-model updates.

This creates a misleading operating state: the weekly run appears to complete successfully, raw and normalized artifacts are created, and a brief is generated, but the brief is not a trustworthy synthesis of the week's external sources.

The 2026-W30 run is the motivating example: the pipeline ingested 23 raw artifacts, normalized 32 items, and generated a brief with only 3 accepted insights because extraction still relied on mock/stub behavior rather than real semantic source reading.

## Hypothesis

If the pipeline uses an explicit extraction workflow over normalized artifacts, with structured outputs, evidence, rejection reasons, and quality gates, then weekly briefs will reflect actual source understanding rather than artifact plumbing.

## Product Summary

Weekly runs should no longer silently convert normalized source artifacts into mock-derived briefs. The extraction path should either generate Codex-ready packets for real review or import validated extraction JSON with explicit provenance.

## Scope

```productspec-scope
in:
  - Make extraction mode explicit.
  - Keep deterministic mock extraction for tests and golden fixtures.
  - Support Codex-harness extraction packets for selected artifacts.
  - Support importing validated Codex-authored extracted insight JSON.
  - Record extraction provenance on insights and weekly briefs.
  - Warn when accepted brief insights are mock-derived or legacy-derived.
out:
  - Web dashboard.
  - Automatic publishing or email.
  - Live LLM dependency in the default test suite.
  - Hidden API requirement for weekly runs.
  - Broad prompt-framework dependencies.
cut:
  - Full API-backed extraction implementation.
  - Automatic source ranking.
  - Recommendation or visual feed work.
```

### In

- Make extraction mode explicit.
- Keep deterministic mock extraction for tests and golden fixtures.
- Support Codex-harness extraction packets for selected artifacts.
- Support importing validated Codex-authored extracted insight JSON.
- Record extraction provenance on insights and weekly briefs.
- Warn when accepted brief insights are mock-derived or legacy-derived.

### Out

- Web dashboard.
- Automatic publishing or email.
- Live LLM dependency in the default test suite.
- Hidden API requirement for weekly runs.
- Broad prompt-framework dependencies.

### Cut

- Full API-backed extraction implementation.
- Automatic source ranking.
- Recommendation or visual feed work.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: The extraction command exposes an explicit extraction mode, such as mock, api, or codex_packet, instead of silently defaulting to mock behavior for weekly sensemaking.
- id: AC-2
  criterion: Weekly brief generation records extraction provenance in frontmatter or metadata, including whether accepted insights came from mock, API, manual Codex-harness, or mixed sources.
- id: AC-3
  criterion: A single-artifact command can create a Codex-ready extraction packet containing source metadata, normalized text, schema requirements, quality bar, and output paths.
- id: AC-4
  criterion: A validated extracted insight JSON file can be written or imported for a normalized artifact and upserted into SQLite without rerunning mock extraction.
- id: AC-5
  criterion: Real extraction output must include evidence quotes and source URLs/locations.
- id: AC-6
  criterion: The editor rejects generic summaries and records concrete discard reasons.
- id: AC-7
  criterion: Tests cover mock extraction, imported/manual extraction, schema validation failure, provenance metadata, and brief generation from real/imported insights.
- id: AC-8
  criterion: uv run pytest passes without requiring external LLM credentials.
```

- `AC-1`: The extraction command exposes an explicit extraction mode, such as `mock`, `api`, or `codex_packet`, instead of silently defaulting to mock behavior for weekly sensemaking.
- `AC-2`: Weekly brief generation records extraction provenance in frontmatter or metadata, including whether accepted insights came from mock, API, manual Codex-harness, or mixed sources.
- `AC-3`: A single-artifact command can create a Codex-ready extraction packet containing source metadata, normalized text, schema requirements, quality bar, and output paths.
- `AC-4`: A validated extracted insight JSON file can be written or imported for a normalized artifact and upserted into SQLite without rerunning mock extraction.
- `AC-5`: Real extraction output must include evidence quotes and source URLs/locations.
- `AC-6`: The editor rejects generic summaries and records concrete discard reasons.
- `AC-7`: Tests cover mock extraction, imported/manual extraction, schema validation failure, provenance metadata, and brief generation from real/imported insights.
- `AC-8`: `uv run pytest` passes without requiring external LLM credentials.

## AI Evals

- `EVAL-1`: On the sample OpenAI Codex-agent-loop article, the extraction should produce an insight at the level of: "Agents are managed execution loops, not prompts with tools."
- `EVAL-2`: On a low-signal article, the extractor should reject the item with a specific discard reason rather than producing a generic summary.
- `EVAL-3`: On a podcast transcript, the extractor should identify at most 1-3 durable perspective shifts rather than summarizing the full conversation.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Default weekly runs do not create mock-derived briefs.
  target: run-weekly default stops after Codex extraction packets until real extraction is imported.
  window: Per weekly run.
- id: SM-2
  metric: Accepted insights in generated briefs expose extraction provenance.
  target: Brief metadata identifies codex_packet, api, manual, mock, or legacy provenance counts.
  window: Per generated brief.
- id: SM-3
  metric: Real imported extractions retain source evidence.
  target: Non-rejected real extractions require source URL, evidence, and evidence location.
  window: Per imported extraction.
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/6
- Existing extraction code: `app/llm/extract.py`
- Mock client: `app/llm/client.py`
- Prompt contract: `app/llm/prompts.py`
- Extraction packets: `data/extraction-packets/`
- Weekly brief output: `data/briefs/`
- Current-week evidence: `data/briefs/2026-W30.md`
