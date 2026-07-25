from __future__ import annotations

import json
import platform
import secrets
import subprocess
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.models import Source
from app.time import iso, now_utc


EventLevel = Literal["debug", "info", "warning", "error"]
EventType = Literal[
    "run_started",
    "run_finished",
    "stage_started",
    "stage_finished",
    "source_attempt_started",
    "source_attempt_finished",
    "source_skipped",
    "source_failed",
    "item_skipped",
    "artifact_written",
    "artifact_unchanged",
    "fallback_attempted",
    "fallback_succeeded",
    "fallback_failed",
    "brief_attribution_summarized",
]
Outcome = Literal[
    "success",
    "healthy_empty",
    "skipped_config",
    "blocked_auth",
    "blocked_provider",
    "rate_limited",
    "not_found",
    "malformed_source",
    "adapter_regression",
    "network_failure",
    "unexpected_failure",
]
Retryability = Literal["retryable", "permanent", "operator_action_required", "bug_likely", "not_applicable"]


class ErrorDetails(BaseModel):
    exception_class: str
    message: str
    http_status: int | None = None
    provider_error_code: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class PipelineEvent(BaseModel):
    run_id: str
    timestamp: datetime
    command: str
    stage: str
    event_type: EventType
    level: EventLevel = "info"
    source_id: str | None = None
    adapter: str | None = None
    url: str | None = None
    artifact_id: str | None = None
    artifact_path: str | None = None
    elapsed_ms: int | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceAttempt(BaseModel):
    run_id: str
    source_id: str
    source_name: str
    source_type: str
    lane: str
    adapter: str
    stage: str = "ingest"
    urls_attempted: list[str] = Field(default_factory=list)
    item_count: int = 0
    artifact_count: int = 0
    elapsed_ms: int = 0
    outcome: Outcome
    retryability: Retryability
    error: ErrorDetails | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageResult(BaseModel):
    run_id: str
    stage: str
    elapsed_ms: int
    outcome: Outcome
    retryability: Retryability = "not_applicable"
    artifact_count: int = 0
    error: ErrorDetails | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunManifest(BaseModel):
    run_id: str
    command: str
    options: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    data_dir: str
    python_version: str
    git_commit: str | None = None
    extraction_mode: str | None = None
    source_filter: str | None = None
    window: dict[str, str | None] = Field(default_factory=dict)


class RunSummary(BaseModel):
    run_id: str
    command: str
    started_at: datetime
    finished_at: datetime
    elapsed_ms: int
    outcome: Outcome
    source_attempts: int
    source_outcomes: dict[str, int]
    stage_outcomes: dict[str, int]
    artifact_counts: dict[str, int]
    extraction_mode: str | None = None
    failure_report_path: str | None = None
    run_dir: str


def make_run_id(command: str, now: datetime | None = None) -> str:
    stamp = (now or now_utc()).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{command.replace('_', '-')}-{secrets.token_hex(3)}"


def classify_exception(exc: BaseException) -> tuple[Outcome, Retryability, ErrorDetails]:
    http_status: int | None = None
    provider_error_code: str | None = None
    message = str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        http_status = exc.response.status_code
    elif isinstance(exc, httpx.HTTPError):
        return (
            "network_failure",
            "retryable",
            ErrorDetails(exception_class=exc.__class__.__name__, message=message, context={}),
        )

    lowered = message.lower()
    if http_status in {401, 403}:
        outcome, retryability = "blocked_auth", "operator_action_required"
    elif http_status == 429:
        outcome, retryability = "rate_limited", "retryable"
    elif http_status == 404:
        outcome, retryability = "not_found", "permanent"
    elif http_status and 500 <= http_status < 600:
        outcome, retryability = "network_failure", "retryable"
    elif "spotify_not_cached" in lowered:
        outcome, retryability = "not_found", "permanent"
        provider_error_code = "spotify_not_cached"
    elif any(code in lowered for code in ["unsupported_url", "too_long", "auth_required"]):
        outcome, retryability = "blocked_provider", "permanent"
        provider_error_code = lowered.split(":", 1)[0].strip()
    elif any(code in lowered for code in ["metadata_failed", "transcription_failed", "rate_limit"]):
        outcome, retryability = "rate_limited" if "rate_limit" in lowered else "network_failure", "retryable"
        provider_error_code = lowered.split(":", 1)[0].strip()
    elif isinstance(exc, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
        outcome, retryability = "malformed_source", "bug_likely"
    else:
        outcome, retryability = "unexpected_failure", "bug_likely"

    return (
        outcome,
        retryability,
        ErrorDetails(
            exception_class=exc.__class__.__name__,
            message=message,
            http_status=http_status,
            provider_error_code=provider_error_code,
            context={},
        ),
    )


class RunContext:
    def __init__(
        self,
        command: str,
        data_dir: Path,
        options: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> None:
        self.command = command
        self.data_dir = data_dir
        self.run_id = run_id or make_run_id(command)
        self.run_dir = data_dir / "runs" / self.run_id
        self.started_at = now_utc()
        self.options = options or {}
        self.events: list[PipelineEvent] = []
        self.source_attempts: list[SourceAttempt] = []
        self.stage_results: list[StageResult] = []
        self.artifact_counts: Counter[str] = Counter()
        self.summary: RunSummary | None = None

    def start(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self._write_json("manifest.json", self.manifest().model_dump(mode="json"))
        self.event("run", "run_started", "Run started.", metadata={"options": self.options})

    def manifest(self) -> RunManifest:
        window = self.options.get("window") if isinstance(self.options.get("window"), dict) else {}
        return RunManifest(
            run_id=self.run_id,
            command=self.command,
            options=self.options,
            started_at=self.started_at,
            data_dir=str(self.data_dir),
            python_version=platform.python_version(),
            git_commit=_git_commit(),
            extraction_mode=self.options.get("extraction_mode"),
            source_filter=self.options.get("source"),
            window={str(k): str(v) if v is not None else None for k, v in window.items()},
        )

    def event(
        self,
        stage: str,
        event_type: EventType,
        message: str,
        *,
        level: EventLevel = "info",
        source: Source | None = None,
        source_id: str | None = None,
        adapter: str | None = None,
        url: str | None = None,
        artifact_id: str | None = None,
        artifact_path: str | None = None,
        elapsed_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineEvent:
        event = PipelineEvent(
            run_id=self.run_id,
            timestamp=now_utc(),
            command=self.command,
            stage=stage,
            event_type=event_type,
            level=level,
            source_id=source.id if source else source_id,
            adapter=adapter or (source.adapter or source.type if source else None),
            url=url,
            artifact_id=artifact_id,
            artifact_path=artifact_path,
            elapsed_ms=elapsed_ms,
            message=message,
            metadata=metadata or {},
        )
        self.events.append(event)
        with (self.run_dir / "events.jsonl").open("a") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event

    @contextmanager
    def stage(self, name: str, metadata: dict[str, Any] | None = None) -> Iterator[None]:
        started = time.perf_counter()
        self.event(name, "stage_started", f"Stage {name} started.", metadata=metadata)
        try:
            yield
        except BaseException as exc:
            elapsed_ms = _elapsed_ms(started)
            outcome, retryability, error = classify_exception(exc)
            self.stage_results.append(
                StageResult(
                    run_id=self.run_id,
                    stage=name,
                    elapsed_ms=elapsed_ms,
                    outcome=outcome,
                    retryability=retryability,
                    error=error,
                    metadata=metadata or {},
                )
            )
            self.event(
                name,
                "stage_finished",
                f"Stage {name} failed.",
                level="error",
                elapsed_ms=elapsed_ms,
                metadata={"outcome": outcome, "retryability": retryability, "error": error.model_dump(mode="json")},
            )
            raise
        else:
            elapsed_ms = _elapsed_ms(started)
            self.stage_results.append(
                StageResult(run_id=self.run_id, stage=name, elapsed_ms=elapsed_ms, outcome="success", metadata=metadata or {})
            )
            self.event(
                name,
                "stage_finished",
                f"Stage {name} finished.",
                elapsed_ms=elapsed_ms,
                metadata={"outcome": "success", "retryability": "not_applicable"},
            )

    def record_stage_skip(self, stage: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        self.stage_results.append(
            StageResult(run_id=self.run_id, stage=stage, elapsed_ms=0, outcome="skipped_config", metadata=metadata or {})
        )
        self.event(stage, "stage_started", f"Stage {stage} skipped.", metadata=metadata)
        self.event(
            stage,
            "stage_finished",
            message,
            metadata={"outcome": "skipped_config", "retryability": "not_applicable", **(metadata or {})},
        )

    def record_source_attempt(
        self,
        source: Source,
        *,
        stage: str,
        urls_attempted: list[str],
        item_count: int,
        artifact_count: int,
        elapsed_ms: int,
        outcome: Outcome,
        retryability: Retryability = "not_applicable",
        error: ErrorDetails | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SourceAttempt:
        attempt = SourceAttempt(
            run_id=self.run_id,
            source_id=source.id,
            source_name=source.name,
            source_type=source.type,
            lane=source.lane,
            adapter=source.adapter or source.type,
            stage=stage,
            urls_attempted=urls_attempted,
            item_count=item_count,
            artifact_count=artifact_count,
            elapsed_ms=elapsed_ms,
            outcome=outcome,
            retryability=retryability,
            error=error,
            metadata=metadata or {},
        )
        self.source_attempts.append(attempt)
        event_type: EventType = "source_failed" if error or outcome not in {"success", "healthy_empty", "skipped_config"} else "source_attempt_finished"
        self.event(
            stage,
            event_type,
            f"Source {source.id} finished with {outcome}.",
            level="error" if event_type == "source_failed" else "info",
            source=source,
            url=urls_attempted[0] if urls_attempted else None,
            elapsed_ms=elapsed_ms,
            metadata=attempt.model_dump(mode="json"),
        )
        return attempt

    def record_artifact(self, stage: str, artifact_path: str, artifact_id: str | None, changed: bool) -> None:
        event_type: EventType = "artifact_written" if changed else "artifact_unchanged"
        counter_key = f"{stage}_{'written' if changed else 'unchanged'}"
        self.artifact_counts[counter_key] += 1
        self.event(
            stage,
            event_type,
            f"Artifact {'written' if changed else 'unchanged'}: {artifact_path}",
            artifact_id=artifact_id,
            artifact_path=artifact_path,
        )

    def finish(self) -> RunSummary:
        failures = [attempt for attempt in self.source_attempts if attempt.outcome not in {"success", "healthy_empty", "skipped_config"}]
        stage_failures = [stage for stage in self.stage_results if stage.outcome not in {"success", "skipped_config"}]
        outcome: Outcome = "success" if not failures and not stage_failures else "unexpected_failure"
        failure_report_path = None
        if failures or stage_failures:
            failure_report_path = str(self.run_dir / "failure_report.md")
            (self.run_dir / "failure_report.md").write_text(render_failure_report(self))
        summary = RunSummary(
            run_id=self.run_id,
            command=self.command,
            started_at=self.started_at,
            finished_at=now_utc(),
            elapsed_ms=int((now_utc() - self.started_at).total_seconds() * 1000),
            outcome=outcome,
            source_attempts=len(self.source_attempts),
            source_outcomes=dict(Counter(attempt.outcome for attempt in self.source_attempts)),
            stage_outcomes=dict(Counter(stage.outcome for stage in self.stage_results)),
            artifact_counts=dict(self.artifact_counts),
            extraction_mode=self.options.get("extraction_mode"),
            failure_report_path=failure_report_path,
            run_dir=str(self.run_dir),
        )
        self.summary = summary
        self._write_json("summary.json", summary.model_dump(mode="json"))
        self.event("run", "run_finished", f"Run finished with {outcome}.", metadata=summary.model_dump(mode="json"))
        return summary

    def _write_json(self, name: str, payload: dict[str, Any]) -> None:
        (self.run_dir / name).write_text(json.dumps(payload, indent=2, default=str) + "\n")


def render_failure_report(context: RunContext) -> str:
    lines = [
        f"# Failure Report - {context.run_id}",
        "",
        f"- Command: `{context.command}`",
        f"- Started: {iso(context.started_at)}",
        "",
    ]
    failing_attempts = [attempt for attempt in context.source_attempts if attempt.outcome not in {"success", "healthy_empty", "skipped_config"}]
    failing_stages = [stage for stage in context.stage_results if stage.outcome not in {"success", "skipped_config"}]
    if failing_attempts:
        lines.extend(["## Source Failures", ""])
        for attempt in failing_attempts:
            lines.append(f"### {attempt.source_id}")
            lines.append(f"- Outcome: `{attempt.outcome}`")
            lines.append(f"- Retryability: `{attempt.retryability}`")
            lines.append(f"- Adapter: `{attempt.adapter}`")
            if attempt.urls_attempted:
                lines.append(f"- URL: {attempt.urls_attempted[0]}")
            if attempt.error:
                lines.append(f"- Error: `{attempt.error.exception_class}` - {attempt.error.message}")
                if attempt.error.http_status:
                    lines.append(f"- HTTP status: `{attempt.error.http_status}`")
                if attempt.error.provider_error_code:
                    lines.append(f"- Provider code: `{attempt.error.provider_error_code}`")
            lines.append(f"- Next action: {_next_action(attempt.outcome, attempt.retryability)}")
            lines.append("")
    if failing_stages:
        lines.extend(["## Stage Failures", ""])
        for stage in failing_stages:
            lines.append(f"### {stage.stage}")
            lines.append(f"- Outcome: `{stage.outcome}`")
            lines.append(f"- Retryability: `{stage.retryability}`")
            if stage.error:
                lines.append(f"- Error: `{stage.error.exception_class}` - {stage.error.message}")
            lines.append(f"- Next action: {_next_action(stage.outcome, stage.retryability)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _next_action(outcome: Outcome, retryability: Retryability) -> str:
    if retryability == "operator_action_required":
        return "Check credentials, access, paywall, or provider policy."
    if retryability == "retryable":
        return "Retry later and preserve this run folder if the failure repeats."
    if retryability == "permanent":
        return "Do not retry blindly; update source configuration or fallback path."
    if retryability == "bug_likely":
        return "Add or update a regression fixture and inspect the adapter/parser."
    return f"Inspect `{outcome}` in the run events."


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _git_commit() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None
