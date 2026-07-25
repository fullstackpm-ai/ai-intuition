---
doc_type: living
category: processes
status: current
---

# ProductSpec Directive

Use [ProductSpec](https://github.com/gokulrajaram/ProductSpec) when consequential repo work needs intent, scope, acceptance criteria, and evidence to survive handoff between the user, Codex, and future agents.

ProductSpec is for changing the compiler. It is not for every article, transcript, extracted insight, or belief update.

## GitHub Issue Rule

When the user says "add an issue", "create an issue", or otherwise asks to track work in GitHub, create a new GitHub issue in ProductSpec format.

The GitHub issue should include the same operating structure as a repo ProductSpec:

- ProductSpec framing, including `spec_status`, `spec_revision`, `applies_to`, and related ProductSpec path when known
- Problem
- Hypothesis
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

Before planning or coding against a Product Spec:

1. Read the relevant `.product-spec.md`.
2. Identify `spec_revision`.
3. Map the implementation plan to `AC-` IDs.
4. Treat `scope.out` and `scope.cut` as explicit non-goals.
5. Run or add tests for every acceptance criterion that can be verified locally.
6. If implementation pressure conflicts with the spec, do not silently change intent.

When reporting completion:

- Cite the spec path and `spec_revision`.
- Cite the `AC-` and `EVAL-` items covered.
- Name any intentionally deferred scope.
- Link evidence paths, tests, generated artifacts, or GitHub issues.

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
npm exec --package @productspec/parser -- productspec garden .
```

If validation cannot run locally, state that explicitly and still enforce this directive by reading the spec and checking acceptance criteria manually.
