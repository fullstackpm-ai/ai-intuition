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
