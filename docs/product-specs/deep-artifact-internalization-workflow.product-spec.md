---
spec_format_version: "0.1"
title: "Deep Artifact Internalization Workflow"
artifact_type: "prd"
spec_revision: 1
status: proposed
owner: akshay
author: "akshay"
created_at: "2026-07-25T16:24:13Z"
updated_at: "2026-07-25T16:24:13Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/11
applies_to:
  - path: app/cli.py
  - path: app/models.py
  - path: app/llm/prompts.py
  - path: app/llm/extract.py
  - path: app/observability/
  - path: tests/
  - path: data/
  - path: docs/living/project/processes/
---

# Deep Artifact Internalization Workflow

## Problem

The repo can collect raw and normalized artifacts and can produce weekly insight extraction packets, but it does not yet support a deliberate “go deep on this exact subsection” workflow.

That leaves a gap for the project’s real purpose: building durable intuition. A full podcast or long research article often contains one dense section that deserves slow reading, reconstruction, counterargument, and practice. The weekly pipeline is optimized for filtering and synthesis across sources; it is not optimized for fully internalizing one high-value segment.

Example motivating use case:

> Select a raw podcast artifact, choose a 10-20 minute transcript section, and derive a focused mental model, design law, failure mode, drill, and follow-up questions from that subsection without summarizing the whole episode.

## Hypothesis

If a user can select a specific raw or normalized artifact subsection and generate a deep internalization packet, then the system will compound more durable learning than weekly briefs alone because it will preserve the reasoning path from source passage to reusable intuition.

## Product Summary

Add a user-invoked workflow for deep artifact internalization. The workflow should take an existing artifact plus a subsection selector, produce a Codex-ready deep-dive packet, and allow importing a structured internalization output that is stored separately from weekly extraction outputs.

The output should emphasize understanding, reconstruction, and practice:

- what the subsection is really about
- the mechanism or claim being advanced
- what changed in the user’s mental model
- where the claim breaks
- how to test or practice the intuition
- source provenance back to the artifact and subsection

## Scope

```productspec-scope
in:
  - Add a command or workflow for selecting a subsection from a raw or normalized artifact.
  - Support article subsections and podcast transcript sections.
  - Produce a Codex-ready deep internalization packet with source text, provenance, prompts, and expected output schema.
  - Support importing validated Codex-authored internalization JSON or markdown output.
  - Store deep internalization artifacts separately from weekly extraction packets and weekly briefs.
  - Record source artifact path, source URL when available, subsection locator, and evidence references.
  - Add observability events for packet creation, import, validation failure, and artifact writes.
  - Add deterministic tests for subsection selection, packet generation, schema validation, import, and observability.
out:
  - Automatic choice of which subsection is worth studying.
  - Automatic LLM/API extraction as the default path.
  - Web reading interface or dashboard.
  - Spaced-repetition scheduling.
  - Recommendation systems based on followed people.
  - Replacing the weekly brief workflow.
cut:
  - Multimedia clipping or audio playback.
  - Full knowledge graph construction.
  - Cross-artifact perspective synthesis.
  - User accounts or personalization.
```

### In

- Add a command or workflow for selecting a subsection from a raw or normalized artifact.
- Support article subsections and podcast transcript sections.
- Produce a Codex-ready deep internalization packet with source text, provenance, prompts, and expected output schema.
- Support importing validated Codex-authored internalization JSON or markdown output.
- Store deep internalization artifacts separately from weekly extraction packets and weekly briefs.
- Record source artifact path, source URL when available, subsection locator, and evidence references.
- Add observability events for packet creation, import, validation failure, and artifact writes.
- Add deterministic tests for subsection selection, packet generation, schema validation, import, and observability.

### Out

- Do not make the system automatically decide which subsection to study.
- Do not require OpenAI API credentials, useTranscribe calls, or live source fetching for the default workflow.
- Do not add a web dashboard or reading UI.
- Do not add spaced repetition or recommendation logic.
- Do not change the weekly brief pipeline except to keep artifact semantics compatible.

### Cut

- Audio/video clipping.
- Full knowledge graph construction.
- Cross-artifact synthesis.
- User accounts, preferences, or social/recommendation features.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: A user can invoke a command with an existing artifact path or artifact id and a subsection selector to create a deep internalization packet.
- id: AC-2
  criterion: The subsection selector supports at least one article-oriented mode, such as heading or character range, and one podcast-oriented mode, such as timestamp range or transcript segment range.
- id: AC-3
  criterion: The generated packet includes source metadata, raw or normalized source provenance, subsection locator, selected source text, quality bar, prompt instructions, and expected output schema.
- id: AC-4
  criterion: The deep internalization output schema captures mechanism, intuition update, mental model, design law or failure mode, boundary conditions, counterargument, evidence, internalization drill, and follow-up questions.
- id: AC-5
  criterion: A validated Codex-authored internalization output can be imported and stored without being mixed into weekly extraction outputs unless explicitly promoted later.
- id: AC-6
  criterion: Invalid subsection selectors or missing artifact paths fail with actionable errors and are recorded in observability events.
- id: AC-7
  criterion: Packet creation and import emit observability events for attempts, validation outcomes, and artifact write paths.
- id: AC-8
  criterion: Tests cover article subsection selection, podcast transcript range selection, packet rendering, valid import, invalid import, invalid selector diagnostics, and observability.
- id: AC-9
  criterion: uv run pytest passes without requiring network access, OpenAI credentials, useTranscribe quota, or live source websites.
```

## AI Evals

- `EVAL-1`: Given a 10-20 minute podcast transcript section, the internalization output should not summarize the full episode; it should derive one to three durable perspective shifts anchored to timestamped evidence.
- `EVAL-2`: Given a dense article subsection, the output should reconstruct the underlying mechanism and identify at least one boundary condition or counterargument.
- `EVAL-3`: Given a low-signal subsection, the output should say what is missing and either reject the section or produce only a narrow claim with low confidence.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Deep-dive outputs are source-grounded rather than generic summaries.
  target: Reviewed outputs include evidence references and a concrete mental-model update.
  window: Per internalization artifact.
  target_status: provisional
  target_owner: akshay
- id: SM-2
  metric: The workflow supports deliberate study without polluting weekly artifacts.
  target: Deep internalization artifacts are stored outside data/extraction-packets and data/briefs unless explicitly promoted.
  window: Per run.
  target_status: provisional
  target_owner: akshay
- id: SM-3
  metric: Failures are diagnosable.
  target: Invalid selector/import failures include source path, selector, failure class, and suggested fix.
  window: Per failure.
  target_status: provisional
  target_owner: akshay
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/11
- Real extraction spec: `docs/product-specs/real-sensemaking-extraction-workflow.product-spec.md`
- Artifact retention policy: `docs/product-specs/weekly-run-artifact-retention-and-promotion-policy.product-spec.md`
- Observability directive: `docs/product-specs/pipeline-observability-and-failure-regression-harness.product-spec.md`
- Existing extraction packets: `data/extraction-packets/`
- Example podcast artifacts: `data/raw/podcasts/`, `data/normalized/`

## Execution Notes

- Treat this as a user-directed study workflow, not an automated weekly run stage.
- Prefer using normalized markdown when available, but preserve the original raw artifact path and source URL as provenance.
- For podcast transcripts, preserve timestamps in the selected subsection whenever the source artifact provides them.
- Store outputs under a separate path such as `data/internalizations/` or `data/deep-dives/`; the implementation should choose the name that best fits existing artifact policy.
- Follow the observability directive for any new command, import path, validation error, or artifact write.
- Add tests before claiming completion; this workflow must remain deterministic and credential-free by default.
