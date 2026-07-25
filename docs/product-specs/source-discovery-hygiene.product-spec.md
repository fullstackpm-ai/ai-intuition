---
spec_format_version: "0.1"
title: "Source Discovery Hygiene"
artifact_type: "prd"
spec_revision: 1
status: accepted
owner: akshay
author: "akshay"
created_at: "2026-07-25T06:00:00Z"
updated_at: "2026-07-25T15:25:00Z"
applies_to:
  - path: app/ingest/discovery.py
  - path: sources.yaml
  - path: tests/test_discovery.py
---

# Source Discovery Hygiene

## Problem

Several configured source adapters discover noisy pages that should not enter the weekly pipeline:

- team/index/archive pages from Anthropic
- generic research or publication pages from Google DeepMind
- RSS/archive pages from Google Research
- blocked OpenAI Research HTML fetches

The weekly pipeline should spend extraction effort on article/post candidates, not source navigation pages.

## Hypothesis

If discovery uses source-specific filters or adapters when generic HTML discovery is too noisy, then the weekly pipeline will ingest fewer irrelevant artifacts while preserving enough source coverage for high-signal insights.

## Product Summary

Configured lab and research source discovery should return article/post candidates instead of navigation, archive, team, feed, or generic landing pages.

## Scope

```productspec-scope
in:
  - Improve discovery hygiene for configured lab/research sources.
  - Filter team pages, archive pages, RSS pages, generic landing pages, and non-article research pages.
  - Preserve publish dates when available.
  - Add source-specific adapter behavior where generic HTML discovery is insufficient.
  - Document any source that remains blocked and choose a fallback path.
out:
  - Adding new deferred sources.
  - Browser automation scraping.
  - Bypassing access controls.
  - Solving extraction/editing quality beyond discovery input quality.
cut:
  - Full semantic ranking of discovered items.
  - General-purpose crawler behavior.
```

### In

- Improve discovery hygiene for configured lab/research sources.
- Filter team pages, archive pages, RSS pages, generic landing pages, and non-article research pages.
- Preserve publish dates when available.
- Add source-specific adapter behavior where generic HTML discovery is insufficient.
- Document any source that remains blocked and choose a fallback path.

### Out

- Adding new deferred sources.
- Browser automation scraping.
- Bypassing access controls.
- Solving extraction/editing quality beyond discovery input quality.

### Cut

- Full semantic ranking of discovered items.
- General-purpose crawler behavior.

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: uv run aic discover --since 7d --limit 5 has materially less noise for the issue #2 sources.
- id: AC-2
  criterion: Source discovery returns article/post items, not team pages, archive pages, feed pages, or generic landing pages.
- id: AC-3
  criterion: Publish dates are extracted when available.
- id: AC-4
  criterion: Any source that remains blocked has an explicit documented reason and fallback path.
- id: AC-5
  criterion: Focused tests cover parser/filter rules for each changed adapter.
- id: AC-6
  criterion: uv run pytest passes.
```

- `AC-1`: `uv run aic discover --since 7d --limit 5` has materially less noise for the issue #2 sources.
- `AC-2`: Source discovery returns article/post items, not team pages, archive pages, feed pages, or generic landing pages.
- `AC-3`: Publish dates are extracted when available.
- `AC-4`: Any source that remains blocked has an explicit documented reason and fallback path.
- `AC-5`: Focused tests cover parser/filter rules for each changed adapter.
- `AC-6`: `uv run pytest` passes.

## AI Evals

- `EVAL-1`: Discovery output for each cleaned source should classify candidate URLs as keep/reject with reasons that align with the source admission rule.

## Success Metrics

```productspec-success-metrics
- id: SM-1
  metric: Weekly runs produce fewer rejected/noisy raw artifacts from lab/research sources.
  target: Less review time spent cleaning source noise.
  window: Per weekly run.
- id: SM-2
  metric: Manual review effort shifts from cleaning source noise to judging actual insights.
  target: Most reviewed artifacts are source articles/posts rather than navigation pages.
  window: Per weekly review.
```

- `SM-1`: Weekly runs produce fewer rejected/noisy raw artifacts from lab/research sources.
- `SM-2`: Manual review effort shifts from cleaning source noise to judging actual insights.

## Related Artifacts

- GitHub issue: https://github.com/fullstackpm-ai/ai-intuition/issues/2
- Source registry: `sources.yaml`
- Discovery code: `app/ingest/discovery.py`
- Discovery tests: `tests/test_discovery.py`
- Product direction: `docs/living/project/north-star/compounding-knowledge-system.md`
