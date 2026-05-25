# Eval Patterns

## Replay captured production payloads

Synthetic examples miss real edge cases. Use captured turns that already exhibit the failure mode.

## Binary metrics before subjective quality

Track whether the violation occurred before judging whether the answer was good.

## One variable per experiment

Change prompt, model, or tool design independently.

## Rule of three for zero observed failures

If zero failures are observed in N trials, the approximate 95% upper bound is 3/N.

## 2026-W21
- REFINED: Replay captured conversations with prompt-only restrictions versus dynamic tool permissions and measure violation rates.
