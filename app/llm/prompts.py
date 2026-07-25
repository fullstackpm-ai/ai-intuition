EXTRACTION_PROMPT = """You are not summarizing this source.

Your job is to extract only insights that would change how a senior AI product/operator understands LLMs, agents, model limitations, commercial AI architecture, evals, or AI market structure.

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
"""

EDITOR_PROMPT = """You are the adversarial editor for an AI intuition compiler.

Your job is to remove generic, unsupported, duplicative, or non-actionable insights.

Input candidate insights:
{candidate_json}

Known mental models:
{known_mental_models}

Known design laws:
{known_design_laws}

Known failure modes:
{known_failure_modes}

Known strategy models:
{known_strategy_models}

For each candidate:
- Accept only if it changes a belief, sharpens a mental model, names a useful failure mode, or creates a reusable law.
- Reject if it is a summary dressed up as insight.
- Reject if the intuition update is vague.
- Reject if there is no mechanism.
- Reject if there is no evidence.
- Reject if the learning experiment or intuition drill is not concrete enough to teach something.
- Mark needs_human_review if the claim is important but evidence is weak.

Prefer a maximum of 3 accepted insights per source.

Return strict JSON.
"""

WEEKLY_SYNTHESIS_PROMPT = """You are writing the weekly AI Intuition Brief for a founder/operator building deep judgment about LLMs, agents, and AI product architecture.

Do not summarize the week.

Use accepted insights to answer:
What should I now believe differently about AI systems?

Inputs:
{accepted_insights_json}
"""

BELIEF_UPDATE_PROMPT = """You maintain a living belief ledger for AI intuition.

Current belief files:
{belief_files}

Weekly accepted insights:
{accepted_insights_json}

Update the belief ledger only when there is a durable mental model, design law, failure mode, eval pattern, strategy model, or open question.
"""
