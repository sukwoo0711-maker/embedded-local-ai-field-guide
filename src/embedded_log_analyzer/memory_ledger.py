from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any


EVENT_TYPES = {
    "observation",
    "issue",
    "attempt",
    "result",
    "decision",
    "note",
}
STATUSES = {"proposed", "verified", "rejected", "superseded"}
SENSITIVITY = {"public", "internal", "restricted"}
EVENT_ID_RE = re.compile(r"^EV-[0-9]{8}-[0-9]{4}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class LedgerValidationError(ValueError):
    pass


def _require_text(event: dict[str, Any], key: str, line_no: int) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LedgerValidationError(f"line {line_no}: {key} must be non-empty text")
    return value


def _validate_timestamp(value: str, line_no: int) -> None:
    if not value.endswith("Z"):
        raise LedgerValidationError(f"line {line_no}: timestamp_utc must end in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LedgerValidationError(
            f"line {line_no}: timestamp_utc is not ISO-8601"
        ) from exc


def validate_event(
    event: Any,
    *,
    line_no: int,
    prior_ids: set[str],
) -> str:
    if not isinstance(event, dict):
        raise LedgerValidationError(f"line {line_no}: event must be an object")
    if event.get("schema_version") != "1.0":
        raise LedgerValidationError(f"line {line_no}: schema_version must be 1.0")

    event_id = _require_text(event, "event_id", line_no)
    if not EVENT_ID_RE.fullmatch(event_id):
        raise LedgerValidationError(f"line {line_no}: invalid event_id {event_id!r}")
    if event_id in prior_ids:
        raise LedgerValidationError(f"line {line_no}: duplicate event_id {event_id}")

    timestamp = _require_text(event, "timestamp_utc", line_no)
    _validate_timestamp(timestamp, line_no)
    event_type = _require_text(event, "event_type", line_no)
    if event_type not in EVENT_TYPES:
        raise LedgerValidationError(f"line {line_no}: unsupported event_type {event_type}")
    status = _require_text(event, "status", line_no)
    if status not in STATUSES:
        raise LedgerValidationError(f"line {line_no}: unsupported status {status}")
    sensitivity = _require_text(event, "sensitivity", line_no)
    if sensitivity not in SENSITIVITY:
        raise LedgerValidationError(
            f"line {line_no}: unsupported sensitivity {sensitivity}"
        )
    _require_text(event, "summary", line_no)

    source_commit = event.get("source_commit")
    if source_commit is not None and (
        not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit)
    ):
        raise LedgerValidationError(
            f"line {line_no}: source_commit must be null or 40 lowercase hex"
        )

    if not isinstance(event.get("model_generated"), bool):
        raise LedgerValidationError(f"line {line_no}: model_generated must be boolean")

    references = event.get("references")
    if not isinstance(references, list) or not all(
        isinstance(item, str) for item in references
    ):
        raise LedgerValidationError(f"line {line_no}: references must be a string array")
    missing = sorted(set(references) - prior_ids)
    if missing:
        raise LedgerValidationError(
            f"line {line_no}: references must point backward; missing {missing}"
        )
    if event_type in {"attempt", "result"} and not references:
        raise LedgerValidationError(
            f"line {line_no}: {event_type} requires at least one prior reference"
        )

    evidence = event.get("evidence")
    if not isinstance(evidence, list):
        raise LedgerValidationError(f"line {line_no}: evidence must be an array")
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise LedgerValidationError(
                f"line {line_no}: evidence[{index}] must be an object"
            )
        for key in ("artifact_id", "sha256", "locator"):
            _require_text(item, key, line_no)
        if not SHA256_RE.fullmatch(item["sha256"]):
            raise LedgerValidationError(
                f"line {line_no}: evidence[{index}].sha256 must be 64 lowercase hex"
            )
    if status == "verified" and not evidence:
        raise LedgerValidationError(
            f"line {line_no}: verified events require evidence"
        )
    return event_id


def validate_ledger(path: Path) -> dict[str, Any]:
    prior_ids: set[str] = set()
    counts = {event_type: 0 for event_type in sorted(EVENT_TYPES)}
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            digest.update(raw_line)
            if not raw_line.strip():
                raise LedgerValidationError(f"line {line_no}: blank lines are not allowed")
            try:
                event = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LedgerValidationError(f"line {line_no}: invalid UTF-8 JSON") from exc
            event_id = validate_event(event, line_no=line_no, prior_ids=prior_ids)
            prior_ids.add(event_id)
            counts[event["event_type"]] += 1
    return {
        "schema_version": "1.0",
        "valid": True,
        "events": len(prior_ids),
        "counts": counts,
        "sha256": digest.hexdigest(),
    }
