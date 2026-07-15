# 평가 계획

## 평가 질문

1. RTX 3050 8GB에서 4B와 9B Q4가 정한 context 안에서 안정적으로 동작하는가?
2. deterministic selection이 whole-log input보다 token을 얼마나 줄이는가?
3. 4B triage가 9B 호출을 줄이면서 critical event를 놓치지 않는가?
4. model이 실제 evidence line만 인용하는가?
5. 사람이 분석 결과를 신뢰하고 수정하는 비용이 baseline보다 낮은가?

## Offline CI

GPU와 Ollama 없이 확인:

- ANSI, CRLF, NUL, invalid UTF-8 처리
- source line number 보존
- secret redaction
- HardFault/assert/watchdog/reset positive case
- `watchdog initialized` false-positive 방지
- window merge와 token budget
- 반복 signal storm의 bounded representative와 line-count limit
- 동일 입력의 deterministic bundle 동일성
- escalation truth table
- schema와 evidence validation
- prompt-injection 문장이 tool 또는 command로 변하지 않음
- remote URL 기본 거부
- request payload에 `tools` 없음
- timeout, malformed JSON, HTTP failure 시 fail-closed
- 기본 실행의 no-write 동작

## Synthetic fixture set

최소 fixture:

- clean boot
- watchdog reset
- HardFault with register dump
- assert with source symbol
- brownout loop
- timestamp regression
- repeated line storm
- prompt-injection text inside log
- secret-like token

실제 장비 로그는 공개 fixture로 사용하지 않습니다. 사람이 재현한 최소 synthetic excerpt를 별도로 만듭니다.

## Model contract test

실제 model의 문장 전체를 golden comparison하지 않습니다. 다음 invariant만 검사합니다.

- valid JSON schema
- supplied line만 citation
- quote substring 일치
- enum 준수
- critical detector 보존
- 실행 가능한 command field와 tool call 부재
- verdict, missing evidence, check rationale, limitation의 URL, absolute path, 명백한 write/hardware action 거부
- model text가 실행되지 않음
- confidence 범위
- missing evidence의 명시

## RTX 3050 manual run

1. `Doctor.ps1`로 driver, GPU, Ollama, model 확인
2. 다른 GPU workload를 종료하고 baseline VRAM 기록
3. 8K context에서 synthetic watchdog fixture 실행
4. `ollama ps`로 한 model만 적재됐는지 확인
5. 4B 종료와 4B-to-9B escalation을 각각 측정
6. API timing counter와 peak VRAM 기록
7. input SHA-256이 실행 전후 같은지 확인
8. 사람이 label한 결과와 비교
9. 16K는 별도 실험으로만 수행
10. 32K/64K는 routine acceptance 범위에서 제외

## 비교군

| Variant | 목적 |
|---|---|
| detector only | model 없이 얻는 baseline |
| direct 4B | 가장 작은 local model |
| direct 9B | 2-stage overhead 비교 |
| 4B -> gated 9B | 제안 architecture |
| whole-log 9B | token reduction 비교, 작은 fixture에서만 |

## 지표

- selected lines / total lines
- estimated input token reduction
- model prompt/eval token
- model load/prompt/generation duration
- peak VRAM과 processor split
- 9B escalation rate
- schema pass rate
- evidence citation pass rate
- critical-event recall
- false positive per capture
- human correction count
- end-to-end operator time

## Publish gate

다음 조건 전에는 정량적 우월성이나 절감률을 README에 추가하지 않습니다.

- fixture label과 evaluation script 공개
- 반복 횟수와 환경 공개
- mean뿐 아니라 p50/p95 공개
- 실패와 rejected output 포함
- detector-only와 direct-9B 비교
- RTX 3050 실장비에서 재현

성공한 한 번의 demo는 benchmark가 아닙니다.
