# Belief Ledger

Durable belief updates are appended under weekly headings.

## 2026-W21
- manual: LLMs are unreliable final authorities for business rules when those rules are encoded only in prose.
- manual: Treat the model as a probabilistic interpreter of rules, not the layer that owns enforcement.
- anthropic_research: Stop asking whether the model is safe enough in isolation. Ask which layer owns each reliability property: model behavior, harness constraints, tool permissions, or environment boundaries.
- anthropic_research: More approval prompts do not necessarily mean more control. Oversight works when the user is asked to judge the plan, risk, and escalation points they can actually understand.
- anthropic_research: Defending against prompt injection means constraining the whole path from untrusted content to external action, not merely teaching the model to ignore bad instructions.

## 2026-W30
- dwarkesh_podcast: Treat frontier research papers less as static literature and more as rebuildable laboratories; LLM coding makes replication a practical intuition-building tool.
- dwarkesh_podcast: When evaluating agents, separate learned judgment from deliberation machinery. A stronger model is not the same thing as a better search/control loop.
- dwarkesh_podcast: Stop treating inference cost as an abstract cloud price. It is downstream of physical choices about arithmetic, precision, memory movement, and chip area.
- dwarkesh_podcast: Think of precision as a budgeted resource across the computation graph, not a single global knob.
