from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal

import frontmatter
from pydantic import BaseModel, Field


LifecycleState = Literal[
    "working",
    "retained-local",
    "evidence",
    "review-packet",
    "reviewed-knowledge",
    "diagnostic",
    "disposable",
]
ArtifactRecommendation = Literal["commit", "review", "keep-local", "attach-to-issue", "delete"]

REAL_EXTRACTION_METHODS = {"api", "codex_packet", "manual"}
RISKY_EXTRACTION_METHODS = {"mock", "legacy"}
HASH_SUFFIX_RE = re.compile(r"_[0-9a-f]{8,}$")


class ArtifactDecision(BaseModel):
    path: str
    git_status: str = ""
    lifecycle: LifecycleState
    recommendation: ArtifactRecommendation
    reason: str
    evidence: list[str] = Field(default_factory=list)


class ArtifactReport(BaseModel):
    root: str
    total: int
    recommendations: dict[str, int]
    lifecycles: dict[str, int]
    decisions: list[ArtifactDecision]


def collect_weekly_artifact_paths(root: Path, data_dir: Path) -> list[tuple[Path, str]]:
    """Return changed data artifacts plus ignored local SQLite state when present."""
    paths: list[tuple[Path, str]] = []
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--", str(data_dir.relative_to(root))],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError, ValueError):
        result = None

    if result:
        for line in result.stdout.splitlines():
            if not line:
                continue
            status = line[:2].strip() or line[:2]
            raw_path = line[3:].strip()
            if " -> " in raw_path:
                raw_path = raw_path.split(" -> ", 1)[1]
            path = root / raw_path
            if path.is_dir():
                paths.extend((child, status) for child in sorted(path.rglob("*")) if child.is_file())
            else:
                paths.append((path, status))

    sqlite_path = data_dir / "state.sqlite3"
    if sqlite_path.exists() and all(path != sqlite_path for path, _ in paths):
        paths.append((sqlite_path, "ignored"))
    return sorted(paths, key=lambda item: _relative_path(root, item[0]))


def build_artifact_report(root: Path, changed_paths: list[tuple[Path, str]] | None = None, data_dir: Path | None = None) -> ArtifactReport:
    data_dir = data_dir or root / "data"
    path_statuses = changed_paths if changed_paths is not None else collect_weekly_artifact_paths(root, data_dir)
    decisions = classify_artifacts(root, path_statuses)
    return ArtifactReport(
        root=str(root),
        total=len(decisions),
        recommendations=dict(Counter(decision.recommendation for decision in decisions)),
        lifecycles=dict(Counter(decision.lifecycle for decision in decisions)),
        decisions=decisions,
    )


def classify_artifacts(root: Path, path_statuses: list[tuple[Path, str]]) -> list[ArtifactDecision]:
    siblings = _same_item_siblings(root, [path for path, _ in path_statuses])
    changed_statuses_by_key: dict[str, set[str]] = defaultdict(set)
    for path, status in path_statuses:
        key = _stable_item_key(root, path)
        if key:
            changed_statuses_by_key[key].add(status)
    decisions: list[ArtifactDecision] = []
    for path, status in path_statuses:
        decision = classify_artifact(root, path, git_status=status)
        stable_key = _stable_item_key(root, path)
        same_item = siblings.get(stable_key, [])
        if same_item:
            decision.evidence.append(f"Possible rerun sibling(s): {', '.join(same_item)}")
            if _is_clean_rerun_replacement(status, changed_statuses_by_key.get(stable_key, set())):
                decision.evidence.append("rubric=clean-rerun replacement")
                if decision.recommendation == "commit":
                    decision.reason = f"{decision.reason} This artifact replaces a deleted stale rerun sibling in the same change."
            elif status == "??":
                decision.lifecycle = "disposable"
                decision.recommendation = "delete"
                decision.reason = (
                    f"{decision.reason} Existing retained sibling found; delete this regenerated duplicate unless you intentionally "
                    "want a new point-in-time capture."
                )
            elif decision.recommendation == "commit":
                decision.recommendation = "review"
                decision.reason = f"{decision.reason} Review possible rerun duplicate before promotion."
        decisions.append(decision)
    return decisions


def _is_clean_rerun_replacement(status: str, sibling_statuses: set[str]) -> bool:
    return status in {"??", "A", "D"} and "D" in sibling_statuses and bool(sibling_statuses & {"??", "A"})


def classify_artifact(root: Path, path: Path, git_status: str = "") -> ArtifactDecision:
    relative = _relative_path(root, path)
    parts = Path(relative).parts
    if relative == "data/state.sqlite3":
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="retained-local",
            recommendation="keep-local",
            reason="SQLite is local idempotency/index state and should not be committed.",
        )
    if len(parts) < 2 or parts[0] != "data":
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="working",
            recommendation="review",
            reason="Path is outside the known weekly artifact policy; inspect manually.",
        )

    section = parts[1]
    if section == "raw":
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="evidence",
            recommendation="commit",
            reason="Raw captures are point-in-time source evidence for the weekly corpus and should be retained unless superseded.",
            evidence=["rubric=point-in-time evidence"],
        )
    if section == "normalized":
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="evidence",
            recommendation="commit",
            reason="Normalized items are reproducible point-in-time extraction inputs and should be retained with their raw source evidence.",
            evidence=["rubric=point-in-time evidence"],
        )
    if section == "extraction-packets":
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="working",
            recommendation="delete",
            reason="Bulk extraction packets are regenerable working output. Delete by default unless intentionally selected as a fixture or review packet.",
            evidence=["rubric=working output"],
        )
    if section in {"extracted", "rejected"}:
        return _classify_extraction_json(root, path, git_status, section)
    if section == "briefs":
        return _classify_brief(root, path, git_status)
    if section == "beliefs":
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="reviewed-knowledge",
            recommendation="commit",
            reason="Belief files are living knowledge. Commit changes when they reflect current reviewed understanding.",
            evidence=["rubric=living knowledge"],
        )
    if section == "runs":
        return _classify_run_diagnostic(root, path, git_status)
    return ArtifactDecision(
        path=relative,
        git_status=git_status,
        lifecycle="working",
        recommendation="review",
        reason="Data artifact is not covered by a more specific rule; inspect before committing.",
    )


def render_artifact_report_markdown(report: ArtifactReport) -> str:
    lines = [
        "# Weekly Artifact Report",
        "",
        f"- Total artifacts: {report.total}",
        f"- Recommendations: {_format_counts(report.recommendations)}",
        f"- Lifecycle states: {_format_counts(report.lifecycles)}",
        "",
        "| Recommendation | Lifecycle | Path | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for decision in report.decisions:
        evidence = f" Evidence: {'; '.join(decision.evidence)}" if decision.evidence else ""
        lines.append(
            f"| `{decision.recommendation}` | `{decision.lifecycle}` | `{decision.path}` | {decision.reason}{evidence} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _classify_extraction_json(root: Path, path: Path, git_status: str, section: str) -> ArtifactDecision:
    relative = _relative_path(root, path)
    methods = _extraction_methods(path)
    risky = sorted(methods & RISKY_EXTRACTION_METHODS)
    real = sorted(methods & REAL_EXTRACTION_METHODS)
    if risky or not methods:
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="disposable",
            recommendation="delete",
            reason=f"{section} JSON has mock, legacy, or missing extraction provenance and should not become durable knowledge.",
            evidence=[f"extraction_methods={sorted(methods) or ['missing']}"],
        )
    if real and methods <= REAL_EXTRACTION_METHODS:
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="reviewed-knowledge",
            recommendation="commit",
            reason=f"{section} JSON has real extraction provenance and is reviewed knowledge eligible for retention.",
            evidence=[f"extraction_methods={real}", "rubric=point-in-time reviewed knowledge"],
        )
    return ArtifactDecision(
        path=relative,
        git_status=git_status,
        lifecycle="working",
        recommendation="review",
        reason=f"{section} JSON has unfamiliar extraction provenance; inspect before committing.",
        evidence=[f"extraction_methods={sorted(methods)}"],
    )


def _classify_brief(root: Path, path: Path, git_status: str) -> ArtifactDecision:
    relative = _relative_path(root, path)
    provenance = _brief_provenance(path)
    methods = set(provenance)
    risky = sorted(methods & RISKY_EXTRACTION_METHODS)
    if risky or not methods:
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="disposable",
            recommendation="delete",
            reason="Brief lacks real/reviewed extraction provenance or includes mock/legacy provenance.",
            evidence=[f"extraction_provenance={provenance or {'missing': 0}}"],
        )
    if methods <= REAL_EXTRACTION_METHODS:
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="reviewed-knowledge",
            recommendation="commit",
            reason="Brief is a point-in-time weekly synthesis based on real extraction provenance.",
            evidence=[f"extraction_provenance={provenance}", "rubric=point-in-time synthesis"],
        )
    return ArtifactDecision(
        path=relative,
        git_status=git_status,
        lifecycle="working",
        recommendation="review",
        reason="Brief has unfamiliar provenance; inspect before committing.",
        evidence=[f"extraction_provenance={provenance}"],
    )


def _classify_run_diagnostic(root: Path, path: Path, git_status: str) -> ArtifactDecision:
    relative = _relative_path(root, path)
    run_dir = _run_dir_for(path)
    summary_path = run_dir / "summary.json" if run_dir else None
    failure_report_path = run_dir / "failure_report.md" if run_dir else None
    summary = _read_json(summary_path) if summary_path and summary_path.exists() else {}
    outcome = summary.get("outcome")
    source_outcomes = summary.get("source_outcomes", {})
    has_failure_report = bool(failure_report_path and failure_report_path.exists())
    if has_failure_report or (outcome and outcome != "success"):
        return ArtifactDecision(
            path=relative,
            git_status=git_status,
            lifecycle="diagnostic",
            recommendation="attach-to-issue",
            reason="Run diagnostics explain a degraded or failed run. Link to a bug/spec before committing.",
            evidence=[f"run_outcome={outcome}", f"source_outcomes={source_outcomes}"],
        )
    return ArtifactDecision(
        path=relative,
        git_status=git_status,
        lifecycle="diagnostic",
        recommendation="keep-local",
        reason="Successful run diagnostics are operational evidence and should not be committed by default.",
        evidence=[f"run_outcome={outcome or 'unknown'}"],
    )


def _extraction_methods(path: Path) -> set[str]:
    payload = _read_json(path)
    records = payload if isinstance(payload, list) else [payload]
    methods = set()
    for record in records:
        if isinstance(record, dict):
            methods.add(str(record.get("extraction_method") or "legacy"))
    return methods


def _brief_provenance(path: Path) -> dict[str, int]:
    try:
        post = frontmatter.loads(path.read_text())
    except Exception:
        return {}
    provenance = post.metadata.get("extraction_provenance")
    if not isinstance(provenance, dict):
        return {}
    return {str(key): int(value) for key, value in provenance.items()}


def _same_item_siblings(root: Path, changed_paths: list[Path]) -> dict[str, list[str]]:
    tracked = _tracked_data_paths(root)
    by_key: dict[str, list[Path]] = defaultdict(list)
    for path in [*changed_paths, *tracked]:
        key = _stable_item_key(root, path)
        if key:
            by_key[key].append(path)
    result: dict[str, list[str]] = {}
    for key, paths in by_key.items():
        unique = sorted({_relative_path(root, path) for path in paths})
        if len(unique) > 1:
            for path in paths:
                relative = _relative_path(root, path)
                result.setdefault(key, [candidate for candidate in unique if candidate != relative])
    return result


def _stable_item_key(root: Path, path: Path) -> str:
    relative = _relative_path(root, path)
    parts = Path(relative).parts
    if len(parts) < 3 or parts[0] != "data" or parts[1] not in {"raw", "normalized", "extraction-packets"}:
        return ""
    stem = HASH_SUFFIX_RE.sub("", Path(relative).stem)
    return str(Path(*parts[:-1], stem))


def _tracked_data_paths(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "data/raw", "data/normalized", "data/extraction-packets"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [root / line for line in result.stdout.splitlines() if line]


def _run_dir_for(path: Path) -> Path | None:
    parts = path.parts
    if "runs" not in parts:
        return None
    index = parts.index("runs")
    if len(parts) <= index + 1:
        return None
    return Path(*parts[: index + 2])


def _read_json(path: Path | None) -> Any:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
