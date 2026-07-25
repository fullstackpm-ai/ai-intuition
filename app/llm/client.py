from __future__ import annotations

import json
from typing import Protocol


class LLMClient(Protocol):
    def complete_json(self, prompt: str) -> object:
        ...


class MockLLMClient:
    def complete_json(self, prompt: str) -> object:
        lower = prompt.lower()
        if "finite attention" in lower or "prompt compliance" in lower or "business-critical rules" in lower:
            return [
                {
                    "claim": "LLMs are unreliable final authorities for business rules when those rules are encoded only in prose.",
                    "mechanism": "Finite attention, position salience, default pretrained behavior, and multi-hop conditional failure make prompt compliance probabilistic.",
                    "intuition_update": "Treat the model as a probabilistic interpreter of rules, not the layer that owns enforcement.",
                    "mental_model": "Prompting is attention architecture; business rules need structural authority.",
                    "design_law": "Business-critical rules should be enforced through tools, code, schemas, validators, permissions, and workflow state.",
                    "failure_mode": "Distant conditional / buried negative / pre-commitment drift / authority failure",
                    "eval_pattern": "Replay captured conversations with prompt-only restrictions versus dynamic tool permissions and measure violation rates.",
                    "boundary_conditions": "Prompt-only rules may be acceptable for low-stakes style or tone constraints, but not for safety, money, permissions, or irreversible action.",
                    "learning_experiment": "Replay captured conversations with prompt-only restrictions versus dynamic tool permissions and measure violation rates.",
                    "intuition_drill": "Explain the difference between a model understanding a rule and a system enforcing a rule.",
                    "evidence": [
                        {
                            "quote": "Prompt instructions are attention architecture, not deterministic authority.",
                            "location": "golden prompt-design note",
                            "note": "Captures the mechanism behind prose-only rule failures.",
                        }
                    ],
                    "confidence": "high",
                    "novelty": "high",
                    "mental_model_impact": "high",
                }
            ]
        return [
            {
                "claim": "The source discusses AI progress.",
                "mechanism": "",
                "intuition_update": "",
                "mental_model": None,
                "design_law": None,
                "failure_mode": None,
                "eval_pattern": None,
                "boundary_conditions": None,
                "learning_experiment": None,
                "intuition_drill": None,
                "evidence": [],
                "confidence": "low",
                "novelty": "low",
                "mental_model_impact": "low",
                "discard_reason": "Generic summary with no mechanism, intuition update, learning experiment, or evidence.",
            }
        ]


def parse_jsonish(payload: object) -> object:
    if isinstance(payload, str):
        return json.loads(payload)
    return payload
