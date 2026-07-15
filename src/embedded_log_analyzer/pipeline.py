from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaModelOutputError,
)
from .preprocess import PreprocessResult, preprocess_file
from .schema import load_prompt, load_schema
from .validation import (
    ModelOutputValidationError,
    effective_severity,
    validate_analysis,
    validate_triage,
)


@dataclass(frozen=True)
class PipelineConfig:
    triage_model: str = "embedded-log-triage:4b"
    analysis_model: str = "embedded-log-analysis:9b"
    num_ctx: int = 8192
    triage_num_predict: int = 384
    analysis_num_predict: int = 1024
    escalation_confidence: float = 0.65
    encoding: str = "utf-8"
    max_input_bytes: int = 50 * 1024 * 1024
    max_input_lines: int = 250_000
    window_before: int = 80
    window_after: int = 40
    max_windows: int = 3
    max_evidence_lines: int = 300
    max_estimated_tokens: int = 3000


def should_escalate(
    deterministic: PreprocessResult,
    triage: dict[str, Any],
    *,
    confidence_threshold: float,
) -> bool:
    if deterministic.has_critical_pattern:
        return True
    if triage["severity"] in {"critical", "high"}:
        return True
    if triage["classification"] in {
        "possible_anomaly",
        "insufficient_evidence",
    }:
        return True
    if triage["needs_deep_analysis"]:
        return True
    if float(triage["confidence"]) < confidence_threshold:
        return True
    return False


def _base_report(
    deterministic: PreprocessResult,
    *,
    stage: str,
    config: PipelineConfig,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "deterministic_only",
        "requested_stage": stage,
        "effective_severity": deterministic.highest_severity,
        "deterministic": deterministic.deterministic_dict(),
        "model_policy": {
            "triage_model": config.triage_model,
            "analysis_model": config.analysis_model,
            "num_ctx": config.num_ctx,
            "requests_are_sequential": True,
            "requested_keep_alive": 0,
            "tools_enabled": False,
        },
        "triage": None,
        "analysis": None,
        "model_metrics": {},
        "safety_overrides": [],
        "limitations": [
            "Model output is advisory and may be rejected.",
            "No model output is executed; no hardware-changing path exists.",
        ],
    }


def _preprocess(path: Path, config: PipelineConfig) -> PreprocessResult:
    return preprocess_file(
        path,
        encoding=config.encoding,
        max_input_bytes=config.max_input_bytes,
        max_input_lines=config.max_input_lines,
        before=config.window_before,
        after=config.window_after,
        max_windows=config.max_windows,
        max_lines=config.max_evidence_lines,
        max_estimated_tokens=config.max_estimated_tokens,
    )


def run_pipeline(
    path: Path,
    *,
    stage: str,
    config: PipelineConfig,
    client: OllamaClient | None = None,
) -> dict[str, Any]:
    if stage not in {"deterministic", "triage", "analysis", "auto"}:
        raise ValueError(f"Unsupported stage: {stage}")

    deterministic = _preprocess(path, config)
    report = _base_report(deterministic, stage=stage, config=config)
    if stage == "deterministic":
        return report
    if not deterministic.selected_lines:
        report["limitations"].append("The input contained no log lines.")
        return report
    if client is None:
        raise ValueError("An Ollama client is required for model stages")

    available_lines = set(deterministic.line_map())
    evidence_bundle = deterministic.evidence_bundle()

    if stage in {"triage", "auto"}:
        try:
            triage_response = client.chat(
                model=config.triage_model,
                schema=load_schema("triage"),
                system_prompt=load_prompt("triage"),
                evidence_bundle=evidence_bundle,
                num_ctx=config.num_ctx,
                num_predict=config.triage_num_predict,
            )
        except OllamaModelOutputError as exc:
            report["status"] = "model_output_rejected"
            report["limitations"].append(f"Triage rejected: {exc}")
            return report
        except OllamaError as exc:
            report["status"] = "model_unavailable"
            report["limitations"].append(str(exc))
            return report
        try:
            triage = validate_triage(
                triage_response.content,
                available_lines,
            )
        except ModelOutputValidationError as exc:
            report["status"] = "model_output_rejected"
            report["limitations"].append(f"Triage rejected: {exc}")
            return report
        report["triage"] = triage
        report["model_metrics"]["triage"] = triage_response.metrics
        report["effective_severity"] = effective_severity(
            deterministic.highest_severity,
            triage["severity"],
        )
        if stage == "triage":
            report["status"] = "triage_only"
            return report
        if not should_escalate(
            deterministic,
            triage,
            confidence_threshold=config.escalation_confidence,
        ):
            report["status"] = "triage_only"
            return report

    try:
        analysis_response = client.chat(
            model=config.analysis_model,
            schema=load_schema("analysis"),
            system_prompt=load_prompt("analysis"),
            evidence_bundle=evidence_bundle,
            num_ctx=config.num_ctx,
            num_predict=config.analysis_num_predict,
        )
    except OllamaModelOutputError as exc:
        report["status"] = "model_output_rejected"
        report["limitations"].append(f"Analysis rejected: {exc}")
        return report
    except OllamaError as exc:
        report["status"] = "model_unavailable"
        report["limitations"].append(str(exc))
        return report
    try:
        analysis = validate_analysis(
            analysis_response.content,
            deterministic.line_map(),
        )
    except ModelOutputValidationError as exc:
        report["status"] = "model_output_rejected"
        report["limitations"].append(f"Analysis rejected: {exc}")
        return report

    analysis = dict(analysis)
    report["analysis"] = analysis
    report["model_metrics"]["analysis"] = analysis_response.metrics
    report["effective_severity"] = effective_severity(
        deterministic.highest_severity,
        analysis["severity"],
    )
    if (
        deterministic.has_critical_pattern
        and analysis["severity"] != "critical"
    ):
        report["safety_overrides"].append(
            "Critical deterministic signal overrides lower model severity."
        )
    if deterministic.has_critical_pattern and not analysis[
        "needs_human_review"
    ]:
        analysis["needs_human_review"] = True
        report["safety_overrides"].append(
            "Critical deterministic signal requires human review."
        )
    report["status"] = (
        "analysis_only" if stage == "analysis" else "complete"
    )
    return report
