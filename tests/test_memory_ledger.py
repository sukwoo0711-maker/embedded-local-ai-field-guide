from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from embedded_log_analyzer.memory_ledger import (
    LedgerValidationError,
    validate_ledger,
)


class MemoryLedgerTests(unittest.TestCase):
    def test_synthetic_ledger_is_valid(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = validate_ledger(root / "samples" / "project-memory.synthetic.jsonl")
        self.assertTrue(report["valid"])
        self.assertEqual(report["events"], 3)
        self.assertEqual(report["counts"]["attempt"], 1)

    def test_synthetic_evidence_hash_matches_artifact(self) -> None:
        root = Path(__file__).resolve().parents[1]
        import hashlib

        artifact = root / "samples" / "uart-watchdog.synthetic.log"
        expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
        first = json.loads(
            (root / "samples" / "project-memory.synthetic.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        self.assertEqual(first["evidence"][0]["sha256"], expected)

    def test_forward_reference_is_rejected(self) -> None:
        event = {
            "schema_version": "1.0",
            "event_id": "EV-20260722-0001",
            "timestamp_utc": "2026-07-22T01:00:00Z",
            "event_type": "issue",
            "status": "proposed",
            "sensitivity": "public",
            "summary": "Synthetic issue",
            "source_commit": None,
            "model_generated": False,
            "references": ["EV-20260722-0002"],
            "evidence": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(LedgerValidationError, "point backward"):
                validate_ledger(path)

    def test_verified_without_evidence_is_rejected(self) -> None:
        event = {
            "schema_version": "1.0",
            "event_id": "EV-20260722-0001",
            "timestamp_utc": "2026-07-22T01:00:00Z",
            "event_type": "observation",
            "status": "verified",
            "sensitivity": "public",
            "summary": "Unsupported fact",
            "source_commit": None,
            "model_generated": True,
            "references": [],
            "evidence": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(LedgerValidationError, "require evidence"):
                validate_ledger(path)


if __name__ == "__main__":
    unittest.main()
