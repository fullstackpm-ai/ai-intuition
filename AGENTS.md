# AGENTS.md

## Project intent

This repo is an AI operating intelligence system. It is not an AI-news summarizer.

The system ingests sources, extracts durable commercial agent-design insights, updates a belief ledger, and generates weekly briefs.

The output should answer:

What should I now believe differently about commercial agent design, and what should Ender do because of it?

## Core product rule

Do not optimize for coverage. Optimize for surprise, decision impact, and reusable design laws.

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

## Quality bar

A useful insight has:
- mechanism
- design law or failure mode
- Ender implication
- falsifiable experiment
- evidence

Reject summaries that lack these.

## Run commands

Install:
`uv sync`

Run tests:
`uv run pytest`

Run weekly pipeline:
`uv run aios run-weekly`

Generate current brief:
`uv run aios brief --current-week`
