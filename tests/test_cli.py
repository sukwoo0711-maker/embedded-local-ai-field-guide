from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from embedded_log_analyzer.cli import main


class CliTests(unittest.TestCase):
    def test_default_deterministic_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.log"
            source.write_text("HardFault synthetic\n", encoding="utf-8")
            before = {path.name for path in root.iterdir()}
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["deterministic", str(source)])
            after = {path.name for path in root.iterdir()}

        self.assertEqual(exit_code, 0)
        self.assertEqual(before, after)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "deterministic_only")

    def test_explicit_output_is_exclusive_create(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.log"
            output = root / "results" / "report.json"
            source.write_text("healthy\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "deterministic",
                        str(source),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.exists())

            original = output.read_bytes()
            with (
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as raised,
            ):
                main(
                    [
                        "deterministic",
                        str(source),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(output.read_bytes(), original)

    def test_invalid_numeric_options_fail_before_analysis(self) -> None:
        bad_arguments = (
            ["deterministic", "missing.log", "--max-windows", "0"],
            ["deterministic", "missing.log", "--window-before", "-1"],
            ["deterministic", "missing.log", "--max-input-lines", "0"],
            [
                "analyze",
                "missing.log",
                "--context",
                "0",
            ],
            [
                "analyze",
                "missing.log",
                "--escalation-confidence",
                "2",
            ],
        )
        for arguments in bad_arguments:
            with self.subTest(arguments=arguments):
                with (
                    redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as raised,
                ):
                    main(arguments)
                self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
