from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from embedded_log_analyzer.preprocess import (
    InputTooLargeError,
    preprocess_file,
)


class PreprocessTests(unittest.TestCase):
    def write_bytes(self, directory: str, data: bytes) -> Path:
        path = Path(directory) / "capture.log"
        path.write_bytes(data)
        return path

    def test_normalizes_and_redacts_common_secret_forms(self) -> None:
        raw = (
            b"\x1b[31m[00:00:00.000] Booting test\x1b[0m\r\n"
            b"[00:00:00.010] reset reason: power-on\r\n"
            b'password="hello world"\x00\r\n'
            b'{"token":"abc123","api_key":"xyz789"}\r\n'
            b"Authorization: Bearer bearer-value\r\n"
            b"-----BEGIN ENCRYPTED PRIVATE KEY-----\r\n"
            b"private-material\r\n"
            b"-----END ENCRYPTED PRIVATE KEY-----\r\n"
            b"[00:00:01.000] HardFault in synthetic_task\r\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(self.write_bytes(directory, raw))

        self.assertEqual(result.source_sha256, hashlib.sha256(raw).hexdigest())
        self.assertGreaterEqual(result.redactions, 7)
        selected = "\n".join(
            line.sanitized_text for line in result.selected_lines
        )
        for secret in (
            "hello world",
            "abc123",
            "xyz789",
            "bearer-value",
            "private-material",
        ):
            self.assertNotIn(secret, selected)
        self.assertNotIn("\x1b", selected)
        self.assertNotIn("\x00", selected)

    def test_watchdog_initialization_is_not_a_failure(self) -> None:
        data = (
            b"watchdog initialized interval=2000ms\n"
            b"watchdog reset triggered\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(self.write_bytes(directory, data))

        watchdog_lines = [
            signal.source_line
            for signal in result.signals
            if signal.rule_id == "watchdog_reset"
        ]
        self.assertEqual(watchdog_lines, [2])

    def test_boot_and_reset_reason_share_one_session(self) -> None:
        data = (
            b"Booting synthetic\n"
            b"reset reason: power-on\n"
            b"ready\n"
            b"Booting synthetic\n"
            b"reset reason: watchdog\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(self.write_bytes(directory, data))

        sessions = [line.session_id for line in result.selected_lines]
        self.assertEqual(
            sessions,
            [
                "session-001",
                "session-001",
                "session-001",
                "session-002",
                "session-002",
            ],
        )

    def test_single_long_line_obeys_token_budget(self) -> None:
        data = ("X" * 12000 + "\n").encode()
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(
                self.write_bytes(directory, data),
                max_estimated_tokens=100,
            )

        self.assertLessEqual(result.estimated_selected_tokens, 100)
        self.assertEqual(len(result.selected_lines), 1)
        self.assertIn("<TRUNCATED>", result.selected_lines[0].sanitized_text)

    def test_signal_anchors_survive_window_budget_truncation(self) -> None:
        lines = [f"line {number}: normal" for number in range(1, 1001)]
        for number in (100, 500, 900):
            lines[number - 1] = f"line {number}: HardFault synthetic"
        data = ("\n".join(lines) + "\n").encode()
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(self.write_bytes(directory, data))

        selected_numbers = {
            line.source_line for line in result.selected_lines
        }
        self.assertTrue({100, 500, 900}.issubset(selected_numbers))
        self.assertLessEqual(result.estimated_selected_tokens, 3000)
        self.assertLessEqual(len(result.selected_lines), 300)

    def test_long_first_signal_does_not_consume_other_anchor_budget(self) -> None:
        lines = [
            "HardFault " + ("X" * 12000),
            "normal context",
            "HardFault second",
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(
                self.write_bytes(
                    directory,
                    ("\n".join(lines) + "\n").encode(),
                ),
                before=0,
                after=0,
                max_estimated_tokens=100,
            )

        self.assertEqual(
            {line.source_line for line in result.selected_lines},
            {1, 3},
        )
        self.assertLessEqual(result.estimated_selected_tokens, 100)

    def test_no_signal_tail_preserves_source_numbers(self) -> None:
        data = "\n".join(f"healthy {number}" for number in range(1, 101))
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(
                self.write_bytes(directory, (data + "\n").encode())
            )

        self.assertEqual(result.selected_lines[0].source_line, 21)
        self.assertEqual(result.selected_lines[-1].source_line, 100)

    def test_repeated_signal_storm_has_bounded_representatives(self) -> None:
        data = ("error: repeated synthetic failure\n" * 2000).encode()
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(self.write_bytes(directory, data))

        report = result.deterministic_dict()
        self.assertEqual(result.signal_count_total, 2000)
        self.assertEqual(len(result.signals), 32)
        self.assertTrue(report["signals_truncated"])
        self.assertEqual(
            report["signal_counts_by_rule"]["explicit_failure"],
            2000,
        )
        self.assertLessEqual(len(result.selected_lines), 300)

    def test_physical_line_limit_rejects_pathological_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_bytes(directory, b"x\n" * 6)
            with self.assertRaises(InputTooLargeError):
                preprocess_file(path, max_input_lines=5)

    def test_non_crlf_unicode_separators_do_not_amplify_line_count(self) -> None:
        text = "alpha\vbeta\x85gamma\u2028delta\u2029omega"
        with tempfile.TemporaryDirectory() as directory:
            result = preprocess_file(
                self.write_bytes(directory, text.encode("utf-8")),
                max_input_lines=1,
            )

        self.assertEqual(result.lines_total, 1)
        sanitized = result.selected_lines[0].sanitized_text
        for separator in ("\v", "\x85", "\u2028", "\u2029"):
            self.assertNotIn(separator, sanitized)


if __name__ == "__main__":
    unittest.main()
