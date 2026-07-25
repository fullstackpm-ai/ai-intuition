# AGENTS.md

## Project intent

This repo is an AI intuition compiler. It is not an AI-news summarizer.

The system ingests sources, extracts durable mental models and commercial agent-design insights, updates a belief ledger, and generates weekly briefs.

The output should answer:

What should I now believe differently about LLMs, agents, model limitations, product architecture, and AI market structure?

## Core product rule

Do not optimize for coverage. Optimize for surprise, mental-model impact, and reusable laws.

## Development rules

- Use Python 3.12+.
- Use `uv` for package management.
- Use `typer` for CLI.
- Use `pydantic` for data models.
- Keep v1 repo-first. Do not add a web dashboard.
- Store raw, normalized, extracted, and brief artifacts as files under `data/`.
- Use SQLite only for indexing/idempotency state.
- Avoid LangChain/LlamaIndex unless explicitly needed.
- Add tests for every pipeline stage.
- Make commands idempotent.

## Documentation rules

- `AGENTS.md` is the concise agent-facing source of current operating rules.
- Use `docs/living/` for current explanations, runbooks, north-star direction, and shared processes.
- Use `docs/point-in-time/` for accepted specs, decisions, and plans that should preserve historical context.
- Use ProductSpec files under `docs/product-specs/` for consequential repo changes that need explicit intent, scope, acceptance criteria, and evidence.
- ProductSpec has ceremony cost. Do not use it for tiny fixes, one-off source fetches, weekly content runs, or isolated artifact additions. Use it when changes affect pipeline behavior, artifact semantics, extraction quality, weekly briefs, repo process, or another durable product contract.
- When the user says "add an issue", "create an issue", or asks to track work in GitHub, create a new GitHub issue in ProductSpec format. Use the ProductSpec issue structure even if a local `.product-spec.md` file is not yet warranted, and link/create the local ProductSpec file when the work is consequential enough to execute.
- Before planning or coding against a `.product-spec.md`, follow the ProductSpec implementation workflow in `docs/living/project/processes/productspec-implementation-workflow.md`: validate the spec, generate/read the Agent Handoff when tooling is available, map work to `AC-` IDs, respect `scope.out` and `scope.cut`, record an Agent Run receipt for material implementation work, validate the run receipt, and manually reconcile gaps before claiming completion.
- If implementation pressure conflicts with a Product Spec, propose a spec revision, implementation change, Decision Trace, or reopened work; do not silently change intent.
- Treat root `SPEC.md` as point-in-time product context unless a living doc explicitly supersedes it.
- Do not treat generated `data/` artifacts as documentation; they are pipeline evidence and outputs.
- Follow the artifact commit policy in `docs/living/project/processes/artifact-commit-policy.md`: generated `data/` artifacts are not docs, but their retention follows the same living versus point-in-time rubric. Commit point-in-time evidence and source-grounded synthesis, commit living belief files when reviewed, attach degraded run diagnostics to issues, keep local state local, and delete regenerable working output or mock/legacy synthesis.
- Before staging generated weekly artifacts, run `uv run aic artifact-report` and treat its `commit`, `keep-local`, `attach-to-issue`, or `delete` recommendation as the default action. Treat `review` as an ambiguity exception, not as permission to defer the decision.
- When changing pipeline behavior, source discovery, ingestion/transcripts, extraction, brief generation, belief updates, or artifact layout, wire the change into observability: run events, source/stage attempts, artifact write/unchanged events, failure classification, and run summaries where applicable. Add or update tests so failures remain diagnosable and regressions are caught.
- Update living docs alongside code when behavior, commands, source policy, or artifact semantics change.

## Quality bar

A useful insight has:
- mechanism
- intuition update
- mental model, design law, failure mode, eval pattern, or strategy model
- evidence
- boundary condition or counterexample when the claim is broad
- learning experiment or intuition drill when useful

Reject summaries that lack these.

## Run commands

Install:
`uv sync`

Run tests:
`uv run pytest`

Run weekly pipeline:
`uv run aic run-weekly`

Classify weekly run artifacts before staging:
`uv run aic artifact-report`

The default weekly run writes Codex-ready extraction packets and skips mock-derived brief generation. Use `uv run aic run-weekly --extraction-mode mock` only for deterministic fixture/testing flows.

Import Codex-authored extraction JSON:
`uv run aic import-extraction --item <normalized_item_id> --path data/extracted/<normalized_item_id>.json`

Generate current brief:
`uv run aic brief --current-week`
