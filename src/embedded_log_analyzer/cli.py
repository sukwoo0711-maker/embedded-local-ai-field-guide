from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Sequence

from . import __version__
from .ollama_client import OllamaClient, OllamaError
from .memory_ledger import LedgerValidationError, validate_ledger
from .pipeline import PipelineConfig, run_pipeline
from .preprocess import InputChangedError, InputTooLargeError


SUCCESS_STATUSES = {
    "complete",
    "analysis_only",
    "triage_only",
    "deterministic_only",
}


def _normalise_base_url(value: str) -> str:
    if "://" not in value:
        return f"http://{value}"
    return value


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _integer_range(
    minimum: int,
    maximum: int,
    label: str,
):
    def parse_value(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"{label} must be an integer"
            ) from exc
        if not minimum <= value <= maximum:
            raise argparse.ArgumentTypeError(
                f"{label} must be within {minimum}..{maximum}"
            )
        return value

    return parse_value


def _float_range(
    minimum: float,
    maximum: float,
    label: str,
):
    def parse_value(raw: str) -> float:
        try:
            value = float(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"{label} must be numeric"
            ) from exc
        if not minimum <= value <= maximum:
            raise argparse.ArgumentTypeError(
                f"{label} must be within {minimum}..{maximum}"
            )
        return value

    return parse_value


def _write_or_print(value: Any, output: Path | None) -> None:
    text = _json_text(value)
    if output is None:
        sys.stdout.write(text)
        return
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    sys.stdout.write(
        _json_text(
            {
                "written": str(output),
                "overwrite": False,
            }
        )
    )


def _add_input_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", type=Path, help="UART/HIL log to read")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument(
        "--max-input-mb",
        type=_integer_range(1, 10240, "max input MiB"),
        default=50,
    )
    parser.add_argument(
        "--max-input-lines",
        type=_integer_range(1, 2_000_000, "max-input-lines"),
        default=250_000,
    )
    parser.add_argument(
        "--window-before",
        type=_integer_range(0, 10000, "window-before"),
        default=80,
    )
    parser.add_argument(
        "--window-after",
        type=_integer_range(0, 10000, "window-after"),
        default=40,
    )
    parser.add_argument(
        "--max-windows",
        type=_integer_range(1, 100, "max-windows"),
        default=3,
    )
    parser.add_argument(
        "--max-evidence-lines",
        type=_integer_range(1, 10000, "max-evidence-lines"),
        default=300,
    )
    parser.add_argument(
        "--max-estimated-tokens",
        type=_integer_range(64, 131072, "max-estimated-tokens"),
        default=3000,
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a new JSON file; existing files are never overwritten",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embedded-log-analyzer",
        description="Bounded local embedded-log analysis",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    deterministic = subparsers.add_parser(
        "deterministic",
        help="Run normalization and rule detectors only",
    )
    _add_input_options(deterministic)

    analyze = subparsers.add_parser(
        "analyze",
        help="Run bounded Ollama analysis",
    )
    _add_input_options(analyze)
    analyze.add_argument(
        "--stage",
        choices=("auto", "triage", "analysis"),
        default="auto",
    )
    analyze.add_argument(
        "--base-url",
        default=os.environ.get("OLLAMA_HOST", "127.0.0.1:11434"),
    )
    analyze.add_argument(
        "--allow-remote",
        action="store_true",
        help="Explicitly allow a non-loopback Ollama endpoint",
    )
    analyze.add_argument(
        "--timeout-seconds",
        type=_float_range(0.1, 3600.0, "timeout-seconds"),
        default=300.0,
    )
    analyze.add_argument(
        "--triage-model",
        default=os.environ.get(
            "EMBEDDED_LOG_TRIAGE_MODEL",
            "embedded-log-triage:4b",
        ),
    )
    analyze.add_argument(
        "--analysis-model",
        default=os.environ.get(
            "EMBEDDED_LOG_ANALYSIS_MODEL",
            "embedded-log-analysis:9b",
        ),
    )
    analyze.add_argument(
        "--context",
        type=_integer_range(512, 131072, "context"),
        default=8192,
    )
    analyze.add_argument(
        "--escalation-confidence",
        type=_float_range(0.0, 1.0, "escalation-confidence"),
        default=0.65,
    )

    doctor = subparsers.add_parser(
        "doctor",
        help="Read-only Ollama API and model check",
    )
    doctor.add_argument(
        "--base-url",
        default=os.environ.get("OLLAMA_HOST", "127.0.0.1:11434"),
    )
    doctor.add_argument("--allow-remote", action="store_true")
    doctor.add_argument(
        "--timeout-seconds",
        type=_float_range(0.1, 3600.0, "timeout-seconds"),
        default=10.0,
    )
    doctor.add_argument(
        "--triage-model",
        default="embedded-log-triage:4b",
    )
    doctor.add_argument(
        "--analysis-model",
        default="embedded-log-analysis:9b",
    )

    ledger = subparsers.add_parser(
        "validate-ledger",
        help="Validate an append-only JSONL project-memory ledger",
    )
    ledger.add_argument("input", type=Path)
    return parser


def _config_from_args(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        triage_model=getattr(
            args, "triage_model", "embedded-log-triage:4b"
        ),
        analysis_model=getattr(
            args, "analysis_model", "embedded-log-analysis:9b"
        ),
        num_ctx=getattr(args, "context", 8192),
        escalation_confidence=getattr(
            args, "escalation_confidence", 0.65
        ),
        encoding=args.encoding,
        max_input_bytes=args.max_input_mb * 1024 * 1024,
        max_input_lines=args.max_input_lines,
        window_before=args.window_before,
        window_after=args.window_after,
        max_windows=args.max_windows,
        max_evidence_lines=args.max_evidence_lines,
        max_estimated_tokens=args.max_estimated_tokens,
    )


def _run_doctor(args: argparse.Namespace) -> int:
    base_url = _normalise_base_url(args.base_url)
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "base_url": base_url,
        "remote_allowed": bool(args.allow_remote),
        "api_reachable": False,
        "ready": False,
        "version": None,
        "required_models": {
            args.triage_model: False,
            args.analysis_model: False,
        },
        "errors": [],
    }
    try:
        client = OllamaClient(
            base_url,
            timeout_seconds=args.timeout_seconds,
            allow_remote=args.allow_remote,
        )
        result["version"] = client.version().get("version")
        tags = client.tags().get("models", [])
        names = {
            model.get("name")
            for model in tags
            if isinstance(model, dict)
        }
        result["api_reachable"] = True
        result["required_models"] = {
            name: name in names for name in result["required_models"]
        }
        result["ready"] = all(result["required_models"].values())
    except (ValueError, OllamaError) as exc:
        result["errors"].append(str(exc))
    sys.stdout.write(_json_text(result))
    if not result["api_reachable"]:
        return 3
    return 0 if result["ready"] else 4


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate-ledger":
        try:
            sys.stdout.write(_json_text(validate_ledger(args.input)))
            return 0
        except FileNotFoundError:
            parser.error(f"Input not found: {args.input}")
        except LedgerValidationError as exc:
            sys.stderr.write(f"invalid_ledger: {exc}\n")
            return 5
    if args.command == "doctor":
        return _run_doctor(args)

    stage = (
        "deterministic"
        if args.command == "deterministic"
        else args.stage
    )
    config = _config_from_args(args)
    client = None
    try:
        if args.output is not None and args.output.exists():
            parser.error(f"Output already exists: {args.output}")
        if stage != "deterministic":
            client = OllamaClient(
                _normalise_base_url(args.base_url),
                timeout_seconds=args.timeout_seconds,
                allow_remote=args.allow_remote,
            )
        report = run_pipeline(
            args.input,
            stage=stage,
            config=config,
            client=client,
        )
        _write_or_print(report, args.output)
        return 0 if report["status"] in SUCCESS_STATUSES else 3
    except FileExistsError:
        parser.error(f"Output already exists: {args.output}")
    except FileNotFoundError as exc:
        parser.error(f"Input not found: {exc.filename}")
    except PermissionError as exc:
        parser.error(f"Permission denied: {exc.filename}")
    except InputTooLargeError as exc:
        parser.error(str(exc))
    except InputChangedError as exc:
        sys.stderr.write(f"input_changed_during_read: {exc}\n")
        return 4
    except (ValueError, LookupError) as exc:
        parser.error(str(exc))
    return 2
