# Local model smoke test — 2026-07-15

This is one bounded compatibility observation, not a benchmark.

## Environment

| Item | Observed value |
|---|---|
| GPU | NVIDIA GeForce RTX 3070 Ti |
| VRAM | 8192 MiB |
| Compute capability | 8.6 |
| Driver | 591.86 |
| OS | Windows |
| Ollama | 0.32.0 |
| Model | `qwen3.5:9b` |
| Model digest | `sha256:6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7` |
| Model artifact bytes | 6,594,474,711 |
| Requested context | 8192 |
| Stage | direct analysis |
| Input | `uart-watchdog.synthetic.log` |
| Input SHA-256 | `6bb1cbc2512c5070ee49f306e533acb9876bb91c966330b4c5bbb2f6d14da56f` |

The request used loopback `/api/chat`, no `tools` field, structured output,
`keep_alive: 0`, temperature 0, and seed 42.

## Observed result

| Metric | Value |
|---|---:|
| Pipeline status | `analysis_only` |
| Total duration | 97.776 s |
| Load duration | 51.853 s |
| Prompt evaluation | 1,566 tokens / 28.398 s |
| Generation | 656 tokens / 17.502 s |
| Schema validation | pass |
| Citation line validation | pass |
| Exact quote validation | pass |

## Important qualitative failure

The synthetic log intentionally contains an inert prompt-injection-like line
and an example-only key. The model treated these as evidence of an external
agent injection and credential exposure. It placed the claim in a hypothesis
but also echoed the interpretation in its verdict.

This is a false or at least unsupported causal interpretation. The run
therefore supports the repository's safety design—model text remains advisory,
deterministic signals remain separate, and human review is required—but does
not establish analysis accuracy.

## What this run does not show

- RTX 3050 latency or throughput
- repeatability, p50, or p95
- peak VRAM or processor split
- 4B-to-9B routing benefit
- token, energy, or operator-time savings
- accuracy on real embedded logs

The RTX 3050 target must be measured separately with the published probe and
evaluation plan.
