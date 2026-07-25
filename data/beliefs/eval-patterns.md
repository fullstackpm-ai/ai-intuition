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
- REFINED: Run the same task across controlled variations of harness, tool permissions, and environment exposure to identify which layer actually prevents the failure.
- REFINED: Replay long workflows with per-action approval versus plan approval and measure user interruptions, missed risky actions, and completion rate.
- REFINED: Seed realistic workflow data with hidden malicious instructions and test whether the agent reads, propagates, or acts on them under different tool-permission settings.

## 2026-W30
- REFINED: Select one canonical agent or ML system, rebuild the minimal version with LLM coding assistance, and log every place where implementation friction changes the conceptual takeaway.
- REFINED: Compare a model-only agent with the same model wrapped in explicit candidate generation, simulation, and scoring on tasks with verifiable end states.
- REFINED: For a target workflow, estimate token volume, context length, precision sensitivity, and latency budget, then map those to likely compute and memory bottlenecks.
- REFINED: Run task-level evals across precision and quantization settings, but separately inspect failures that arise from accumulation-sensitive steps.
