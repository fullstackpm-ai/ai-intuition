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
                    "commercial_design_law": "Business-critical rules should be enforced through tools, code, schemas, validators, permissions, and workflow state.",
                    "failure_mode": "Distant conditional / buried negative / pre-commitment drift / authority failure",
                    "eval_pattern": "Replay captured conversations with prompt-only restrictions versus dynamic tool permissions and measure violation rates.",
                    "ender_implication": "Tour links, fee waivers, ledger edits, and collections actions should be gated by deterministic state and dynamic tool availability.",
                    "experiment_30_day": "Replay captured conversations with prompt-only restrictions vs dynamic tool permissions and measure violation rates.",
                    "evidence": [
                        {
                            "quote": "Prompt instructions are attention architecture, not deterministic authority.",
                            "location": "golden prompt-design note",
                            "note": "Captures the mechanism behind prose-only rule failures.",
                        }
                    ],
                    "confidence": "high",
                    "novelty": "high",
                    "decision_impact": "high",
                }
            ]
        return [
            {
                "claim": "The source discusses AI progress.",
                "mechanism": "",
                "commercial_design_law": None,
                "failure_mode": None,
                "eval_pattern": None,
                "ender_implication": None,
                "experiment_30_day": None,
                "evidence": [],
                "confidence": "low",
                "novelty": "low",
                "decision_impact": "low",
                "discard_reason": "Generic summary with no mechanism, Ender implication, experiment, or evidence.",
            }
        ]


def parse_jsonish(payload: object) -> object:
    if isinstance(payload, str):
        return json.loads(payload)
    return payload
