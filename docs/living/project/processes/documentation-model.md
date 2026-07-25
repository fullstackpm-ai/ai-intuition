---
doc_type: living
category: processes
status: current
---

# Documentation Model

This repo uses a scaled-down version of a living versus point-in-time documentation model.

## Rules

- Current operating rules belong in `AGENTS.md` or `docs/living/`.
- Accepted specs, plans, decisions, and retrospectives belong in `docs/point-in-time/`.
- Existing root-level `SPEC.md` is treated as point-in-time product context unless a newer living document explicitly supersedes it.
- Consequential implementation intent should use ProductSpec files under `docs/product-specs/`.
- Generated artifacts under `data/` are pipeline outputs, not docs. Do not reorganize them into `docs/`.
- The living versus point-in-time rubric still governs whether generated artifacts belong in the repo: source captures, normalized inputs, real extraction JSON, and weekly briefs are point-in-time evidence/synthesis; belief files are living knowledge; run diagnostics are issue/spec evidence only when they explain failures; SQLite and regenerable working outputs stay local or are deleted.
- Living docs must be updated when behavior, commands, source policy, or artifact semantics change.
- Point-in-time docs should not be rewritten to match later reality. Add a newer superseding doc instead.
- Do not create heavy team hierarchies, visibility controls, or paired narrative/directive docs unless this repo grows enough to justify them.

## Minimal Metadata

Markdown docs under `docs/` should start with:

```yaml
---
doc_type: living | point-in-time
category: index | knowledge-transfer | runbooks | north-star | processes | specs | decisions | plans
status: current | superseded | accepted | draft
---
```

Keep metadata sparse. Do not duplicate information already obvious from the file path or Git history.

## When To Add A Doc

Add living documentation when:

- A future agent or contributor would otherwise need conversation history to understand the system.
- A pipeline behavior is non-obvious and likely to matter again.
- A source policy affects legality, privacy, paid access, or provenance.
- A product principle should constrain future changes.

Add point-in-time documentation when:

- A decision has tradeoffs worth preserving.
- A plan was accepted and later progress should be judged against it.
- A spec describes intent at a meaningful moment in the project.

Use ProductSpec when a spec is meant to actively govern implementation. See [ProductSpec directive](productspec-directive.md).
