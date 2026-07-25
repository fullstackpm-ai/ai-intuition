from __future__ import annotations

from pathlib import Path

from app.models import ExtractedInsight


TARGETS = {
    "llm-mental-models.md": "mental_model",
    "agent-design-laws.md": "design_law",
    "failure-modes.md": "failure_mode",
    "eval-patterns.md": "eval_pattern",
    "strategy-models.md": "strategy_implication",
    "questions-to-investigate.md": "open_question",
}


def _with_weekly_lines(existing: str, week: str, lines: list[str]) -> str:
    missing = [line for line in lines if line not in existing]
    if not missing:
        return existing
    header = f"## {week}"
    if header not in existing:
        return existing.rstrip() + f"\n\n{header}\n" + "".join(missing)
    start = existing.index(header)
    next_start = existing.find("\n## ", start + len(header))
    if next_start == -1:
        return existing.rstrip() + "\n" + "".join(missing)
    return existing[:next_start].rstrip() + "\n" + "".join(missing) + existing[next_start:]


def update_beliefs(week: str, insights: list[ExtractedInsight], belief_dir: Path) -> list[Path]:
    accepted = [insight for insight in insights if insight.status == "accepted"]
    touched: list[Path] = []
    for filename, field in TARGETS.items():
        values = [getattr(insight, field) for insight in accepted if getattr(insight, field)]
        if not values:
            continue
        path = belief_dir / filename
        existing = path.read_text() if path.exists() else f"# {filename.removesuffix('.md').replace('-', ' ').title()}\n"
        lines = [f"- REFINED: {value}\n" for value in values]
        new_text = _with_weekly_lines(existing, week, lines)
        if new_text != existing:
            path.write_text(new_text)
            touched.append(path)
    ledger = belief_dir / "belief-ledger.md"
    existing = ledger.read_text() if ledger.exists() else "# Belief Ledger\n"
    lines = [f"- {insight.source_id}: {insight.intuition_update or insight.claim}\n" for insight in accepted]
    new_text = _with_weekly_lines(existing, week, lines)
    if new_text != existing:
        ledger.write_text(new_text)
        touched.append(ledger)
    return touched
