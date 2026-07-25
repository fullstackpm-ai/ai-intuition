---
doc_type: living
category: processes
status: current
---

# Artifact Commit Policy

This repo is intentionally repo-first, but not every generated artifact should be committed.

The limiting factor is not GitHub Free storage or line-count limits. The limiting factor is knowledge hygiene: commits should preserve source evidence and real synthesis, not mock-derived outputs that make the history look more meaningful than it is.

## Commit Decision Table

| Path | Default decision | Reason |
| --- | --- | --- |
| `data/raw/**` | Commit when the run is intended to become part of the durable evidence archive. | Raw source artifacts are provenance and evidence. |
| `data/normalized/**` | Commit when paired with committed raw artifacts or when needed for Codex extraction review. | Normalized artifacts are reproducible derived inputs for extraction. |
| `data/extraction-packets/**` | Commit only when they are deliberate review packets, fixtures, or examples. | Packets are working artifacts; most can be regenerated. |
| `data/extracted/**` | Commit only when extraction provenance is `codex_packet`, `api`, or reviewed `manual`. | Mock/legacy extracted JSON pollutes the knowledge history. |
| `data/rejected/**` | Commit only when the rejection is from real reviewed extraction and is useful evidence. | Mock/legacy rejected JSON is mostly pipeline noise. |
| `data/briefs/**` | Commit only when the brief is based on real/reviewed extraction provenance. | Mock-derived or questionable briefs should not become durable synthesis. |
| `data/beliefs/**` | Commit after reviewing that updates came from real accepted insights. | Belief files are the durable knowledge layer. |
| `data/state.sqlite3` | Do not commit. | SQLite is local index/idempotency state, not durable knowledge. |

## Deterministic Rules

1. Do not commit `data/extracted/**`, `data/rejected/**`, or `data/briefs/**` when their accepted insight provenance includes `mock` or `legacy`, unless the file is explicitly a test fixture.
2. Do not commit generated briefs that the operator has not reviewed as real synthesis.
3. Prefer committing raw and normalized artifacts together; avoid committing normalized artifacts without their raw source unless they are fixtures.
4. Keep code/docs/tests commits separate from weekly run artifact commits unless the user explicitly asks for one combined snapshot.
5. Do not let generated artifact volume decide the policy by itself. Size matters only when files are unusually large; semantics decide first.
6. If an artifact is needed only to reproduce a bug, put it in a fixture path or reference it in a ProductSpec/issue instead of treating it as durable knowledge.

## Weekly Run Recommendation

For a normal weekly run:

1. Commit `data/raw/**` and `data/normalized/**` only if the sourced material should be preserved for later extraction.
2. Generate or commit `data/extraction-packets/**` only for selected artifacts that need Codex review.
3. Import Codex-authored or API-authored extraction JSON with explicit provenance.
4. Commit `data/extracted/**`, `data/rejected/**`, `data/briefs/**`, and `data/beliefs/**` only after real extraction and review.

This keeps the repository useful as a compounding knowledge archive instead of a dump of pipeline byproducts.
