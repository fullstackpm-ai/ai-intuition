EXTRACTION_PROMPT = """You are not summarizing this source.

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

Return strict JSON matching the ExtractedInsight list schema.
Prefer fewer, sharper insights.
"""

EDITOR_PROMPT = """You are the adversarial editor for an AI operating intelligence system.

Your job is to remove generic, unsupported, duplicative, or non-actionable insights.

Input candidate insights:
{candidate_json}

Known design laws:
{known_design_laws}

Known failure modes:
{known_failure_modes}

Return strict JSON.
"""

WEEKLY_SYNTHESIS_PROMPT = """You are writing the weekly AI Operating Intelligence brief for a founder building commercial AI agents.

Do not summarize the week.

Use accepted insights to answer:
What should I now believe differently about commercial agent design?

Inputs:
{accepted_insights_json}
"""

BELIEF_UPDATE_PROMPT = """You maintain a living belief ledger for commercial agent design.

Current belief files:
{belief_files}

Weekly accepted insights:
{accepted_insights_json}
"""
