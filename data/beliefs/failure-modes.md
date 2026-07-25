# Failure Modes

## Buried negative

A "do not" rule appears in a low-salience location and loses to default model behavior.

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

## 2026-W21
- REFINED: Distant conditional / buried negative / pre-commitment drift / authority failure
- REFINED: Layer collapse: treating model alignment as if it also guarantees harness correctness, tool safety, permissioning, and environment isolation.
- REFINED: Approval fatigue: repeated low-value confirmations train users to approve without reviewing, weakening the control they were meant to provide.
- REFINED: Instruction laundering: hostile text enters through a trusted workflow object and is converted by the agent into an authorized external action.

## 2026-W30
- REFINED: Paper-only understanding: believing you understand an architecture because you read the result, while missing the operational constraints revealed by rebuilding it.
- REFINED: Pure-prior overreach: asking a model to intuit an answer where the task actually needs systematic exploration of possible futures.
- REFINED: Abstraction blindness: optimizing prompts or models while ignoring that latency and cost are dominated by low-level compute and memory constraints.
- REFINED: Uniform-precision thinking: using one precision posture across a workflow and missing where accumulated error, memory packing, or hardware availability changes the tradeoff.
