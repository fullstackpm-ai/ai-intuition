# Extraction Packet: Trustworthy agents in practice

## Output paths

- Accepted/candidate insights: `data/extracted/anthropic_research_2026-04-09_trustworthy-agents-in-practice_dryrun.json`

- Rejected insights: `data/rejected/anthropic_research_2026-04-09_trustworthy-agents-in-practice_dryrun.json`

## Source metadata

- item_id: `anthropic_research_2026-04-09_trustworthy-agents-in-practice_dryrun`

- source_id: `anthropic_research`

- lane: `reliability_failures`

- title: `Trustworthy agents in practice`

- url: `https://www.anthropic.com/research/trustworthy-agents`

- published_at: `2026-04-09 00:00:00-07:00`

## Schema guidance

Return a JSON list of ExtractedInsight-like objects using these fields:
- claim
- mechanism
- intuition_update
- mental_model
- design_law
- failure_mode
- eval_pattern
- boundary_conditions
- counterargument
- strategy_implication
- learning_experiment
- intuition_drill
- open_question
- evidence: [{quote, location, note}]
- confidence: low | medium | high
- novelty: low | medium | high
- mental_model_impact: low | medium | high
- discard_reason for rejected summaries

## Extraction prompt

You are not summarizing this source.

Your job is to extract only insights that would change how a senior AI product/operator understands LLMs, agents, model limitations, commercial AI architecture, evals, or AI market structure.

Source lane:
reliability_failures

Source title:
Trustworthy agents in practice

Source text:
# Trustworthy agents in practice

Dry-run source capture for Anthropic's April 9, 2026 article.

The article defines agents as self-directed systems that plan, act, observe, adjust, and repeat until a task is complete or human input is needed. It frames agents as made from four interacting components: model, harness, tools, and environment. The model provides core intelligence, but behavior depends on all four layers working together.

Anthropic uses expense submission as a concrete example: the agent may transcribe receipts, extract vendors and amounts, categorize expenses, submit them, notice policy gaps, ask whether to fetch an expense policy, and continue after receiving user approval.

The article argues that useful autonomy creates a governance tension. Simple action-by-action approval is intuitive, but for long workflows repeated prompts become friction and may cause users to ignore approvals. Claude Code's Plan Mode shifts oversight from individual actions to review of a proposed strategy, while preserving intervention during execution.

The article also describes the goal-uncertainty problem: an agent must learn when to resolve a gap itself and when to ask the user for preference or intent. Anthropic says it trains Claude on ambiguous scenarios and reinforces pausing over assuming in some cases.

For security, the article treats prompt injection as a multi-layer problem. A malicious instruction hidden in external content can cause damage only through the interaction of model interpretation, exposed tools, permissions, and environment. Anthropic says no single defense is enough, so defenses must span model training, monitoring, red teaming, tool choices, permissions, and operating environments.

The ecosystem-level section argues for shared benchmarks, evidence sharing, and open protocols such as MCP so agent security properties can be built into infrastructure rather than patched per deployment.

Extract candidate insights only if they satisfy at least one condition:
- reveal a mechanism of model behavior or agent behavior
- expose a failure mode relevant to commercial agent design
- suggest a reusable agent design law
- imply a concrete eval pattern
- sharpen intuition about business-rule understanding, tool use, context, memory, planning, or autonomy
- affect a prior about AI capability trajectories, product adoption, value capture, or market structure
- reveal a boundary condition where a common belief breaks
- suggest a toy example, learning experiment, or test question that would build intuition

For each candidate insight:
1. State the claim.
2. State the mechanism, not the headline.
3. State the intuition update: what should the reader now believe differently?
4. Convert it into a reusable mental model or commercial agent design law if possible.
5. Name the failure mode it exposes or reduces if possible.
6. Name the eval pattern it suggests if possible.
7. State boundary conditions and counterarguments if relevant.
8. Propose a learning experiment, toy example, or intuition drill.
9. Include short evidence quotes or timestamp/location.
10. Assign confidence, novelty, and mental_model_impact.

Reject anything that is merely:
- news
- funding
- generic AI hype
- generic product advice
- benchmark movement without deployment implication
- duplicate of an existing known law
- interesting but not intuition-changing

Return strict JSON matching the ExtractedInsight list schema.
Prefer fewer, sharper insights.

