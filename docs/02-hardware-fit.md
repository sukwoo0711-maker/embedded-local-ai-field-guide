# RTX 3050 8GB 하드웨어 적합성

## 확인된 사실

- Ollama 공식 hardware 문서는 RTX 3050을 compute capability 8.6 목록에 포함합니다.
- 현재 문서는 Nvidia driver 550 이상을 요구합니다.
- Qwen3.5 registry의 artifact 크기는 다음과 같습니다.

| Model tag | Registry size | 8GB에서의 판단 |
|---|---:|---|
| `qwen3.5:4b-q4_K_M` | 3.4GB | 가장 여유 있는 triage 후보 |
| `qwen3.5:9b-q4_K_M` | 6.6GB | 작은 context, single load 조건에서 평가 |
| `qwen3.5:9b-q8_0` | 11GB | 완전 GPU 적재 후보에서 제외 |
| `qwen3.5:27b-q4_K_M` | 17GB | 완전 GPU 적재 후보에서 제외 |

위 크기는 model artifact 크기입니다. runtime buffer, KV cache, vision projector, driver overhead, 다른 프로세스의 VRAM을 포함하지 않습니다.

## Context의 모순처럼 보이는 권고

Ollama 공식 문서는:

- 24GiB 미만 VRAM에서 기본 context를 4K로 설정하고
- web search, agent, coding tool 같은 긴 작업에는 64K 이상을 제안합니다.

두 문장은 충돌하지 않습니다. 64K가 필요한 범용 agent를 8GB GPU에서 9B 모델로 온전히 수행하기 어렵다는 뜻입니다. 따라서 이 저장소는 범용 agent가 아니라 약 3K token 이하의 선별된 로그 evidence를 처리하는 bounded analyzer를 택합니다.

## 동일 VRAM proxy 관찰

원 조사 중 RTX 3070 Ti 8GB, compute capability 8.6, driver 591.86, Ollama 0.31.2, Qwen3.5 9B Q4에서 다음 model-allocation 표시가 기록됐습니다.

| Requested context | Ollama 표시 크기 | Processor 표시 |
|---:|---:|---:|
| 4K | 5.6GB | 100% GPU |
| 8K | 5.7GB | 100% GPU |
| 16K | 5.8GB | 100% GPU |
| 32K | 6.8GB | 86% GPU, 14% CPU |
| 64K | 7.5GB | 78% GPU, 22% CPU |

이 표는 다음을 의미하지 않습니다.

- RTX 3050의 처리 속도
- 3050에서 동일한 tokens/s 또는 latency
- 모든 prompt에서 동일한 메모리
- 8K 또는 16K가 품질상 최적
- 별도 GPU 앱이 실행 중일 때의 적합성

두 GPU가 8GB와 sm_86을 공유하므로 memory-fit 가설을 세우는 참고치는 되지만 성능 extrapolation은 할 수 없습니다. 이 관찰의 raw benchmark artifact는 저장소에 없으므로 [probe script](../scripts/probe_ollama.py)로 각 장비에서 다시 측정해야 합니다.

2026-07-15에는 같은 RTX 3070 Ti 8GB 호스트에서 Ollama 0.32.0과 `qwen3.5:9b`로 synthetic log direct-analysis를 한 번 더 실행했습니다. schema와 citation 검증은 통과했지만 inert prompt-injection 문자열을 실제 외부 agent 개입으로 과해석했습니다. timing과 한계는 [local smoke record](../research/local-smoke-2026-07-15.md)에 분리해 두었으며, 이 한 번의 결과를 RTX 3050 benchmark나 정확도 근거로 사용하지 않습니다.

## 권장 profile

| 항목 | 시작값 | 이유 |
|---|---:|---|
| Context | 8,192 | 로그 evidence와 schema/output 공간의 균형 |
| Prompt evidence budget | 약 3,000 tokens | system, schema, output을 위한 여유 |
| Parallel requests | 1 | context memory multiplication 방지 |
| Loaded models | 1 | 4B와 9B 동시 상주 방지 |
| KV cache | q8_0 | f16 대비 메모리 절감, 품질은 별도 확인 |
| Flash Attention | enabled | context 증가 시 메모리 완화 |
| Cloud | disabled | local-only 경계 명시 |
| 4B keep-alive | 0 after response | 9B 적재 전에 unload |
| 9B calls | 분석당 최대 1회 | latency와 VRAM thrash 제한 |

16K는 `ollama ps`로 full-GPU 상태를 확인한 뒤 선택적으로 평가합니다. 32K와 64K는 routine profile에서 제외합니다.

## RAM 64GB의 역할

64GB system RAM은 부분 offload와 큰 input buffer를 가능하게 하지만 GPU 적합성을 대신하지 않습니다. CPU offload로 실행된다는 사실은 latency가 허용 가능하다는 뜻이 아닙니다. system RAM은:

- 원본 artifact 보관과 hash 계산
- build, symbol, known-good 비교
- 일시적인 CPU offload 안전망

으로 보고, 거대한 model이나 context를 정당화하는 근거로 사용하지 않습니다.

## 장비별 acceptance 측정

각 RTX 3050 장비에서 최소 다음을 기록해야 합니다.

1. GPU model, VRAM, driver, compute capability
2. Ollama version과 model digest
3. context, prompt token count, output token count
4. `ollama ps`의 processor split
5. load, prompt-eval, generation duration
6. peak VRAM과 다른 GPU process
7. schema pass율과 evidence citation pass율
8. 사람이 label한 fixture 대비 false positive와 false negative

처리량과 정확도가 기록되기 전에는 “적용 가능”을 “실험 가능하고 memory-fit 가능성이 있음”으로 해석해야 합니다.
