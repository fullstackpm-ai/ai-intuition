# LLM Mental Models

## LLMs are probabilistic interpreters, not deterministic authorities

LLMs can interpret ambiguous situations, synthesize language, and propose actions. They should not be the final authority for rules that require deterministic enforcement.

## Prompting is attention architecture

A prompt shapes what the model attends to. Placement, repetition, competition, and current-turn salience all affect behavior.

## Context size is not context control

Long context increases access to information. It does not guarantee that the right rule or fact controls the next token.

## Model size buys robustness, not correctness

Larger models can better compensate for weak prompt structure, but that can hide flawed architecture rather than fix it.

## Multi-hop conditional reasoning compounds failure probability

Tasks like "recall rule X, find state Y, apply condition Z, suppress default behavior" fail more often than single-hop directives or structural controls.

## 2026-W21
- REFINED: Prompting is attention architecture; business rules need structural authority.
- REFINED: Agent reliability stack = model capability + harness policy + tool affordances + environment exposure.
- REFINED: Oversight granularity should match human judgment granularity.
- REFINED: Prompt injection risk = untrusted observation x model compliance x tool capability x permission scope x environment exposure.

## 2026-W30
- REFINED: Research replication is becoming an operator workflow, not only an institutional capability.
- REFINED: Intelligence stack = learned prior + search process + environment model + outcome feedback.
- REFINED: Inference economics are physical: model behavior rides on multiply-accumulate density, precision, memory movement, and wiring.
- REFINED: Precision allocation = error budget + area budget + memory-packing budget.
