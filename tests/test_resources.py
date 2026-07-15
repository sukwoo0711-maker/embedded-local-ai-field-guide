from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import unittest

from embedded_log_analyzer.schema import load_prompt, load_schema


class ResourceTests(unittest.TestCase):
    def test_public_and_packaged_resources_are_in_sync(self) -> None:
        root = Path(__file__).resolve().parents[1]
        package = files("embedded_log_analyzer.resources")
        for name in ("triage", "analysis"):
            with self.subTest(kind="schema", name=name):
                public = (
                    root / "schemas" / f"{name}.schema.json"
                ).read_text(encoding="utf-8")
                packaged = package.joinpath(
                    "schemas", f"{name}.schema.json"
                ).read_text(encoding="utf-8")
                self.assertEqual(public, packaged)
                self.assertIsInstance(load_schema(name), dict)

            with self.subTest(kind="prompt", name=name):
                public = (
                    root / "prompts" / f"{name}.system.txt"
                ).read_text(encoding="utf-8").strip()
                packaged = package.joinpath(
                    "prompts", f"{name}.system.txt"
                ).read_text(encoding="utf-8").strip()
                self.assertEqual(public, packaged)
                self.assertEqual(load_prompt(name), packaged)


if __name__ == "__main__":
    unittest.main()
