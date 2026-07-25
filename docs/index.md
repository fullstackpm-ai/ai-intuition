---
doc_type: living
category: index
status: current
---

# Documentation Index

This repo uses a lightweight documentation model.

The goal is to preserve historical intent without confusing it with current operating rules.

## Document Classes

- Living documentation describes current reality: how the system works, how to operate it, and what new work should follow.
- Point-in-time documentation captures a decision, spec, plan, or snapshot as it was understood when written.
- Generated knowledge artifacts are pipeline outputs under `data/`. They are versioned evidence and synthesis artifacts, not documentation.

## Authority

When documents conflict, use this order:

1. `AGENTS.md`
2. Living documentation under `docs/living/`
3. Point-in-time documentation under `docs/point-in-time/` and legacy root specs such as `SPEC.md`
4. Generated artifacts under `data/`

`AGENTS.md` remains the concise agent-facing rulebook. Living docs can explain those rules in more detail.

## Navigation

- [Living documentation](living/index.md)
- [Point-in-time documentation](point-in-time/index.md)
- [Product Specs](product-specs/index.md)
- [Agent Runs](agent-runs/index.md)
- [Decision Traces](decision-traces/index.md)
