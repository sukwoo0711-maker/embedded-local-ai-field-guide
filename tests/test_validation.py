from __future__ import annotations

import unittest

from embedded_log_analyzer.schema import load_schema
from embedded_log_analyzer.validation import (
    CLASSIFICATIONS,
    ESCALATION_REASONS,
    ModelOutputValidationError,
    READ_ONLY_CHECKS,
    SEVERITIES,
    effective_severity,
    validate_analysis,
    validate_triage,
)


def valid_triage() -> dict:
    return {
        "classification": "possible_anomaly",
        "severity": "high",
        "components": ["watchdog"],
        "evidence_lines": [2],
        "needs_deep_analysis": True,
        "escalation_reason": "critical_pattern",
        "missing_evidence": [],
        "confidence": 0.8,
    }


def valid_analysis() -> dict:
    return {
        "verdict": "A watchdog reset is present in the supplied evidence.",
        "severity": "high",
        "components": ["watchdog"],
        "evidence_lines": [
            {"line_no": 2, "quote": "watchdog reset"}
        ],
        "observed_facts": [
            {"fact": "The log records a watchdog reset.", "line_numbers": [2]}
        ],
        "hypotheses": [
            {
                "statement": "Task starvation may have preceded the reset.",
                "supporting_lines": [2],
                "contradicting_lines": [],
                "confidence": 0.4,
            }
        ],
        "missing_evidence": ["Prior scheduler timing is not supplied."],
        "next_read_only_checks": [
            {
                "check_id": "compare_known_good",
                "rationale": "Compare the same bounded time window.",
            }
        ],
        "confidence": 0.7,
        "needs_human_review": True,
        "limitations": ["Only the supplied excerpt was evaluated."],
    }


class ValidationTests(unittest.TestCase):
    def test_valid_objects_pass(self) -> None:
        self.assertEqual(validate_triage(valid_triage(), {1, 2}), valid_triage())
        analysis = valid_analysis()
        self.assertEqual(
            validate_analysis(analysis, {2: "watchdog reset triggered"}),
            analysis,
        )

    def test_malformed_enum_values_fail_closed(self) -> None:
        cases = (
            ("classification", []),
            ("severity", {}),
            ("escalation_reason", None),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                item = valid_triage()
                item[field] = value
                with self.assertRaises(ModelOutputValidationError):
                    validate_triage(item, {2})

        item = valid_analysis()
        item["severity"] = []
        with self.assertRaises(ModelOutputValidationError):
            validate_analysis(item, {2: "watchdog reset triggered"})

        item = valid_analysis()
        item["next_read_only_checks"][0]["check_id"] = {}
        with self.assertRaises(ModelOutputValidationError):
            validate_analysis(item, {2: "watchdog reset triggered"})

    def test_bad_citation_or_quote_is_rejected(self) -> None:
        item = valid_analysis()
        item["evidence_lines"][0]["line_no"] = 99
        with self.assertRaises(ModelOutputValidationError):
            validate_analysis(item, {2: "watchdog reset triggered"})

        item = valid_analysis()
        item["evidence_lines"][0]["quote"] = "not present"
        with self.assertRaises(ModelOutputValidationError):
            validate_analysis(item, {2: "watchdog reset triggered"})

    def test_actionable_hardware_instruction_is_rejected(self) -> None:
        item = valid_analysis()
        item["verdict"] = "Reset the board and write the firmware image."
        with self.assertRaises(ModelOutputValidationError):
            validate_analysis(item, {2: "watchdog reset triggered"})

    def test_exact_untrusted_quote_may_contain_command_text(self) -> None:
        item = valid_analysis()
        item["evidence_lines"] = [
            {"line_no": 2, "quote": "run west flash"}
        ]
        item["observed_facts"] = [
            {
                "fact": "The log contains an untrusted command-like string.",
                "line_numbers": [2],
            }
        ]
        validate_analysis(item, {2: "payload says run west flash"})

    def test_effective_severity_never_lowers_deterministic_result(self) -> None:
        self.assertEqual(effective_severity("critical", "none"), "critical")

    def test_packaged_schema_enums_match_python_contract(self) -> None:
        triage = load_schema("triage")["properties"]
        analysis = load_schema("analysis")["properties"]
        self.assertEqual(set(triage["classification"]["enum"]), CLASSIFICATIONS)
        self.assertEqual(set(triage["severity"]["enum"]), SEVERITIES)
        self.assertEqual(
            set(triage["escalation_reason"]["enum"]),
            ESCALATION_REASONS,
        )
        check_enum = analysis["next_read_only_checks"]["items"][
            "properties"
        ]["check_id"]["enum"]
        self.assertEqual(set(check_enum), READ_ONLY_CHECKS)


if __name__ == "__main__":
    unittest.main()
