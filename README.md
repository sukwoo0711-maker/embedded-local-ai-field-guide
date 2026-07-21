# Embedded Local AI Field Guide

RTX 3050 8GB와 RAM 64GB 환경에서 검토한 로컬 임베디드 로그 분석, Git 기반 AI 인수인계, 좁고 반복적인 개인 자동화의 근거 중심 가이드입니다.

> Research snapshot: 2026-06-14 to 2026-07-14
> Primary-source verification: 2026-07-15
> Target profile: GeForce RTX 3050 8GB, 64GB system RAM, Windows
> Status: reference design and proof of concept, not a production benchmark

English abstract: this repository separates verified facts, observations, inferences, and recommendations for a bounded local-AI workflow. The included implementation treats model output as advisory, cites only supplied log lines, exposes no tools, and has no execution path for hardware-changing actions.

## 결론

세 방향 모두 적용 가능하지만 범위를 작게 고정해야 합니다.

| 주제 | 보수적 판단 | 이 저장소의 선택 |
|---|---|---|
| 로컬 임베디드 로그 분석 | 가능 | 결정론적 전처리와 규칙 탐지가 기준이며 Qwen3.5 4B/9B는 자문 계층 |
| Qwen3.5 4B Q4 | 8GB에서 가장 여유 있는 후보 | 1차 분류 |
| Qwen3.5 9B Q4 | 작은 컨텍스트와 단일 적재 조건에서 평가 가능 | 필요한 경우에만 2차 분석 |
| 9B Q8, 27B Q4 이상 | 모델 파일만 8GB를 초과 | 기본 범위에서 제외 |
| Ollama 네이티브 agent | v0.32.0 정식 릴리스에 포함됐지만 호스트 도구 권한이 큼 | 핵심 경로에서 제외하고 `/api/chat`만 사용 |
| 여러 AI의 인수인계 | Git과 검증 가능한 상태 파일 패턴이 반복 관찰됨 | 채팅은 비권위 자료, Git 상태와 artifact hash가 기준 |
| Personal AI | 표본에서 좁고 반복적인 업무가 두드러짐 | 요약·분류·초안까지만 자동화, 외부 효과는 사람 승인 |
| 토큰 절감 | 전체 로그 대신 이상 구간만 넣으면 입력량은 줄어듦 | 구조적 절감만 주장, 절감률은 측정 전까지 주장하지 않음 |

핵심 구조는 다음과 같습니다.

```text
immutable UART/HIL log
  -> deterministic normalization and detectors
  -> bounded evidence windows
  -> Qwen3.5 4B triage
  -> deterministic escalation gate
  -> Qwen3.5 9B analysis
  -> schema and line-citation validation
  -> stdout or explicitly requested artifact
```

모델이 없어도 탐지 결과는 남습니다. 모델이 낸 심각도보다 `HardFault`, assertion, watchdog reset 같은 결정론적 신호가 우선합니다.

## 중요한 정정

초기 조사 원자료는 네이티브 agent를 `v0.32.0-rc0` 프리릴리스로 정리했습니다. 재검증 결과, [Ollama v0.32.0](https://github.com/ollama/ollama/releases/tag/v0.32.0)은 2026-07-11 공개된 정식 릴리스이며 interactive agent experience를 포함합니다.

정식 릴리스 여부와 운영 안전성은 다른 문제입니다. agent는 파일·셸·웹 같은 호스트 도구를 사용할 수 있으므로, 이 저장소는 `--yolo`나 자동 도구 승인 대신 도구가 전혀 없는 로컬 API 호출을 기본으로 합니다.

## 빠른 시작

필수 조건:

- Nvidia driver 550 이상
- Ollama 0.32.0 또는 호환되는 structured-output API 버전
- Python 3.11 이상
- `qwen3.5:4b`와 `qwen3.5:9b`를 순차 적재할 수 있는 디스크 여유

환경과 모델 준비 명령을 먼저 확인합니다. 모델 다운로드는 기본적으로 실행되지 않습니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Doctor.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Prepare-Models.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Prepare-Models.ps1 -Apply
```

`Doctor.ps1`는 API가 닿아도 두 custom model이 없으면 exit code 4를 반환합니다. `Prepare-Models.ps1`는 `-Apply`가 없으면 명령만 보여주며 다운로드나 model 생성을 하지 않습니다.

패키지를 설치하고 synthetic 로그를 결정론적으로 검사합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m embedded_log_analyzer deterministic ./samples/uart-watchdog.synthetic.log
```

Ollama를 포함한 2단계 분석은 다음과 같습니다. 기본 출력은 stdout이며 입력 파일을 수정하지 않습니다.

```powershell
python -m embedded_log_analyzer analyze `
  ./samples/uart-watchdog.synthetic.log `
  --stage auto
```

파일 저장은 명시해야 하며, 기존 파일 덮어쓰기는 거부합니다.

```powershell
python -m embedded_log_analyzer analyze `
  ./samples/uart-watchdog.synthetic.log `
  --stage auto `
  --output ./artifacts/example-report.json
```

## 8GB 기준 운영값

권장 시작값은 `8K context`, `parallel=1`, `loaded models=1`입니다. 공식 문서는 24GiB 미만 VRAM의 기본 context를 4K로 두며 agent·coding 같은 일반 작업에는 64K 이상을 제안합니다. 이 둘은 8GB 환경에서 일반 목적 agent보다 작은 로그 분석기를 택해야 하는 이유입니다.

`config/ollama.env.ps1.example`:

```powershell
$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_CONTEXT_LENGTH = "8192"
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_FLASH_ATTENTION = "1"
$env:OLLAMA_KV_CACHE_TYPE = "q8_0"
$env:OLLAMA_NO_CLOUD = "1"
```

이 값은 범용 최적값이 아닙니다. 다른 GPU 앱이 VRAM을 사용하면 9B가 부분 CPU offload로 전환될 수 있으므로 `ollama ps`로 실제 적재 상태를 확인해야 합니다.

동일 VRAM의 더 빠른 RTX 3070 Ti에서 수행한 단 한 번의 9B smoke test도 load를 포함해 약 97.8초가 걸렸습니다. 따라서 RTX 3050에서 9B를 interactive 기본 경로로 간주하지 않으며, background 분석 SLA가 맞지 않으면 4B/detector-only로 제한하거나 9B 단계를 생략해야 합니다.

## 안전 경계

이 PoC는 다음을 하지 않습니다.

- tool calling, shell, web, file-edit 도구 제공
- firmware flash, erase, reset, power-cycle, fuse, key 조작
- cloud fallback 또는 원격 Ollama endpoint 자동 허용
- 원본 로그 수정
- 모델 출력을 명령으로 실행
- 승인이나 채팅 기억을 다음 AI 세션에 승계
- 실제 장비 로그를 저장소에 자동 커밋

로그의 문자열은 모두 신뢰하지 않는 데이터입니다. 로그 안의 “지시”와 모델 출력은 실행되지 않습니다. 결과에는 입력으로 전달한 line number만 인용할 수 있고, 검증에 실패한 모델 응답은 폐기됩니다. redaction은 quoted/JSON key-value와 private-key block을 포함한 best-effort 방어이며 완전한 DLP가 아니므로 실제 로그 공개 전에는 사람이 다시 검토해야 합니다.

자세한 위협 모델은 [docs/06-security.md](docs/06-security.md)를 참고하세요.

## Git 기반 인수인계

채팅 기록은 참고 자료일 뿐 source of truth가 아닙니다. 재개 순서는 다음과 같습니다.

1. `AGENTS.md`
2. `docs/agent/STATE.yaml`
3. 활성 task의 `HANDOFF.yaml`
4. `docs/agent/known-good.yaml`
5. 결정 기록과 hash가 검증된 artifact
6. resume gate 결과

resume gate는 `MATCH`, `MINOR_DRIFT`, `MATERIAL_DRIFT`, `CANNOT_RESUME` 네 상태만 사용합니다. branch, source commit, dirty digest, board/probe/fixture, toolchain, firmware hash, UART/HIL 증거 중 기능적 차이가 있으면 기존 계획을 자동 재개하지 않습니다.

## 좁은 자동화 후보

이 하드웨어에서 우선 검토할 만한 작업:

- nightly HIL 실패 요약
- UART anomaly 분류와 근거 line 정리
- firmware/test handoff 초안
- release note와 issue 초안
- read-only known-good 비교

사람 승인 없이 수행하지 않을 작업:

- 자동 flash/erase/reset/power
- fuse, key, protection state 변경
- issue/PR/email 자동 전송
- 장비 상태를 바꾸는 HIL actuator 실행

[docs/05-narrow-automations.md](docs/05-narrow-automations.md)에 자동화 단계별 경계를 정리했습니다.

## 근거를 읽는 법

이 저장소는 문장을 다음 네 종류로 구분합니다.

- `FACT`: 공식 문서, 릴리스, registry에서 직접 확인
- `OBSERVATION`: 특정 환경에서 관찰했지만 일반화할 수 없음
- `INFERENCE`: 여러 근거로부터 도출한 해석
- `RECOMMENDATION`: 이 target profile을 위한 설계 선택

원 조사에는 107개 항목이 있었지만 대부분을 독립적인 기술 근거로 세지 않았습니다. X가 빠졌고, 일부 fallback 항목은 조사 기간 밖이거나 entity-miss였으며, 소셜 조회수와 star는 관심도이지 정확도·안전성·비용 절감의 증거가 아니기 때문입니다.

- [조사 방법과 한계](docs/01-evidence-and-method.md)
- [하드웨어 적합성](docs/02-hardware-fit.md)
- [reference architecture](docs/03-log-analysis-stack.md)
- [Git 상태 인수인계](docs/04-git-state-handoff.md)
- [평가 계획](docs/07-evaluation.md)
- [RTX 3050 적용 결정표](docs/08-deployment-decision.md)
- [Wiki, event ledger, handoff](docs/09-project-memory-ledger.md)
- [Compiler-native index](docs/10-compiler-native-index.md)
- [제한된 야간 second-brain pipeline](docs/11-nightly-second-brain.md)
- [Second-brain auto-grill 결정 로그](docs/12-auto-grill-decision-log.md)
- [선별 근거 register](research/evidence-register.md)
- [단일-host 9B smoke test와 qualitative failure](research/local-smoke-2026-07-15.md)

## 저장소 구성

```text
config/       conservative Ollama environment
models/       4B triage and 9B analysis Modelfiles
prompts/      bounded system prompts
schemas/      model-output contracts
src/          zero-runtime-dependency Python PoC
scripts/      Windows-first doctor and setup wrappers
samples/      synthetic, non-device log fixtures
tests/        offline tests with no GPU or Ollama requirement
docs/         research, architecture, safety, and handoff guidance
research/     curated evidence register, not the raw social dump
```

## Project-memory ledger

공개 가능한 합성 event ledger와 zero-dependency validator가 포함되어 있습니다. 과거 행은
수정하지 않으며 verified event에는 artifact hash와 locator가 필요합니다.

```powershell
python -m embedded_log_analyzer validate-ledger `
  .\samples\project-memory.synthetic.jsonl
```

이 ledger는 `agent-token-ledger`의 token/cost trace와 다릅니다. 여기서는 관찰, 이슈, 시도,
결과, 결정의 project memory를 기록합니다.

## 검증

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
```

실제 모델 평가는 정답 문장 일치가 아니라 다음 invariant를 확인해야 합니다.

- JSON schema 준수
- 전달된 line만 인용
- quote가 실제 sanitized line의 substring
- critical detector를 `no_anomaly`로 덮어쓰지 않음
- 실행 가능한 command field가 없고, verdict·missing evidence·check rationale·limitation의 URL·경로·명백한 action 문구가 후검증됨
- 어떤 모델 출력도 실행되지 않음
- 4B/9B 요청이 순차 실행되고 각 요청에 `keep_alive: 0`이 적용됨

자유형 자연어 blacklist는 모든 명령 제안을 완전하게 판별할 수 없습니다. 실제 동시 적재 여부와 model digest는 각각 `ollama ps`와 model registry/API로 manual acceptance에서 확인합니다.

## 라이선스와 면책

코드와 문서는 MIT License로 제공합니다. 외부 프로젝트와 문서는 링크만 인용하며 각 원 저작물의 라이선스가 적용됩니다. 이 저장소는 특정 AI 공급자나 모델을 추천·보증하지 않으며, 모델 정확도·처리량·토큰 절감률·비용 절감률을 입증하지 않습니다.
