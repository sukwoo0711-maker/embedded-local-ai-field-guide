from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from embedded_log_analyzer.ollama_client import (
    OllamaError,
    OllamaModelOutputError,
    OllamaResponse,
)
from embedded_log_analyzer.pipeline import PipelineConfig, run_pipeline


def triage(
    *,
    classification: str = "possible_anomaly",
    severity: str = "high",
    evidence_lines: list[int] | None = None,
    needs_deep_analysis: bool = True,
    confidence: float = 0.8,
) -> dict:
    return {
        "classification": classification,
        "severity": severity,
        "components": [] if severity == "none" else ["cpu"],
        "evidence_lines": (
            evidence_lines
            if evidence_lines is not None
            else ([] if severity == "none" else [2])
        ),
        "needs_deep_analysis": needs_deep_analysis,
        "escalation_reason": (
            "none" if not needs_deep_analysis else "critical_pattern"
        ),
        "missing_evidence": [],
        "confidence": confidence,
    }


def analysis(*, severity: str = "low") -> dict:
    return {
        "verdict": "A HardFault is recorded in the supplied log.",
        "severity": severity,
        "components": ["cpu"],
        "evidence_lines": [{"line_no": 2, "quote": "HardFault"}],
        "observed_facts": [
            {"fact": "A HardFault is recorded.", "line_numbers": [2]}
        ],
        "hypotheses": [],
        "missing_evidence": [],
        "next_read_only_checks": [
            {
                "check_id": "review_source_at_symbol",
                "rationale": "Inspect the implicated symbol read-only.",
            }
        ],
        "confidence": 0.8,
        "needs_human_review": False,
        "limitations": ["Synthetic fixture only."],
    }


class FakeClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.models: list[str] = []

    def chat(self, *, model: str, **kwargs) -> OllamaResponse:
        self.models.append(model)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return OllamaResponse(outcome, {"model": model})


class PipelineTests(unittest.TestCase):
    def write_log(self, directory: str, text: str) -> Path:
        path = Path(directory) / "fixture.log"
        path.write_text(text, encoding="utf-8")
        return path

    def test_critical_signal_escalates_and_forces_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_log(
                directory,
                "Booting synthetic\nHardFault in sensor_task\n",
            )
            client = FakeClient([triage(), analysis(severity="low")])
            report = run_pipeline(
                path,
                stage="auto",
                config=PipelineConfig(),
                client=client,
            )

        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["effective_severity"], "critical")
        self.assertEqual(len(client.models), 2)
        self.assertTrue(report["analysis"]["needs_human_review"])
        self.assertEqual(len(report["safety_overrides"]), 2)

    def test_clean_high_confidence_triage_does_not_escalate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_log(directory, "Booting synthetic\nhealthy\n")
            client = FakeClient(
                [
                    triage(
                        classification="no_anomaly",
                        severity="none",
                        needs_deep_analysis=False,
                        confidence=0.95,
                    )
                ]
            )
            report = run_pipeline(
                path,
                stage="auto",
                config=PipelineConfig(),
                client=client,
            )

        self.assertEqual(report["status"], "triage_only")
        self.assertEqual(len(client.models), 1)

    def test_malformed_triage_does_not_fall_through_to_9b(self) -> None:
        malformed = triage()
        malformed["classification"] = []
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_log(
                directory,
                "Booting synthetic\nHardFault in sensor_task\n",
            )
            client = FakeClient([malformed, analysis()])
            report = run_pipeline(
                path,
                stage="auto",
                config=PipelineConfig(),
                client=client,
            )

        self.assertEqual(report["status"], "model_output_rejected")
        self.assertEqual(len(client.models), 1)

    def test_transport_and_model_content_errors_are_distinct(self) -> None:
        cases = (
            (OllamaError("offline"), "model_unavailable"),
            (
                OllamaModelOutputError("invalid model JSON"),
                "model_output_rejected",
            ),
        )
        for error, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_log(directory, "healthy\n")
                    report = run_pipeline(
                        path,
                        stage="triage",
                        config=PipelineConfig(),
                        client=FakeClient([error]),
                    )
                self.assertEqual(report["status"], expected)
                self.assertIsNotNone(report["deterministic"])

    def test_direct_analysis_has_explicit_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_log(
                directory,
                "Booting synthetic\nHardFault in sensor_task\n",
            )
            report = run_pipeline(
                path,
                stage="analysis",
                config=PipelineConfig(),
                client=FakeClient([analysis()]),
            )
        self.assertEqual(report["status"], "analysis_only")


if __name__ == "__main__":
    unittest.main()
