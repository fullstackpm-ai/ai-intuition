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
| `data/runs/**` | Commit only when needed as bug evidence, regression fixtures, or spec examples. | Run diagnostics are operational evidence; most live run folders are reproducible or ephemeral. |
| `data/state.sqlite3` | Do not commit. | SQLite is local index/idempotency state, not durable knowledge. |

## Retention Decision Model

For every weekly artifact, decide two things in order:

1. **Should this be retained in the repo at all?**
   - Retain when it is durable source evidence, selected review input, reviewed knowledge, or diagnostic evidence attached to a bug/spec.
   - Do not retain when it is local idempotency state, regenerated working output, mock/legacy synthesis, or an unreviewed summary.
2. **If retained, how should it be organized?**
   - `evidence`: source captures and normalized inputs that preserve provenance for future extraction.
   - `review-packet`: selected Codex extraction packets that should be reviewed or reused as fixtures.
   - `reviewed-knowledge`: real extracted JSON, accepted briefs, and belief updates after human or Codex review.
   - `diagnostic`: run folders or fixtures that explain a failure, validate a regression fix, or document an operational incident.
   - `retained-local`: useful local state that should remain on disk but not enter git.
   - `disposable`: generated output that should be deleted after review because it would pollute knowledge history.

Run the classifier before deciding what to stage:

```bash
uv run aic artifact-report
uv run aic artifact-report --json
```

The report is dry-run only. It recommends `commit`, `review`, `keep-local`, `attach-to-issue`, or `delete`; it never deletes files automatically.

## Deterministic Rules

1. Do not commit `data/extracted/**`, `data/rejected/**`, or `data/briefs/**` when their accepted insight provenance includes `mock` or `legacy`, unless the file is explicitly a test fixture.
2. Do not commit generated briefs that the operator has not reviewed as real synthesis.
3. Prefer committing raw and normalized artifacts together; avoid committing normalized artifacts without their raw source unless they are fixtures.
4. Keep code/docs/tests commits separate from weekly run artifact commits unless the user explicitly asks for one combined snapshot.
5. Do not let generated artifact volume decide the policy by itself. Size matters only when files are unusually large; semantics decide first.
6. If an artifact is needed only to reproduce a bug, put it in a fixture path or reference it in a ProductSpec/issue instead of treating it as durable knowledge.
7. Do not commit `data/runs/**` by default after a normal weekly run. Commit a run folder only when it explains a bug, validates a regression fix, or documents an important operational incident.
8. If rerunning the same week creates same-title artifacts with different content hashes, treat them as possible superseded siblings and review before promoting either version.

## Weekly Run Recommendation

For a normal weekly run:

1. Run `uv run aic artifact-report`.
2. Review `data/raw/**` and `data/normalized/**` as evidence candidates. Commit only the material that should be preserved for later extraction.
3. Review `data/extraction-packets/**` as review-packet candidates. Commit only selected packets that need Codex review or fixture value.
4. Import Codex-authored or API-authored extraction JSON with explicit provenance.
5. Commit `data/extracted/**`, `data/rejected/**`, `data/briefs/**`, and `data/beliefs/**` only after real extraction and review.
6. Keep ordinary `data/runs/**` locally. Attach or commit run diagnostics only when they explain a GitHub issue, ProductSpec, regression fixture, or operational incident.

This keeps the repository useful as a compounding knowledge archive instead of a dump of pipeline byproducts.
