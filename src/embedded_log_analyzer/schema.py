from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


RESOURCE_PACKAGE = "embedded_log_analyzer.resources"


def load_schema(name: str) -> dict[str, Any]:
    allowed = {"triage", "analysis"}
    if name not in allowed:
        raise ValueError(f"Unknown schema: {name}")
    resource = files(RESOURCE_PACKAGE).joinpath(
        "schemas", f"{name}.schema.json"
    )
    with resource.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_prompt(name: str) -> str:
    allowed = {"triage", "analysis"}
    if name not in allowed:
        raise ValueError(f"Unknown prompt: {name}")
    resource = files(RESOURCE_PACKAGE).joinpath(
        "prompts", f"{name}.system.txt"
    )
    return resource.read_text(encoding="utf-8").strip()
