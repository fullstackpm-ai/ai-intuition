---
spec_format_version: "0.1"
spec_revision: 1
status: accepted
owner: akshay
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/6
applies_to:
  - app/llm/extract.py
  - app/llm/client.py
  - app/llm/synthesize.py
  - app/cli.py
  - app/models.py
  - tests/
---

# Real Sensemaking Extraction Workflow

## Problem

The weekly pipeline can discover, ingest, and normalize current articles and podcast transcripts, but the extraction stage currently defaults to deterministic mock behavior. That means the system is collecting useful source material without actually reading it deeply enough to produce durable mental-model updates.

This creates a misleading operating state: the weekly run appears to complete successfully, raw and normalized artifacts are created, and a brief is generated, but the brief is not a trustworthy synthesis of the week's external sources.

The 2026-W30 run is the motivating example: the pipeline ingested 23 raw artifacts, normalized 32 items, and generated a brief with only 3 accepted insights because extraction still relied on mock/stub behavior rather than real semantic source reading.

## Hypothesis

If the pipeline uses an explicit extraction workflow over normalized artifacts, with structured outputs, evidence, rejection reasons, and quality gates, then weekly briefs will reflect actual source understanding rather than artifact plumbing.

## Scope

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

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/6
- Existing extraction code: `app/llm/extract.py`
- Mock client: `app/llm/client.py`
- Prompt contract: `app/llm/prompts.py`
- Extraction packets: `data/extraction-packets/`
- Weekly brief output: `data/briefs/`
- Current-week evidence: `data/briefs/2026-W30.md`
