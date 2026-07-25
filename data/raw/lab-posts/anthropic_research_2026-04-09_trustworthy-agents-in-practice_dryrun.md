---
source_id: anthropic_research
source_name: Anthropic Research
lane: reliability_failures
source_type: html
title: Trustworthy agents in practice
url: https://www.anthropic.com/research/trustworthy-agents
published_at: 2026-04-09T00:00:00-07:00
---

# Trustworthy agents in practice

Dry-run source capture for Anthropic's April 9, 2026 article.

The article defines agents as self-directed systems that plan, act, observe, adjust, and repeat until a task is complete or human input is needed. It frames agents as made from four interacting components: model, harness, tools, and environment. The model provides core intelligence, but behavior depends on all four layers working together.

Anthropic uses expense submission as a concrete example: the agent may transcribe receipts, extract vendors and amounts, categorize expenses, submit them, notice policy gaps, ask whether to fetch an expense policy, and continue after receiving user approval.

The article argues that useful autonomy creates a governance tension. Simple action-by-action approval is intuitive, but for long workflows repeated prompts become friction and may cause users to ignore approvals. Claude Code's Plan Mode shifts oversight from individual actions to review of a proposed strategy, while preserving intervention during execution.

The article also describes the goal-uncertainty problem: an agent must learn when to resolve a gap itself and when to ask the user for preference or intent. Anthropic says it trains Claude on ambiguous scenarios and reinforces pausing over assuming in some cases.

For security, the article treats prompt injection as a multi-layer problem. A malicious instruction hidden in external content can cause damage only through the interaction of model interpretation, exposed tools, permissions, and environment. Anthropic says no single defense is enough, so defenses must span model training, monitoring, red teaming, tool choices, permissions, and operating environments.

The ecosystem-level section argues for shared benchmarks, evidence sharing, and open protocols such as MCP so agent security properties can be built into infrastructure rather than patched per deployment.
