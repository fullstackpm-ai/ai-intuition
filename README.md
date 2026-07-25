# AI Intuition Compiler

Repo-first source-to-insight compiler for building durable intuition about LLMs, agents, model limitations, product architecture, and AI market structure.

```bash
uv sync
uv run aic run-weekly
```

By default, `run-weekly` discovers, ingests, normalizes, and writes Codex-ready extraction packets. It does not generate a final brief from mock extraction.

For deterministic test fixtures only:

```bash
uv run aic run-weekly --extraction-mode mock
```

For real Codex-harness extraction:

```bash
uv run aic extract --mode codex_packet --item <normalized_item_id>
uv run aic import-extraction --item <normalized_item_id> --path data/extracted/<normalized_item_id>.json
uv run aic edit
uv run aic brief --current-week
```

## Documentation

Start with [docs/index.md](docs/index.md).

This repo distinguishes living docs, point-in-time docs, and generated knowledge artifacts under `data/`.
