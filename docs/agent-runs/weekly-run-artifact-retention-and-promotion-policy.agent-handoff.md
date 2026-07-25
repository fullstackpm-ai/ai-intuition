# Agent Handoff: Weekly Run Artifact Retention and Promotion Policy

## Build Contract

Implement ProductSpec revision 1.
Source Product Spec: `docs/product-specs/weekly-run-artifact-retention-and-promotion-policy.product-spec.md`.
Satisfy every acceptance criterion before claiming the work is done.
Stay inside scope. If implementation pressure changes product intent, stop and propose a Product Spec update or Decision Trace.

## Product Summary

The project should have an explicit weekly artifact lifecycle: generated artifacts start as working output, then the system should first decide whether each artifact deserves repo retention at all. Only retained artifacts should then be organized as evidence, review packets, reviewed knowledge, or diagnostic evidence. Non-retained artifacts should remain local only or be deleted after operator review.

The output of this spec should be a policy and, if needed, CLI support that answers after each weekly run:

- What changed?
- Does each artifact need to be kept in the repo?
- If yes, what role should it play in the repo?
- Which artifacts are safe to stage after review?
- Which artifacts should be reviewed before commit?
- Which artifacts should be deleted?
- Which artifacts are diagnostic evidence for an issue?
- Which artifacts are durable knowledge?

## Scope Guardrails

- In: Define artifact lifecycle states for weekly run outputs.
- In: Define commit/delete/promote rules for raw, normalized, extraction packets, extracted JSON, rejected JSON, briefs, beliefs, run diagnostics, and SQLite state.
- In: Make the retention decision explicit before organization: keep-in-repo, keep-local, attach-to-issue, or delete.
- In: Decide whether run diagnostics should be committed by default, attached to issues, or kept local.
- In: Add a CLI command or dry-run report that classifies current uncommitted weekly artifacts by recommended action.
- In: Ensure summarized artifacts such as briefs are committed only when based on real/reviewed extraction provenance.
- In: Add tests for artifact classification and policy enforcement.
- In: Update artifact commit policy and AGENTS guidance.
- Out: Cloud artifact storage.
- Out: Database-backed artifact repository.
- Out: Web UI for artifact review.
- Out: Automatic deletion without an explicit operator action.
- Out: Automatic insight extraction or synthesis quality review.
- Cut if needed: Long-term archive compression.
- Cut if needed: Per-source retention tuning beyond defaults.
- Cut if needed: Git LFS or external blob storage.

## Must Satisfy

- AC-1: The repo has a documented lifecycle model for weekly artifacts, including working, evidence, review-packet, reviewed-knowledge, diagnostic, and disposable states.
- AC-2: Each major data path has a deterministic default action: data/raw, data/normalized, data/extraction-packets, data/extracted, data/rejected, data/briefs, data/beliefs, data/runs, and data/state.sqlite3.
- AC-3: A post-run command or report can classify uncommitted artifacts into commit, review, keep-local, attach-to-issue, or delete recommendations.
- AC-4: The policy distinguishes raw evidence from summarized knowledge and prevents unreviewed/mock summaries from being recommended as durable knowledge.
- AC-5: Run diagnostics are retained or promoted only when they explain failures, validate a regression fix, or document an operational incident.
- AC-6: Rerunning the same week does not make stale artifacts look current; superseded artifacts are identified or recommended for cleanup.
- AC-7: Tests cover classification for raw/normalized artifacts, extraction packets, real extracted JSON, mock extracted JSON, briefs, belief files, run diagnostics, and SQLite state.
- AC-8: Observability events or run summaries capture enough metadata for the post-run artifact report to explain why a recommendation was made.
- AC-9: uv run pytest passes.

## Suggested Verification

- Verification for AC-1: prove that "The repo has a documented lifecycle model for weekly artifacts, including working, evidence, review-packet, reviewed-knowledge, diagnostic, and disposable states." is true in the built product.
- Verification for AC-2: prove that "Each major data path has a deterministic default action: data/raw, data/normalized, data/extraction-packets, data/extracted, data/rejected, data/briefs, data/beliefs, data/runs, and data/state.sqlite3." is true in the built product.
- Verification for AC-3: prove that "A post-run command or report can classify uncommitted artifacts into commit, review, keep-local, attach-to-issue, or delete recommendations." is true in the built product.
- Verification for AC-4: prove that "The policy distinguishes raw evidence from summarized knowledge and prevents unreviewed/mock summaries from being recommended as durable knowledge." is true in the built product.
- Verification for AC-5: prove that "Run diagnostics are retained or promoted only when they explain failures, validate a regression fix, or document an operational incident." is true in the built product.
- Verification for AC-6: prove that "Rerunning the same week does not make stale artifacts look current; superseded artifacts are identified or recommended for cleanup." is true in the built product.
- Verification for AC-7: prove that "Tests cover classification for raw/normalized artifacts, extraction packets, real extracted JSON, mock extracted JSON, briefs, belief files, run diagnostics, and SQLite state." is true in the built product.
- Verification for AC-8: prove that "Observability events or run summaries capture enough metadata for the post-run artifact report to explain why a recommendation was made." is true in the built product.
- Verification for AC-9: prove that "uv run pytest passes." is true in the built product.

## Success Metrics

- SM-1: After a weekly run, the operator can decide what to commit or delete from a single artifact report. targets No manual scan of all generated data paths is required for first-pass cleanup. over Per weekly run. (committed).
- SM-2: Durable knowledge commits contain reviewed extraction or synthesis, not mock or unreviewed generated summaries. targets No mock-derived briefs or extracted JSON are committed outside fixtures. over Per artifact commit. (committed).
- SM-3: Diagnostic run artifacts are linked to an issue or spec when committed. targets Every committed data/runs folder has a stated purpose. over Per diagnostic artifact commit. (committed).

## Evidence To Return

- Pull request URL.
- Verification result for each acceptance criterion.
- Eval run result for each AI eval.
- Screenshots or demo link if UI changed.
- Decision Trace if implementation changes product intent.
