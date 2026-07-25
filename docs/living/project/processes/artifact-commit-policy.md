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
| `data/raw/**` | Commit by default, unless superseded by an existing same-item capture. | Raw source artifacts are point-in-time provenance and evidence. |
| `data/normalized/**` | Commit by default with paired raw artifacts, unless superseded. | Normalized artifacts are point-in-time extraction inputs. |
| `data/extraction-packets/**` | Delete by default after the run. | Bulk packets are regenerable working artifacts; commit only deliberately selected fixtures or review packets. |
| `data/extracted/**` | Commit when extraction provenance is `codex_packet`, `api`, or reviewed `manual`; delete mock/legacy. | Real extracted JSON is reviewed knowledge; mock/legacy JSON pollutes history. |
| `data/rejected/**` | Commit when rejection provenance is real and useful; delete mock/legacy. | Real reviewed rejection can be evidence; mock/legacy rejected JSON is mostly pipeline noise. |
| `data/briefs/**` | Commit when based on real/reviewed extraction provenance; delete missing/mock/legacy provenance. | Weekly briefs are point-in-time synthesis only when source-grounded. |
| `data/beliefs/**` | Commit by default after review. | Belief files are the living knowledge layer. |
| `data/runs/**` | Attach to issue/spec when degraded; otherwise keep local. | Run diagnostics are operational evidence, not durable knowledge by default. |
| `data/state.sqlite3` | Keep local. | SQLite is local index/idempotency state, not durable knowledge. |

## Retention Decision Model

For every weekly artifact, the classifier decides two things in order:

1. **Should this be retained in the repo at all?**
   - Retain point-in-time evidence: raw captures, normalized extraction inputs, real extracted/rejected JSON, and source-grounded weekly briefs.
   - Retain living knowledge: belief files that represent current reviewed understanding.
   - Retain diagnostics only when they explain a degraded run, validate a regression fix, or document an operational incident.
   - Do not retain local idempotency state, regenerated working output, mock/legacy synthesis, or unreviewed summaries.
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

The report is dry-run only. It recommends `commit`, `review`, `keep-local`, `attach-to-issue`, or `delete`; it never deletes files automatically. Treat `review` as an exception path for ambiguity, not the normal output.

## Deterministic Rules

1. Do not commit `data/extracted/**`, `data/rejected/**`, or `data/briefs/**` when their accepted insight provenance includes `mock` or `legacy`, unless the file is explicitly a test fixture.
2. Do not commit generated briefs that the operator has not reviewed as real synthesis.
3. Commit raw and normalized artifacts together; avoid committing normalized artifacts without their raw source unless they are fixtures.
4. Keep code/docs/tests commits separate from weekly run artifact commits unless the user explicitly asks for one combined snapshot.
5. Do not let generated artifact volume decide the policy by itself. Size matters only when files are unusually large; semantics decide first.
6. If an artifact is needed only to reproduce a bug, put it in a fixture path or reference it in a ProductSpec/issue instead of treating it as durable knowledge.
7. Do not commit `data/runs/**` by default after a normal weekly run. Commit a run folder only when it explains a bug, validates a regression fix, or documents an important operational incident.
8. If rerunning the same week creates same-title artifacts with different content hashes and an existing retained sibling exists, delete the untracked regenerated duplicate unless there is a deliberate reason to preserve a new point-in-time capture.

## Weekly Run Recommendation

For a normal weekly run:

1. Run `uv run aic artifact-report`.
2. Commit `data/raw/**` and `data/normalized/**` entries recommended as `commit`; they are point-in-time evidence.
3. Delete bulk `data/extraction-packets/**` entries recommended as `delete`; regenerate them later from normalized files when needed.
4. Import Codex-authored or API-authored extraction JSON with explicit provenance.
5. Commit `data/extracted/**`, `data/rejected/**`, `data/briefs/**`, and `data/beliefs/**` when the classifier confirms real provenance or living-knowledge status.
6. Keep ordinary `data/runs/**` locally. Attach or commit run diagnostics only when the classifier says `attach-to-issue`.

This keeps the repository useful as a compounding knowledge archive instead of a dump of pipeline byproducts.
