---
spec_format_version: "0.1"
title: "<Feature Or System Change>"
artifact_type: "prd"
spec_revision: 1
status: draft
owner: akshay
author: "akshay"
created_at: "<ISO-8601 timestamp>"
updated_at: "<ISO-8601 timestamp>"
applies_to:
  - path: app/
  - path: tests/
  - path: sources.yaml
  - path: data/
  - path: docs/
---

# <Feature Or System Change>

## Problem

What pain, ambiguity, or missed capability does this change address?

For this repo, state whether the problem affects:

- source discovery
- ingestion/transcripts
- extraction quality
- belief/topic synthesis
- weekly briefs
- repo operation

## Hypothesis

What causal bet are we making?

Example:

> If podcast ingestion preserves source provenance and timestamps, then extracted insights can cite evidence more reliably without relying on provider summaries.

## Product Summary

What will exist when this is done?

Example:

> The weekly pipeline emits structured source/run diagnostics that future Codex sessions can read before debugging failed sources.

## Scope

```productspec-scope
in:
  - <IN-1>
out:
  - <OUT-1>
cut:
  - <CUT-1>
```

### In

- <IN-1>

### Out

- <OUT-1>

### Cut

- <CUT-1>

## Acceptance Criteria

```productspec-acceptance-criteria
- id: AC-1
  criterion: <Observable build/result criterion.>
- id: AC-2
  criterion: <Observable build/result criterion.>
```

## AI Evals

Use this section only when the change affects model/prompt/extraction behavior.

- `EVAL-1`: <Input, expected behavior, and pass/fail condition.>

## Success Metrics

Post-change indicators. These are not implementation tasks.

```productspec-success-metrics
- id: SM-1
  metric: <Outcome signal to inspect later.>
  target: <target or provisional baseline>
  window: <measurement window>
  target_status: provisional
  target_owner: akshay
```

## Related Artifacts

- GitHub issue: <URL or issue number>
- Living docs: <paths>
- Evidence/input examples: <paths>
- Prior specs/decisions: <paths>

## Execution Notes

- Planned implementation approach:
- Test plan:
- Known risks:
