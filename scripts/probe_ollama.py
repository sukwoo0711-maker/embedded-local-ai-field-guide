#!/usr/bin/env python3
"""Measure one local Ollama generation and print a JSON record to stdout."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib import error, parse, request


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def request_json(
    opener: request.OpenerDirector,
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(
        f"{base_url}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    with opener.open(req, timeout=timeout) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise RuntimeError("Ollama response exceeded 2 MiB")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise RuntimeError("Ollama returned a non-object response")
    return decoded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Opt-in local Ollama memory/timing probe"
    )
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--context", type=int, default=8192)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:11434",
    )
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    base_url = args.base_url.rstrip("/")
    parsed = parse.urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname is None
        or parsed.hostname.lower() not in LOOPBACK_HOSTS
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit("Only a credential-free loopback HTTP URL is allowed")
    if not 512 <= args.context <= 131072:
        raise SystemExit("--context must be within 512..131072")
    if not 0 < args.timeout_seconds <= 3600:
        raise SystemExit("--timeout-seconds must be within 0..3600")

    opener = request.build_opener(
        request.ProxyHandler({}),
        request.HTTPHandler(),
    )
    generation: dict[str, Any] | None = None
    running: dict[str, Any] | None = None
    try:
        generation = request_json(
            opener,
            base_url,
            "/api/generate",
            method="POST",
            payload={
                "model": args.model,
                "prompt": "Reply with exactly: OK",
                "stream": False,
                "keep_alive": "10s",
                "think": False,
                "options": {
                    "num_ctx": args.context,
                    "num_predict": 8,
                    "temperature": 0,
                    "seed": 42,
                },
            },
            timeout=args.timeout_seconds,
        )
        running = request_json(
            opener,
            base_url,
            "/api/ps",
            timeout=args.timeout_seconds,
        )
    except (
        error.HTTPError,
        error.URLError,
        TimeoutError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 3
    finally:
        try:
            request_json(
                opener,
                base_url,
                "/api/generate",
                method="POST",
                payload={
                    "model": args.model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": 0,
                },
                timeout=min(args.timeout_seconds, 30.0),
            )
        except Exception:
            pass

    metric_keys = (
        "model",
        "created_at",
        "done_reason",
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "prompt_eval_duration",
        "eval_count",
        "eval_duration",
    )
    models = running.get("models", []) if running else []
    matching = [
        model
        for model in models
        if isinstance(model, dict)
        and model.get("name") in {args.model, f"{args.model}:latest"}
    ]
    result = {
        "status": "complete",
        "model_requested": args.model,
        "context_requested": args.context,
        "metrics": {
            key: generation[key]
            for key in metric_keys
            if generation is not None and key in generation
        },
        "runtime_model": matching[0] if matching else None,
        "notes": [
            "This is a single-host observation, not an RTX 3050 benchmark.",
            "The script unloads the model after collecting /api/ps.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
