---
id: manual_2026-05-24_prompt-design-principles_13dd85ab
lane: manual
published_at: '2026-05-24T00:00:00'
raw_artifact_id: manual_2026-05-24_prompt-design-principles_13dd85ab
raw_path: data/raw/manual/manual_2026-05-24_prompt-design-principles_13dd85ab.md
source_id: manual
source_name: Manual Inputs
source_type: manual
title: Prompt Design Principles
url: internal://golden/prompt-design-principles
---

# Prompt Design Principles

LLMs are unreliable final authorities for business rules when those rules are encoded only in prose. Prompt instructions are attention architecture, not deterministic authority.

Finite attention, position salience, default pretrained behavior, and multi-hop conditional failure make prompt compliance probabilistic. A rule can be present in context and still fail to control the next action, especially when the rule is a buried negative, a distant conditional, or part of a diluted list of prohibitions.

Commercial agents should move business-critical constraints out of prose and into tools, code, schemas, validators, permissions, and workflow state. Tool availability is permissioning: if the model should not perform an action, the tool should not be available.

For Ender, tour links, fee waivers, ledger edits, and collections actions should be gated by deterministic state and dynamic tool availability. A practical eval is to replay captured conversations with prompt-only restrictions versus dynamic tool permissions and measure violation rates.