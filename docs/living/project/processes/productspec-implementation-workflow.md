---
doc_type: living
category: processes
status: current
---

# ProductSpec Implementation Workflow

Use this workflow for consequential repo changes tracked by a `.product-spec.md` file.

## Default Flow

1. Validate the spec:

```bash
npm exec --package @productspec/parser -- productspec validate docs/product-specs/<slug>.product-spec.md
```

2. Generate the Agent Handoff:

```bash
npm exec --package @productspec/parser -- productspec handoff docs/product-specs/<slug>.product-spec.md
```

3. Implement against the handoff and spec:

- Stay within `scope.in`.
- Treat `scope.out` and `scope.cut` as non-goals.
- Map work to `AC-` and `EVAL-` IDs.
- Add or update tests for locally verifiable acceptance criteria.
- If the change touches pipeline behavior, source discovery, ingestion/transcripts, extraction, briefs, belief updates, or artifact layout, wire it into observability and add diagnostics/regression tests.
- If implementation changes intent, stop and revise the spec or create a Decision Trace.

4. Draft an Agent Run receipt:

```bash
npm exec --package @productspec/parser -- productspec init-run docs/product-specs/<slug>.product-spec.md docs/agent-runs/<slug>.agent-run.json
```

5. Update the Agent Run receipt with evidence:

- Test commands and results.
- Changed files or commits.
- Generated artifacts used as evidence.
- Any unchecked post-change success metrics.
- Drift status.

6. Validate the run receipt:

```bash
npm exec --package @productspec/parser -- productspec validate-run docs/agent-runs/<slug>.agent-run.json
```

7. Manually reconcile before reporting completion:

- Every `AC-` has evidence or an explicit deferred reason.
- Every relevant `EVAL-` has evidence or an explicit deferred reason.
- Post-change `SM-` items are marked as provisional or observed.
- Any drift is captured by a spec revision or Decision Trace.

8. Report completion only after reconciliation gaps are understood.

## Repo Maintenance

Use graph when multiple specs are candidates for implementation and file contention matters:

```bash
npm exec --package @productspec/parser -- productspec graph docs/product-specs --json
```

## Local Policy

- Product Specs live in `docs/product-specs/`.
- Agent Run receipts live in `docs/agent-runs/`.
- Decision Traces live in `docs/decision-traces/`.
- GitHub issues may mirror specs, but local specs are the durable execution contract.
- Do not block tiny changes on this workflow. Use it when behavior, data contracts, source ingestion, extraction, briefs, or repo processes change.
