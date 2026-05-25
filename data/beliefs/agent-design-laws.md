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

## 2026-W21
- REFINED: Business-critical rules should be enforced through tools, code, schemas, validators, permissions, and workflow state.
