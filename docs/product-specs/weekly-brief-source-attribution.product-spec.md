---
spec_format_version: "0.1"
title: "Weekly Brief Source Attribution"
artifact_type: "prd"
spec_revision: 1
status: proposed
owner: akshay
author: "akshay"
created_at: "2026-07-25T16:29:10Z"
updated_at: "2026-07-25T16:29:10Z"
github_issue: https://github.com/fullstackpm-ai/ai-intuition/issues/7
applies_to:
  - path: app/models.py
  - path: app/llm/extract.py
  - path: app/llm/synthesize.py
  - path: app/cli.py
  - path: app/observability/
  - path: app/store/
  - path: tests/
  - path: data/briefs/
  - path: data/extracted/
---

# Weekly Brief Source Attribution

## Problem

Weekly briefs explain synthesized insights, but they do not make it easy to trace a belief update, mental model, design law, failure mode, or eval pattern back to the source artifact that produced it.

That weakens trust in the repo's core output. A reader should be able to distinguish:

- an insight grounded in one Anthropic Research article
- an insight grounded in one podcast transcript
- a cross-source synthesis derived from multiple artifacts
- an older retained belief that was not updated by the current week's sources

This matters more now that the pipeline supports Codex extraction packets and reviewed extraction imports. Extraction provenance exists at a method level, but final briefs still hide the artifact-level trail.

## Critical Review

The original issue direction is right, but it leaves several implementation decisions underspecified:

- `ExtractedInsight` currently has `source_id`, `source_title`, and `source_url`, but not `source_name`, `source_type`, `published_at`, raw artifact path, or normalized artifact path.
- `NormalizedItem` has `source_id`, title, URL, date, item id, and raw artifact id, but not the human source name or source type that the brief should display.
- `WeeklyBrief.source_rollup` exists, but the renderer does not currently render it as a real `Sources` section.
- The spec needs a deterministic source-reference contract so tests can assert stable `[S1]`, `[S2]` labels.
- The spec needs explicit behavior for missing URLs/dates, legacy extracted insights, and repeated insights from the same artifact.
- The spec needs to say whether source attribution should be stored only in rendered markdown or also in frontmatter. It should be both: frontmatter for machine review, markdown for human review.
- The spec needs observability expectations because brief generation is a pipeline stage.

## Hypothesis

If weekly briefs carry stable insight-level source references and a consolidated `Sources` section, then the brief becomes easier to audit, review, and build on without becoming a citation dump.

The output should preserve the product's core purpose: durable intuition, not source coverage. Sources should support the insight, not become the main content.

## Product Summary

Add structured source attribution to weekly brief generation.

The implementation should preserve source metadata from normalized items and imported extracted insights, build deterministic source references for accepted insights, render compact `[S1]` markers near brief items, and render a bottom `Sources` section with each source artifact listed once.

The weekly brief frontmatter should also include machine-readable source metadata so future tooling can audit briefs without parsing markdown prose.

## Scope

```productspec-scope
in:
  - Add a structured source attribution model for weekly briefs.
  - Preserve enough source metadata through extraction/import for source attribution.
  - Render compact source reference markers in the main brief content.
  - Render a bottom Sources section with deduplicated source artifacts.
  - Include source attribution metadata in weekly brief frontmatter.
  - Support single-source and multi-source insight attribution.
  - Handle missing URL, missing date, and legacy source metadata gracefully.
  - Add observability for source attribution counts and degraded attribution cases.
  - Add deterministic tests for model behavior, import propagation, rendering, frontmatter, dedupe, and missing metadata.
out:
  - Academic citation formatting.
  - Full bibliography management.
  - Per-sentence citations.
  - Source authority ranking.
  - Source graph visualization.
  - Web UI citation cards or browser previews.
  - Automatic semantic deduplication beyond exact source artifact identity.
cut:
  - Recommendation engine based on followed people or sources.
  - Cross-brief source analytics.
  - Retroactive migration of every historical brief.
```

### In

- Add a structured source attribution model for weekly briefs.
- Preserve enough source metadata through extraction/import for source attribution.
- Render compact source reference markers in the main brief content.
- Render a bottom `Sources` section with deduplicated source artifacts.
- Include source attribution metadata in weekly brief frontmatter.
- Support single-source and multi-source insight attribution.
- Handle missing URL, missing date, and legacy source metadata gracefully.
- Add observability for source attribution counts and degraded attribution cases.
- Add deterministic tests for model behavior, import propagation, rendering, frontmatter, dedupe, and missing metadata.

### Out

- Do not implement academic citations, bibliographies, or per-sentence citations.
- Do not rank sources by authority.
- Do not add citation UI, browser previews, or source graph visualization.
- Do not add semantic clustering of equivalent sources beyond exact artifact/source identity.
- Do not add recommendation features.

### Cut

- Cross-brief source analytics.
- Retrofitting every historical brief.
- Any change that requires live source websites, OpenAI credentials, or useTranscribe quota.

## Source Attribution Contract

The implementation should produce a stable source reference object for each unique source artifact used by accepted insights:

```json
{
  "ref_id": "S1",
  "source_id": "anthropic_research",
  "source_name": "Anthropic Research",
  "source_type": "lab_research",
  "item_id": "anthropic_research_2026_07_24_project_pilot",
  "raw_artifact_id": "raw_artifact_id_when_available",
  "title": "Project Pilot: Can AI control a drone?",
  "url": "https://www.anthropic.com/research/...",
  "published_at": "2026-07-24",
  "extraction_methods": ["codex_packet"],
  "insight_ids": ["insight_1", "insight_2"]
}
```

Reference IDs should be assigned deterministically in first-appearance order from rendered accepted insights, not by dictionary/hash order. Repeated insights from the same artifact should reuse the same `ref_id`.

For legacy data, the minimum acceptable fallback is:

- `source_id`
- `source_title`
- `source_url` when present
- `item_id`
- `extraction_method`

Missing optional fields should render as omitted or `unknown`, never as invented metadata.

## Proposed Brief Shape

Main insight sections should stay focused on the idea:

```markdown
1. Stop asking whether the model is safe enough in isolation. Ask which layer owns each reliability property. [S1]
```

When an insight is explicitly synthesized from multiple source artifacts:

```markdown
- The reliability layer is moving from prompt text into product harnesses. [S1, S2]
```

Bottom section:

```markdown
## Sources

- [S1] Anthropic Research - "Project Pilot: Can AI control a drone?" (lab_research, 2026-07-24)
  https://www.anthropic.com/research/...
- [S2] Lenny's Podcast - "Why Netflix is betting on systems thinkers..." (podcast, 2026-07-19)
  https://www.youtube.com/...
```

When URL or date is missing:

```markdown
- [S3] manual - "Prompt Design Principles" (manual, date unknown)
```

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: Accepted extracted insights carry enough structured source metadata to identify source id, item id, title, URL when available, and extraction method.
- id: AC-2
  criterion: Imported Codex/manual extraction preserves or infers source attribution from the normalized item instead of requiring the author to duplicate every source field.
- id: AC-3
  criterion: Weekly brief generation builds deterministic source references in first-appearance order and deduplicates repeated source artifacts.
- id: AC-4
  criterion: Weekly brief frontmatter includes machine-readable source attribution metadata, including source reference IDs, source IDs, item IDs, insight IDs, source counts, and missing-metadata warnings when applicable.
- id: AC-5
  criterion: Weekly brief markdown includes a bottom section titled Sources.
- id: AC-6
  criterion: Single-source brief items render a compact source marker such as [S1] without cluttering the insight text.
- id: AC-7
  criterion: Multi-source brief items can render multiple compact source markers such as [S1, S2] without duplicating full source details inline.
- id: AC-8
  criterion: Missing URL, source name, source type, or publish date does not crash brief generation and does not cause invented metadata.
- id: AC-9
  criterion: Source attribution is observably summarized during brief generation, including number of accepted insights, unique source artifacts, and degraded/missing attribution cases.
- id: AC-10
  criterion: Tests cover single-source attribution, multi-source attribution, source deduplication, missing URL/date handling, frontmatter metadata, import propagation, legacy fallback behavior, and markdown rendering.
- id: AC-11
  criterion: uv run pytest passes and CI remains credential-free.
```

## AI Evals

- `EVAL-1`: Given two extracted insights from the same article, the weekly brief lists that article once in `Sources` and uses the same marker for both insights.
- `EVAL-2`: Given one synthesized design law supported by two artifacts, the design law displays both compact source references and both artifacts appear once in `Sources`.
- `EVAL-3`: Given an imported Codex-harness extraction with a permalink and evidence location, the generated brief preserves the insight, source marker, source URL, and evidence-compatible attribution.
- `EVAL-4`: Given legacy/mock extracted insights with incomplete metadata, the brief remains readable, labels unknown fields honestly, and emits missing-attribution metadata.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Reviewed weekly briefs are auditable from rendered markdown alone.
  target: Every accepted brief item has at least one compact source marker or an explicit retained/legacy marker.
  window: Per generated brief.
  target_status: provisional
  target_owner: akshay
- id: SM-2
  metric: Machine-readable brief metadata supports audit tooling.
  target: Brief frontmatter contains all source references needed to map source IDs to insight IDs without parsing markdown.
  window: Per generated brief.
  target_status: provisional
  target_owner: akshay
- id: SM-3
  metric: Attribution stays quiet enough to preserve readability.
  target: Main brief sections use compact markers; full URLs appear only in the Sources section.
  window: Per generated brief.
  target_status: provisional
  target_owner: akshay
```

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/7
- Real extraction workflow: `docs/product-specs/real-sensemaking-extraction-workflow.product-spec.md`
- Brief generation: `app/llm/synthesize.py`
- Extraction models: `app/models.py`
- Extraction import: `app/llm/extract.py`
- Normalized artifacts: `data/normalized/`
- Brief artifacts: `data/briefs/`
- Existing provenance test: `tests/test_real_extraction_workflow.py`

## Execution Notes

- Prefer adding explicit source reference structures to the model layer instead of deriving everything from markdown at render time.
- Keep source references tied to artifact identity, not only publication source identity; two articles from the same source should get separate refs.
- Use normalized item metadata as the source of truth when importing Codex-authored JSON.
- Do not require users to hand-enter `source_name` or `source_type` in Codex extraction JSON if the normalized item can provide or infer it.
- Do not let source formatting dominate the brief. The primary output is still the belief update.
- Follow the observability directive because this changes brief-generation behavior.
- Add deterministic tests before implementation is claimed complete.
