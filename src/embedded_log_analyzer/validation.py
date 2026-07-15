from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .preprocess import SEVERITY_ORDER


TRIAGE_KEYS = {
    "classification",
    "severity",
    "components",
    "evidence_lines",
    "needs_deep_analysis",
    "escalation_reason",
    "missing_evidence",
    "confidence",
}
ANALYSIS_KEYS = {
    "verdict",
    "severity",
    "components",
    "evidence_lines",
    "observed_facts",
    "hypotheses",
    "missing_evidence",
    "next_read_only_checks",
    "confidence",
    "needs_human_review",
    "limitations",
}
CLASSIFICATIONS = {
    "known_pattern",
    "possible_anomaly",
    "insufficient_evidence",
    "no_anomaly",
}
SEVERITIES = set(SEVERITY_ORDER)
ESCALATION_REASONS = {
    "critical_pattern",
    "cross_component",
    "low_confidence",
    "unknown_signature",
    "none",
}
READ_ONLY_CHECKS = {
    "inspect_prior_boot",
    "compare_known_good",
    "inspect_reset_register_decode",
    "inspect_build_metadata",
    "rerun_read_only_capture",
    "review_source_at_symbol",
    "none",
}
FORBIDDEN_OUTPUT_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\b[A-Za-z]:[\\/][^\s]+"),
    re.compile(r"(?:^|\s)/(?:[A-Za-z0-9._-]+/)+[^\s]+"),
    re.compile(r"\\\\[^\\\s]+\\[^\\\s]+"),
    re.compile(
        r"\b(?:rm\s+-rf|del\s+/[fsq]|format\s+[A-Za-z]:|"
        r"flash_tool|openocd|pyocd|nrfjprog|west\s+flash|"
        r"curl|wget|powershell|cmd\.exe)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reboot|restart|reset|power[- ]?cycle|flash|erase|write|"
        r"delete)\s+(?:the\s+)?(?:dut|device|target|board|firmware|"
        r"image|flash|filesystem|file)\b",
        re.IGNORECASE,
    ),
)


class ModelOutputValidationError(ValueError):
    pass


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModelOutputValidationError(f"{label} must be an object")
    return value


def _exact_keys(
    value: dict[str, Any], expected: set[str], label: str
) -> None:
    missing = expected - set(value)
    extra = set(value) - expected
    if missing or extra:
        raise ModelOutputValidationError(
            f"{label} keys mismatch; missing={sorted(missing)}, "
            f"extra={sorted(extra)}"
        )


def _require_string(
    value: Any, label: str, *, minimum: int = 0, maximum: int = 320
) -> str:
    if not isinstance(value, str):
        raise ModelOutputValidationError(f"{label} must be a string")
    if not minimum <= len(value) <= maximum:
        raise ModelOutputValidationError(
            f"{label} length must be {minimum}..{maximum}"
        )
    return value


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ModelOutputValidationError(f"{label} must be boolean")
    return value


def _require_confidence(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelOutputValidationError(f"{label} must be numeric")
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise ModelOutputValidationError(f"{label} must be within 0..1")
    return numeric


def _require_enum(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ModelOutputValidationError(f"Invalid {label}")
    return value


def _require_line_number(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ModelOutputValidationError(
            f"{label} must be a positive integer"
        )
    return value


def _require_list(
    value: Any,
    label: str,
    *,
    maximum: int,
    minimum: int = 0,
) -> list[Any]:
    if not isinstance(value, list):
        raise ModelOutputValidationError(f"{label} must be an array")
    if not minimum <= len(value) <= maximum:
        raise ModelOutputValidationError(
            f"{label} length must be {minimum}..{maximum}"
        )
    return value


def _validate_string_list(
    value: Any,
    label: str,
    *,
    maximum: int,
    item_maximum: int,
    unique: bool = False,
) -> list[str]:
    items = _require_list(value, label, maximum=maximum)
    output = [
        _require_string(
            item,
            f"{label}[{index}]",
            maximum=item_maximum,
        )
        for index, item in enumerate(items)
    ]
    if unique and len(set(output)) != len(output):
        raise ModelOutputValidationError(f"{label} must be unique")
    return output


def _validate_line_list(
    value: Any,
    label: str,
    *,
    maximum: int,
    available_lines: set[int],
    minimum: int = 0,
) -> list[int]:
    items = _require_list(
        value,
        label,
        maximum=maximum,
        minimum=minimum,
    )
    output = [
        _require_line_number(item, f"{label}[{index}]")
        for index, item in enumerate(items)
    ]
    if len(set(output)) != len(output):
        raise ModelOutputValidationError(f"{label} must be unique")
    unknown = set(output) - available_lines
    if unknown:
        raise ModelOutputValidationError(
            f"{label} cites unavailable lines: {sorted(unknown)}"
        )
    return output


def _all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _all_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _all_strings(nested)


def _reject_unsafe_output(value: Any) -> None:
    for text in _all_strings(value):
        for pattern in FORBIDDEN_OUTPUT_PATTERNS:
            if pattern.search(text):
                raise ModelOutputValidationError(
                    "Model output contains a forbidden command, URL, or path"
                )


def validate_triage(
    value: Any,
    available_lines: set[int],
) -> dict[str, Any]:
    obj = _require_object(value, "triage")
    _exact_keys(obj, TRIAGE_KEYS, "triage")
    _require_enum(
        obj["classification"],
        CLASSIFICATIONS,
        "triage classification",
    )
    _require_enum(obj["severity"], SEVERITIES, "triage severity")
    _validate_string_list(
        obj["components"],
        "components",
        maximum=5,
        item_maximum=64,
        unique=True,
    )
    lines = _validate_line_list(
        obj["evidence_lines"],
        "evidence_lines",
        maximum=12,
        available_lines=available_lines,
    )
    _require_bool(obj["needs_deep_analysis"], "needs_deep_analysis")
    _require_enum(
        obj["escalation_reason"],
        ESCALATION_REASONS,
        "escalation_reason",
    )
    _validate_string_list(
        obj["missing_evidence"],
        "missing_evidence",
        maximum=8,
        item_maximum=160,
    )
    _require_confidence(obj["confidence"], "confidence")
    if obj["severity"] != "none" and not lines:
        raise ModelOutputValidationError(
            "Non-none severity requires evidence_lines"
        )
    _reject_unsafe_output(obj)
    return obj


def validate_analysis(
    value: Any,
    line_map: dict[int, str],
) -> dict[str, Any]:
    obj = _require_object(value, "analysis")
    _exact_keys(obj, ANALYSIS_KEYS, "analysis")
    _require_string(obj["verdict"], "verdict", minimum=1, maximum=320)
    _require_enum(obj["severity"], SEVERITIES, "analysis severity")
    _validate_string_list(
        obj["components"],
        "components",
        maximum=8,
        item_maximum=64,
        unique=True,
    )
    available = set(line_map)

    evidence = _require_list(
        obj["evidence_lines"],
        "evidence_lines",
        maximum=16,
    )
    for index, entry_value in enumerate(evidence):
        entry = _require_object(
            entry_value, f"evidence_lines[{index}]"
        )
        _exact_keys(
            entry,
            {"line_no", "quote"},
            f"evidence_lines[{index}]",
        )
        line_no = _require_line_number(
            entry["line_no"], f"evidence_lines[{index}].line_no"
        )
        quote = _require_string(
            entry["quote"],
            f"evidence_lines[{index}].quote",
            minimum=1,
            maximum=240,
        )
        if line_no not in available:
            raise ModelOutputValidationError(
                f"Evidence cites unavailable line {line_no}"
            )
        if quote not in line_map[line_no]:
            raise ModelOutputValidationError(
                f"Quote is not present on sanitized line {line_no}"
            )

    facts = _require_list(
        obj["observed_facts"],
        "observed_facts",
        maximum=12,
    )
    for index, fact_value in enumerate(facts):
        fact = _require_object(fact_value, f"observed_facts[{index}]")
        _exact_keys(
            fact,
            {"fact", "line_numbers"},
            f"observed_facts[{index}]",
        )
        _require_string(
            fact["fact"],
            f"observed_facts[{index}].fact",
            minimum=1,
            maximum=240,
        )
        _validate_line_list(
            fact["line_numbers"],
            f"observed_facts[{index}].line_numbers",
            maximum=8,
            minimum=1,
            available_lines=available,
        )

    hypotheses = _require_list(
        obj["hypotheses"],
        "hypotheses",
        maximum=8,
    )
    for index, hypothesis_value in enumerate(hypotheses):
        hypothesis = _require_object(
            hypothesis_value, f"hypotheses[{index}]"
        )
        _exact_keys(
            hypothesis,
            {
                "statement",
                "supporting_lines",
                "contradicting_lines",
                "confidence",
            },
            f"hypotheses[{index}]",
        )
        _require_string(
            hypothesis["statement"],
            f"hypotheses[{index}].statement",
            minimum=1,
            maximum=240,
        )
        _validate_line_list(
            hypothesis["supporting_lines"],
            f"hypotheses[{index}].supporting_lines",
            maximum=8,
            available_lines=available,
        )
        _validate_line_list(
            hypothesis["contradicting_lines"],
            f"hypotheses[{index}].contradicting_lines",
            maximum=8,
            available_lines=available,
        )
        _require_confidence(
            hypothesis["confidence"],
            f"hypotheses[{index}].confidence",
        )

    _validate_string_list(
        obj["missing_evidence"],
        "missing_evidence",
        maximum=12,
        item_maximum=200,
    )
    checks = _require_list(
        obj["next_read_only_checks"],
        "next_read_only_checks",
        maximum=6,
    )
    for index, check_value in enumerate(checks):
        check = _require_object(
            check_value, f"next_read_only_checks[{index}]"
        )
        _exact_keys(
            check,
            {"check_id", "rationale"},
            f"next_read_only_checks[{index}]",
        )
        _require_enum(
            check["check_id"],
            READ_ONLY_CHECKS,
            f"check_id at index {index}",
        )
        _require_string(
            check["rationale"],
            f"next_read_only_checks[{index}].rationale",
            minimum=1,
            maximum=200,
        )

    _require_confidence(obj["confidence"], "confidence")
    _require_bool(obj["needs_human_review"], "needs_human_review")
    _validate_string_list(
        obj["limitations"],
        "limitations",
        maximum=8,
        item_maximum=200,
    )
    if obj["severity"] != "none" and not evidence:
        raise ModelOutputValidationError(
            "Non-none severity requires evidence_lines"
        )
    _reject_unsafe_output(
        {
            "verdict": obj["verdict"],
            "missing_evidence": obj["missing_evidence"],
            "next_read_only_checks": obj["next_read_only_checks"],
            "limitations": obj["limitations"],
        }
    )
    return obj


def effective_severity(
    deterministic_severity: str,
    model_severity: str | None,
) -> str:
    values = [deterministic_severity]
    if model_severity is not None:
        values.append(model_severity)
    return max(values, key=SEVERITY_ORDER.__getitem__)


def stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
