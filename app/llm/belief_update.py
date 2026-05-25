from __future__ import annotations

from pathlib import Path

from app.models import ExtractedInsight


TARGETS = {
    "agent-design-laws.md": "commercial_design_law",
    "failure-modes.md": "failure_mode",
    "eval-patterns.md": "eval_pattern",
    "ender-implications.md": "ender_implication",
}


def update_beliefs(week: str, insights: list[ExtractedInsight], belief_dir: Path) -> list[Path]:
    accepted = [insight for insight in insights if insight.status == "accepted"]
    touched: list[Path] = []
    for filename, field in TARGETS.items():
        values = [getattr(insight, field) for insight in accepted if getattr(insight, field)]
        if not values:
            continue
        path = belief_dir / filename
        existing = path.read_text() if path.exists() else f"# {filename.removesuffix('.md').replace('-', ' ').title()}\n"
        section = [f"\n## {week}\n"]
        for value in values:
            section.append(f"- REFINED: {value}\n")
        new_text = existing.rstrip() + "\n" + "".join(section)
        if new_text != existing:
            path.write_text(new_text)
            touched.append(path)
    ledger = belief_dir / "belief-ledger.md"
    existing = ledger.read_text() if ledger.exists() else "# Belief Ledger\n"
    section = [f"\n## {week}\n"]
    for insight in accepted:
        section.append(f"- {insight.source_id}: {insight.claim}\n")
    if accepted:
        ledger.write_text(existing.rstrip() + "\n" + "".join(section))
        touched.append(ledger)
    return touched
