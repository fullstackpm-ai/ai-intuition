# SPEC.md — AI Operating Intelligence / Source-to-Insight Compiler

## 0. One-line purpose

Build a repo-first intelligence system that ingests frontier AI research, product launches, selected podcasts, and strategy commentary, then produces a weekly memo answering:

> What should I now believe differently about commercial agent design, and what should Ender do because of it?

This is not a summarizer. It is a source-to-insight compiler.

---

## 1. Product thesis

Most AI content is not useful because it stops at summary.

The useful unit is a durable product/design insight:

- a new agent design law
- a named failure mode
- an eval pattern
- a commercial architecture implication
- a concrete experiment to run

The system should discard anything that cannot be converted into one of those artifacts.

Example of the target insight shape:

> Rules expressed only in prose are probabilistic. Business-critical rules should be enforced through tools, code, schemas, validators, permissions, and workflow state. Prompt instructions are attention architecture, not deterministic authority.

That is the quality bar.

---

## 2. Non-goals

Do not build these in v1:

- A dashboard.
- A general AI-news aggregator.
- A chatbot over articles.
- A vector database unless retrieval becomes necessary.
- Autonomous web-browsing swarms.
- Full support for every possible source.
- Perfect podcast transcription.
- Automated decisions that update beliefs without review.

The v1 product is a command-line/repo workflow that creates high-quality markdown artifacts.

---

## 3. Design principles

### 3.1 Repo is the system of record

The Git repo is canonical.

Email is a rendering of the weekly brief, not the source of truth.

All raw inputs, normalized texts, extracted insights, weekly briefs, and belief-ledger updates should be versioned.

### 3.2 Structured extraction beats prose summaries

The core data object is `ExtractedInsight`, not a paragraph summary.

Each insight must include:

- mechanism
- commercial design law
- failure mode
- Ender implication
- experiment
- evidence
- confidence
- novelty
- discard rationale if rejected

### 3.3 Fewer sharper insights

The system should prefer three high-signal belief updates over thirty summaries.

The editor pass should delete aggressively.

### 3.4 Source roles are different

Each source class has a distinct interpretation lens:

- Lab research: mechanisms and frontier primitives.
- Eval/failure/security research: limits and failure modes.
- Product launches: interface contracts and harness patterns.
- Podcasts: frontier priors and operator assumptions.
- Strategy commentary: value capture and defensibility.
- Internal/domain material: Ender-specific workflow implications.

### 3.5 Every output must be decision-linked

No item enters the weekly brief unless it can affect at least one of:

- agent architecture
- permissioning / tool design
- eval design
- roadmap prioritization
- product UX
- GTM / value capture
- Ender defensibility

---

## 4. Target user

Primary user: founder/operator building AI-native commercial software for property-management workflows.

The user wants insight density, not completeness.

The user wants the system to challenge priors, surface failure modes, and compress frontier AI research into product architecture judgment.

---

## 5. v1 source scope

Start narrow.

### 5.1 Frontier / lab sources

Required:

- OpenAI blog / research / product announcements.
- Anthropic research / news / engineering.
- Google DeepMind blog.

Optional after v1 works:

- Meta AI research.
- Microsoft Research AI.
- Selected arXiv papers only when referenced by the required sources or manually added.

### 5.2 Podcast / interview sources

Required initial podcast sources:

- Dwarkesh Podcast.
- Lenny's Podcast.

In v1, do not ingest every episode automatically into the final brief. Ingest all candidates, but only promote items with real belief updates.

### 5.3 Strategy sources

Required:

- Stratechery, if accessible through subscription/manual export/RSS.
- Optional: selected investor/operator essays added manually through `sources.yaml`.

Strategy sources should never be interpreted as technical truth. They should be interpreted for value-capture implications.

### 5.4 Internal / golden sources

Include a `/golden/` folder with known high-quality examples.

The initial golden example should be the prompt-design principles note. It represents the desired transformation from observed model behavior into reusable commercial agent design laws.

---

## 6. Repository structure

```text
ai-operating-intelligence/
  README.md
  AGENTS.md
  SPEC.md
  pyproject.toml
  .env.example
  sources.yaml

  app/
    __init__.py
    cli.py

    config.py
    models.py
    ids.py
    time.py
    logging.py

    ingest/
      __init__.py
      rss.py
      html.py
      podcast.py
      transcript.py
      manual.py

    normalize/
      __init__.py
      normalize.py
      chunk.py

    llm/
      __init__.py
      client.py
      prompts.py
      extract.py
      edit.py
      synthesize.py
      belief_update.py

    store/
      __init__.py
      db.py
      files.py
      git.py

    email/
      __init__.py
      render.py
      send.py

    evals/
      __init__.py
      golden.py
      assertions.py

  data/
    raw/
      podcasts/
      lab-posts/
      product-launches/
      strategy/
      manual/
    normalized/
    extracted/
    rejected/
    briefs/
    beliefs/
      agent-design-laws.md
      failure-modes.md
      eval-patterns.md
      ender-implications.md
      belief-ledger.md
    golden/
      prompt-design-principles.md

  tests/
    test_models.py
    test_extract_schema.py
    test_source_registry.py
    test_golden_prompt_design.py
```

---

## 7. Recommended technical stack

Use Python for v1.

Reason: ingestion, RSS parsing, markdown generation, CLI automation, transcripts, and cron jobs are all simpler in Python. A web app can come later.

Use:

- Python 3.12+
- `uv` for dependency management
- `typer` for CLI
- `pydantic` for schemas
- `httpx` for HTTP
- `feedparser` for RSS
- `trafilatura` or `readability-lxml` for article extraction
- `beautifulsoup4` for fallback parsing
- `python-frontmatter` for markdown metadata
- `sqlite-utils` or SQLAlchemy for local state
- OpenAI SDK for LLM extraction/synthesis
- `pytest` for tests
- `rich` for CLI output
- `resend` or SMTP for email, phase 2

Avoid adding LangChain/LlamaIndex in v1 unless there is a specific need. The pipeline is simple enough without a framework.

---

## 8. Configuration

### 8.1 `.env.example`

```bash
OPENAI_API_KEY=

# Optional transcription providers
TRANSCRIPTION_PROVIDER=manual # manual | usetranscribe | openai
USETRANSCRIBE_API_KEY=
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-transcribe

# Email, phase 2
EMAIL_PROVIDER=none # none | resend | smtp
RESEND_API_KEY=
EMAIL_FROM=
EMAIL_TO=

# Optional authenticated sources
STRATECHERY_COOKIE=
```

### 8.2 `sources.yaml`

```yaml
sources:
  - id: openai
    name: OpenAI
    lane: frontier_primitives
    type: rss_or_html
    urls:
      - https://openai.com/news/
      - https://openai.com/research/
    enabled: true

  - id: anthropic
    name: Anthropic
    lane: reliability_failures
    type: rss_or_html
    urls:
      - https://www.anthropic.com/research
      - https://www.anthropic.com/news
      - https://www.anthropic.com/engineering
    enabled: true

  - id: google-deepmind
    name: Google DeepMind
    lane: frontier_primitives
    type: rss_or_html
    urls:
      - https://deepmind.google/discover/blog/
    enabled: true

  - id: dwarkesh
    name: Dwarkesh Podcast
    lane: frontier_priors
    type: podcast
    urls:
      - https://www.dwarkesh.com/podcast
    enabled: true
    transcript_provider: usetranscribe

  - id: lenny
    name: Lenny's Podcast
    lane: product_patterns
    type: podcast
    urls:
      - https://www.lennysnewsletter.com/podcast
    enabled: true
    transcript_provider: usetranscribe

  - id: stratechery
    name: Stratechery
    lane: strategy_value_capture
    type: manual_or_authenticated
    urls:
      - https://stratechery.com/
    enabled: false
    notes: "Start disabled unless authenticated access/manual export is configured."

  - id: manual
    name: Manual Inputs
    lane: manual
    type: manual
    path: data/raw/manual
    enabled: true
```

---

## 9. Data model

Implement in `app/models.py` using Pydantic.

### 9.1 `Source`

```python
class Source(BaseModel):
    id: str
    name: str
    lane: Literal[
        "frontier_primitives",
        "reliability_failures",
        "product_patterns",
        "frontier_priors",
        "strategy_value_capture",
        "manual",
    ]
    type: str
    urls: list[str] = []
    path: str | None = None
    enabled: bool = True
    transcript_provider: str | None = None
    notes: str | None = None
```

### 9.2 `RawArtifact`

```python
class RawArtifact(BaseModel):
    id: str
    source_id: str
    source_name: str
    lane: str
    source_type: str
    title: str
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    raw_path: str
    content_hash: str
    metadata: dict[str, Any] = {}
```

### 9.3 `NormalizedItem`

```python
class NormalizedItem(BaseModel):
    id: str
    raw_artifact_id: str
    source_id: str
    lane: str
    title: str
    url: str | None = None
    published_at: datetime | None = None
    normalized_path: str
    text: str
    word_count: int
    extraction_notes: str | None = None
```

### 9.4 `ExtractedInsight`

```python
class ExtractedInsight(BaseModel):
    id: str
    item_id: str
    source_id: str
    source_title: str
    source_url: str | None = None
    lane: str

    status: Literal["candidate", "accepted", "rejected", "needs_human_review"]

    claim: str
    mechanism: str
    commercial_design_law: str | None = None
    failure_mode: str | None = None
    eval_pattern: str | None = None
    ender_implication: str | None = None
    experiment_30_day: str | None = None

    evidence: list["Evidence"]
    confidence: Literal["low", "medium", "high"]
    novelty: Literal["low", "medium", "high"]
    decision_impact: Literal["low", "medium", "high"]

    editor_notes: str | None = None
    discard_reason: str | None = None
    created_at: datetime
```

### 9.5 `Evidence`

```python
class Evidence(BaseModel):
    quote: str
    location: str | None = None # URL, timestamp, section, etc.
    note: str | None = None
```

### 9.6 `WeeklyBrief`

```python
class WeeklyBrief(BaseModel):
    week: str # e.g. 2026-W22
    generated_at: datetime
    one_line_thesis: str
    belief_updates: list[str]
    new_or_updated_design_laws: list[str]
    new_failure_modes: list[str]
    ender_implications: dict[str, list[str]]
    experiments: list[str]
    ignored_noise: list[str]
    source_rollup: list[str]
    human_review_flags: list[str]
```

---

## 10. Storage and idempotency

Use SQLite for state and markdown/JSON files for artifacts.

### 10.1 SQLite tables

Minimum tables:

```sql
sources
raw_artifacts
normalized_items
extracted_insights
runs
```

Track content hashes so re-running ingestion does not duplicate artifacts.

Use deterministic IDs:

```text
{source_id}_{published_date}_{slug}_{hash8}
```

For podcasts, use episode URL or title + published date.

---

## 11. CLI commands

Implement with Typer.

### 11.1 `aios ingest`

```bash
aios ingest --since 7d
aios ingest --source openai --since 30d
aios ingest --manual data/raw/manual/some-file.md
```

Behavior:

- Reads `sources.yaml`.
- Fetches enabled sources.
- Saves raw artifacts.
- Updates SQLite.
- Does not call the LLM.

### 11.2 `aios normalize`

```bash
aios normalize --since 7d
aios normalize --item <raw_artifact_id>
```

Behavior:

- Converts raw HTML/transcripts/manual markdown into clean text markdown.
- Saves to `data/normalized/{item_id}.md`.
- Preserves metadata frontmatter.

### 11.3 `aios extract`

```bash
aios extract --since 7d
aios extract --item <normalized_item_id>
```

Behavior:

- Runs extraction prompt over normalized items.
- Writes JSON to `data/extracted/{item_id}.json`.
- Writes rejected insights to `data/rejected/{item_id}.json`.

### 11.4 `aios edit`

```bash
aios edit --since 7d
```

Behavior:

- Runs adversarial editor pass over candidate insights.
- Deletes/downgrades generic insights.
- Marks accepted/rejected/needs_human_review.

### 11.5 `aios brief`

```bash
aios brief --week 2026-W22
aios brief --current-week
```

Behavior:

- Reads accepted insights for the week.
- Clusters/dedupes by mechanism/design law.
- Generates `data/briefs/2026-W22.md`.
- Proposes updates to belief files.

### 11.6 `aios belief-update`

```bash
aios belief-update --week 2026-W22
```

Behavior:

- Updates:
  - `data/beliefs/agent-design-laws.md`
  - `data/beliefs/failure-modes.md`
  - `data/beliefs/eval-patterns.md`
  - `data/beliefs/ender-implications.md`
  - `data/beliefs/belief-ledger.md`
- Should mark changes clearly under a weekly heading.

### 11.7 `aios send`

```bash
aios send --week 2026-W22
```

Behavior:

- Sends the markdown brief to configured email recipient.
- Phase 2 only.

### 11.8 `aios run-weekly`

```bash
aios run-weekly
```

Behavior:

Runs:

```bash
aios ingest --since 7d
aios normalize --since 7d
aios extract --since 7d
aios edit --since 7d
aios brief --current-week
aios belief-update --current-week
```

Do not send email unless `--send` is provided.

---

## 12. LLM prompts

Implement prompt strings in `app/llm/prompts.py`.

### 12.1 Extraction prompt

```text
You are not summarizing this source.

Your job is to extract only insights that would change how a senior AI product/operator designs commercial agents.

Source lane:
{lane}

Source title:
{title}

Source text:
{text}

Extract candidate insights only if they satisfy at least one condition:
- reveal a mechanism of model behavior or agent behavior
- expose a failure mode relevant to commercial agent design
- suggest a reusable agent design law
- imply a concrete product architecture change
- imply a concrete eval pattern
- affect value capture or defensibility for vertical AI software
- suggest a 30-day experiment for Ender

For each candidate insight:
1. State the claim.
2. State the mechanism, not the headline.
3. Convert it into a reusable commercial agent design law if possible.
4. Name the failure mode it exposes or reduces if possible.
5. Explain the implication for Ender workflows.
6. Propose a 30-day experiment.
7. Include short evidence quotes or timestamp/location.
8. Assign confidence, novelty, and decision impact.

Reject anything that is merely:
- news
- funding
- generic AI hype
- generic product advice
- benchmark movement without deployment implications
- duplicate of an existing known law
- interesting but not actionable

Return strict JSON matching the ExtractedInsight list schema.
Prefer fewer, sharper insights.
```

### 12.2 Editorial prompt

```text
You are the adversarial editor for an AI operating intelligence system.

Your job is to remove generic, unsupported, duplicative, or non-actionable insights.

Input candidate insights:
{candidate_json}

Known design laws:
{known_design_laws}

Known failure modes:
{known_failure_modes}

For each candidate:
- Accept only if it changes a deployment assumption or creates a useful reusable law.
- Reject if it is a summary dressed up as insight.
- Reject if the Ender implication is vague.
- Reject if the experiment is not testable in 30 days.
- Mark needs_human_review if the claim is important but evidence is weak.

Prefer a maximum of 3 accepted insights per source.

Return strict JSON.
```

### 12.3 Weekly synthesis prompt

```text
You are writing the weekly AI Operating Intelligence brief for a founder building commercial AI agents.

Do not summarize the week.

Use accepted insights to answer:
What should I now believe differently about commercial agent design?

Inputs:
{accepted_insights_json}

Write a punchy markdown memo with this structure:

# AI Operating Intelligence — {week}

## One-line thesis
One sentence.

## 3 belief updates
Only include belief updates that changed a prior.

## New or updated agent design laws
Each law should be reusable and concrete.

## New failure modes to track
Name the failure mode and explain why it matters.

## Ender implications
Group by:
- Leasing
- Maintenance
- Accounting
- Collections
- Support
- Platform / architecture

## Experiments to run in 30 days
Each experiment must be small, falsifiable, and tied to a failure mode or design law.

## Ignored noise
List categories or specific items ignored and why.

## Human review flags
Important claims that should not be accepted automatically.

Style:
- Dense.
- Direct.
- No hype.
- No generic AI commentary.
- No long summaries.
```

### 12.4 Belief-ledger update prompt

```text
You maintain a living belief ledger for commercial agent design.

Current belief files:
{belief_files}

Weekly accepted insights:
{accepted_insights_json}

Update the belief ledger only when there is a durable law, failure mode, eval pattern, or Ender implication.

For each update:
- state whether it is NEW, REFINED, or CHALLENGED
- include source IDs
- include week
- write in durable language
- do not add transient news

Return markdown patches grouped by target file.
```

---

## 13. Weekly brief output contract

Example file: `data/briefs/2026-W22.md`.

```markdown
---
week: 2026-W22
generated_at: 2026-05-25T09:00:00-05:00
accepted_insights: 7
human_review_flags: 2
---

# AI Operating Intelligence — 2026-W22

## One-line thesis

Agent value is shifting from model capability to controlled execution environments.

## 3 belief updates

1. Long context improves access to information, but not reliable enforcement of business rules.
2. Tool-using agents should be permissioned by available actions, not instructed through prohibitions.
3. User trust appears to form around inspectable autonomy: users want visibility into actions, state, and rollback more than raw reasoning traces.

## New or updated agent design laws

### Context salience beats context size
Long context enables retrieval; it does not guarantee that the right condition controls the next action. Promote active constraints and retrieve passive reference material.

### Tool availability is permissioning
Do not expose tools the model is not allowed to call. Dynamic tool lists are stronger than prompt-level “do not call” instructions.

## New failure modes to track

### Pre-commitment drift
The model commits in language before it verifies whether the action is allowed, then follows the commitment into a rule violation.

## Ender implications

### Leasing
Tour links should be exposed as a tool only when deterministic unit state permits tour scheduling.

### Maintenance
Maintenance triage can tolerate more autonomy because most actions are reversible and inspection-friendly.

### Accounting
Fee waivers, ledger edits, deposits, credits, and write-offs need structural approval gates.

### Collections
Payment-plan suggestions can be drafted by the model, but execution should require deterministic eligibility checks and human approval.

### Platform / architecture
Active constraints should be generated per turn from state, not manually buried in static prompt text.

## Experiments to run in 30 days

1. Replay 50 leasing conversations with full-context prompts versus state-promoted prompts; measure tour-link leakage.
2. Replace prompt-level “do not waive fees” rule with tool-level permission gating; measure false action claims.
3. Build a reversibility matrix for Ender workflows and assign allowed autonomy levels.

## Ignored noise

- Generic funding announcements.
- Benchmark gains with no deployment implication.
- Podcast segments with no changed assumption.

## Human review flags

- Check whether the latest model release materially changes long-context salience failures or only reduces them.
```

---

## 14. Belief files

### 14.1 `data/beliefs/agent-design-laws.md`

Initial seed:

```markdown
# Agent Design Laws

## Rules in prose are probabilistic; rules in tools/code are structural

Business-critical constraints should not rely only on prompt compliance. Use tools, code, schemas, validators, permissions, and workflow state to make disallowed actions impossible or recoverable.

## Context salience beats context size

Long context gives the model access to more material; it does not guarantee the model will apply the right rule at the right moment. Promote active constraints into the current turn.

## Tool availability is permissioning

If the model should not be allowed to perform an action, do not expose the tool. Dynamic tool lists are stronger than prompt-level prohibitions.

## Autonomy expands with reversibility

Agents can be given more autonomy where actions are reversible, low-stakes, observable, and cheaply recoverable. Irreversible financial/legal actions require structural gates.

## Evals must bind to named failure modes

Generic quality ratings are weak. Use replay evals tied to specific failures: leakage, false action claims, policy violation, wrong tool call, stale-state action, and unsafe commitment.
```

### 14.2 `data/beliefs/failure-modes.md`

Initial seed:

```markdown
# Failure Modes

## Buried negative

A “do not” rule appears in a low-salience location and loses to default model behavior.

## Distant conditional

A rule depends on state located far away in the context, forcing a multi-hop chain: recall rule, find data, bind state, apply condition, suppress default behavior.

## Negative list dilution

A long list of prohibitions becomes a set of weak considerations rather than strong constraints.

## Pre-commitment drift

The model writes language committing to an action before checking whether the action is allowed.

## Context bloat

Large irrelevant context dilutes attention and makes important rules less salient.

## Authority failure

The model is allowed to decide something that should have been enforced by code, tool permissions, schemas, or validators.
```

### 14.3 `data/beliefs/eval-patterns.md`

Initial seed:

```markdown
# Eval Patterns

## Replay captured production payloads

Synthetic examples miss real edge cases. Use captured turns that already exhibit the failure mode.

## Binary metrics before subjective quality

Track whether the violation occurred before judging whether the answer was good.

## One variable per experiment

Change prompt, model, or tool design independently.

## Rule of three for zero observed failures

If zero failures are observed in N trials, the approximate 95% upper bound is 3/N.
```

### 14.4 `data/beliefs/ender-implications.md`

Initial seed:

```markdown
# Ender Implications

## Leasing

Tour scheduling must be governed by deterministic unit state and tool availability, not prompt-only instructions.

## Maintenance

Maintenance triage is a high-autonomy candidate because many actions are reversible and auditable.

## Accounting

Ledger mutation, fee waivers, deposits, credits, and write-offs require structural approval gates.

## Collections

Collections workflows should distinguish drafting from execution. The model can draft options; deterministic policy and human approval should govern execution.

## Platform

Active constraints should be generated from state on each turn and placed at the top of the prompt or represented through available tools.
```

---

## 15. Scoring

Each candidate insight should receive:

```text
novelty: low | medium | high
decision_impact: low | medium | high
confidence: low | medium | high
```

Accept if:

```text
decision_impact = high
AND confidence != low
AND novelty != low
```

Or:

```text
decision_impact = medium
AND novelty = high
AND confidence = medium/high
```

Reject if:

- no mechanism
- no Ender implication
- no falsifiable experiment
- no evidence
- generic summary
- not materially different from known belief files

Mark `needs_human_review` if:

- decision impact is high but confidence is low
- source is commentary rather than primary evidence
- claim could materially change roadmap or architecture
- source is paywalled/partial and evidence is incomplete

---

## 16. Source-specific interpretation rules

### 16.1 Lab research

Read for mechanisms.

Extraction question:

> What does this change about what the model can infer versus what the system must enforce?

### 16.2 Eval/failure/security research

Read for limits.

Extraction question:

> What failure mode must our architecture make impossible, observable, or recoverable?

### 16.3 Product launches

Read for interface contracts.

Extraction question:

> What contract is this product establishing between user, model, tool, and environment?

### 16.4 Podcasts

Read for assumptions, not truth.

Extraction question:

> What assumption about the future would I adopt if this person is right, and what would Ender do differently?

### 16.5 Strategy commentary

Read for value capture.

Extraction question:

> Does this make Ender more likely to be the operating system, or more likely to become a database behind someone else's agent?

---

## 17. Transcription approach

v1 should support `manual` and one automated provider.

### 17.1 Manual transcript path

Allow the user to drop transcripts into:

```text
data/raw/podcasts/manual/
```

With frontmatter:

```markdown
---
source_id: dwarkesh
title: Example Episode
url: https://...
published_at: 2026-05-20
---

Transcript text here.
```

This path is important because it avoids blocking on transcription provider quirks.

### 17.2 useTranscribe adapter

Implement provider interface:

```python
class TranscriptProvider(Protocol):
    def transcribe(self, url: str) -> TranscriptResult:
        ...
```

For v1, the useTranscribe adapter can be a placeholder if API details are not available. Do not hardcode brittle scraping.

### 17.3 OpenAI transcription adapter

Support local audio files through OpenAI transcription if the audio file is available.

Inputs:

```bash
aios transcribe --file episode.mp3 --source dwarkesh
```

Output:

```text
data/raw/podcasts/{source_id}_{date}_{slug}.md
```

---

## 18. Quality evals

Create a golden eval around the prompt-design note.

### 18.1 Golden expected extraction

The system should extract something equivalent to:

```json
{
  "claim": "LLMs are unreliable final authorities for business rules when those rules are encoded only in prose.",
  "mechanism": "Finite attention, position salience, default pretrained behavior, and multi-hop conditional failure make prompt compliance probabilistic.",
  "commercial_design_law": "Business-critical rules should be enforced through tools, code, schemas, validators, permissions, and workflow state.",
  "failure_mode": "Distant conditional / buried negative / pre-commitment drift / authority failure",
  "ender_implication": "Tour links, fee waivers, ledger edits, and collections actions should be gated by deterministic state and dynamic tool availability.",
  "experiment_30_day": "Replay captured conversations with prompt-only restrictions vs dynamic tool permissions and measure violation rates."
}
```

### 18.2 Test requirements

Implement tests that assert:

- extraction returns valid JSON
- accepted insights contain mechanism
- accepted insights contain Ender implication
- accepted insights contain experiment
- generic summaries are rejected
- prompt-design golden source produces at least one insight matching the expected design law

---

## 19. AGENTS.md content

Create `AGENTS.md` at repo root:

```markdown
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
```

---

## 20. First implementation milestone

Build this first:

1. Repo skeleton.
2. `sources.yaml`.
3. Pydantic models.
4. SQLite state.
5. Manual source ingestion.
6. RSS/HTML ingestion for one source.
7. Normalization.
8. Extraction prompt with mocked LLM option.
9. Editorial pass with mocked LLM option.
10. Weekly brief generation from extracted JSON.
11. Belief files seeded with initial laws.
12. Golden eval for prompt-design note.

Do not build podcast transcription until the manual path and one lab-source path work.

---

## 21. Second milestone

Add:

1. Podcast ingestion.
2. useTranscribe adapter or OpenAI transcription adapter.
3. Lenny/Dwarkesh source adapters.
4. Email sending.
5. Git commit automation.
6. Weekly cron / GitHub Actions.
7. Human-review flags in the weekly brief.

---

## 22. Third milestone

Add:

1. Clustering/deduplication across insights.
2. Similarity check against known belief laws.
3. Lightweight retrieval over belief files.
4. Source-level performance metrics.
5. Dashboard only if the repo artifacts become too hard to navigate.

---

## 23. GitHub Actions

Create `.github/workflows/weekly.yml` later:

```yaml
name: weekly-ai-operating-intelligence

on:
  schedule:
    - cron: "0 14 * * MON"
  workflow_dispatch:

jobs:
  weekly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run aios run-weekly
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      - name: Commit weekly artifacts
        run: |
          git config user.name "ai-operating-intelligence"
          git config user.email "bot@example.com"
          git add data/
          git commit -m "weekly brief" || echo "No changes"
          git push
```

Do not enable email sending in GitHub Actions until secrets are configured.

---

## 24. Definition of done for v1

v1 is done when:

- `uv run aios run-weekly` works locally.
- The system can ingest at least one manual source and one web source.
- The prompt-design golden source produces a high-quality design-law extraction.
- The system generates a weekly markdown brief.
- Belief files are updated or explicitly unchanged.
- Generic summaries are rejected.
- Tests pass.
- The user can read the weekly brief in under five minutes and find at least one actionable product/architecture implication.

---

## 25. North-star metric

The system is working if the user can say once per week:

> This changed how I think about building commercial agents.

The system is failing if the output feels like:

> Here is what happened in AI this week.
