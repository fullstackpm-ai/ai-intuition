---
doc_type: living
category: processes
status: current
---

# ProductSpec Directive

Use [ProductSpec](https://github.com/gokulrajaram/ProductSpec) when consequential repo work needs intent, scope, acceptance criteria, and evidence to survive handoff between the user, Codex, and future agents.

ProductSpec is for changing the compiler. It is not for every article, transcript, extracted insight, or belief update.

## Ceremony Threshold

ProductSpec has a cost: it adds ceremony. Do not use it for tiny fixes, one-off source fetches, weekly content runs, or isolated artifact additions.

Use it when the change affects pipeline behavior, artifact semantics, extraction quality, weekly briefs, repo process, or another durable product contract. In those cases, the ceremony is intentional because it preserves intent, creates acceptance criteria, and makes future work safer across Codex sessions.

## GitHub Issue Rule

When the user says "add an issue", "create an issue", or otherwise asks to track work in GitHub, create a new GitHub issue in ProductSpec format.

The GitHub issue should include the same operating structure as a repo ProductSpec:

- ProductSpec framing, including `spec_status`, `spec_revision`, `applies_to`, and related ProductSpec path when known
- Problem
- Hypothesis
- Product Summary
- Scope, including explicit out-of-scope and cut items
- Acceptance Criteria with stable `AC-<number>` IDs
- AI/model evals as `EVAL-<number>` items when relevant
- Success Metrics as `SM-<number>` items when useful
- Related Artifacts

A local `.product-spec.md` file is required when the work becomes consequential repo execution work. It is optional for a lightweight issue that is only parking or triaging an idea.

## When To Create A Product Spec

Create or request a `.product-spec.md` when work changes one or more of these:

- source discovery or ingestion behavior
- transcript provider behavior
- extraction schema or prompt contract
- belief/topic update semantics
- weekly brief generation
- repository documentation model
- CLI behavior
- data artifact layout
- evaluation gates or quality bars

For any ProductSpec that touches pipeline behavior, source discovery, ingestion/transcripts, extraction, weekly briefs, belief updates, or artifact layout, include observability requirements in scope and acceptance criteria. The implementation must emit useful run events/source or stage attempts/failure classifications where applicable and include regression tests for those diagnostics.

Do not require ProductSpec for:

- one-off source fetches
- weekly content runs
- small typo fixes
- adding a single raw/manual artifact
- exploratory analysis that does not change repo behavior

## Location

Use these locations:

- Product specs: `docs/product-specs/<slug>.product-spec.md`
- Agent run receipts: `docs/agent-runs/<slug>.agent-run.json`
- Decision traces: `docs/decision-traces/<slug>.decision-trace.json`

Generated knowledge artifacts remain under `data/`.

## Creating A Spec

Use the local template:

- [AI Intuition ProductSpec template](templates/ai-intuition.product-spec.template.md)

A repo ProductSpec must include:

- Problem
- Hypothesis
- Scope, including explicit out-of-scope and cut items
- Acceptance Criteria with stable `AC-<number>` IDs
- AI/model evals as `EVAL-<number>` items when model behavior changes
- Success Metrics as `SM-<number>` items only for post-change outcomes
- Related Artifacts, including GitHub issues, relevant docs, and evidence paths

## Executing A Spec

Use ProductSpec as the implementation harness for consequential repo work. The default execution pattern is:

1. Validate the Product Spec.
2. Generate or read the Agent Handoff.
3. Implement against `scope.in`, `scope.out`, `scope.cut`, `AC-`, and `EVAL-` items.
4. Record an Agent Run receipt.
5. Validate the Agent Run and manually reconcile gaps before claiming completion.

Before planning or coding against a Product Spec:

1. Read the relevant `.product-spec.md`.
2. Identify `spec_revision` and, when possible, pin the spec content hash.
3. Map the implementation plan to `AC-` IDs.
4. Treat `scope.out` and `scope.cut` as explicit non-goals.
5. Generate an Agent Handoff with ProductSpec tooling when Node/npm access is available.
6. Run or add tests for every acceptance criterion that can be verified locally.
7. If implementation pressure conflicts with the spec, do not silently change intent.

When reporting completion:

- Cite the spec path and `spec_revision`.
- Cite the `AC-` and `EVAL-` items covered.
- Name any intentionally deferred scope.
- Link evidence paths, tests, generated artifacts, or GitHub issues.
- Create or update an Agent Run receipt under `docs/agent-runs/` for the implementation pass when the work materially changes code or durable behavior.

## Drift Rule

If evidence or implementation changes the intended product behavior, choose one:

- update the Product Spec revision
- update the implementation to match the spec
- record a Decision Trace
- reopen the work

Do not let code drift become undocumented intent.

## Validation

When Node/npm access is available, validate ProductSpec artifacts with:

```bash
npm exec --package @productspec/parser -- productspec validate docs/product-specs/<slug>.product-spec.md
npm exec --package @productspec/parser -- productspec handoff docs/product-specs/<slug>.product-spec.md
npm exec --package @productspec/parser -- productspec init-run docs/product-specs/<slug>.product-spec.md docs/agent-runs/<slug>.agent-run.json
npm exec --package @productspec/parser -- productspec validate-run docs/agent-runs/<slug>.agent-run.json
npm exec --package @productspec/parser -- productspec graph docs/product-specs --json
```

If validation cannot run locally, state that explicitly and still enforce this directive by reading the spec and checking acceptance criteria manually.

## Companion Artifacts

Use companion artifacts deliberately:

- Agent Handoff: use before implementation to create a compact, agent-ready build brief from the Product Spec.
- Agent Run: use after an implementation pass to record checked `AC-`, `EVAL-`, and `SM-` items, evidence, drift state, and completion claim.
- Decision Trace: use when implementation evidence changes product intent, scope, acceptance criteria, or success metrics.
- Graph: use before batching ProductSpec work to inspect spec relationships and possible file contention.
- Manual reconciliation: compare the Agent Run receipt against the Product Spec before claiming completion.
