# 로컬 임베디드 로그 분석 reference architecture

## 설계 목표

이 스택은 “로그를 읽는 agent”가 아니라 “교체 가능한 Ollama backend를 가진 검증형 분류기”입니다.

우선순위는 다음과 같습니다.

1. 원본 증거 보존
2. 결정론적 탐지
3. 입력 축소
4. 구조화된 모델 자문
5. evidence 검증
6. 사람 판단

## 단계별 흐름

### 1. Immutable input

- binary를 한 번 읽고 SHA-256을 계산합니다.
- 읽기 전후 size와 mtime이 달라지면 중단합니다.
- 입력 파일을 수정하지 않습니다.
- basename과 hash만 보고서에 넣고 absolute path는 제외합니다.
- 실제 DUT 로그는 Git 밖에 두고 manifest에 hash와 time slice만 기록합니다.
- 기본 입력 상한은 50MiB와 250,000 physical lines이며 어느 하나를 넘으면 중단합니다.

### 2. Deterministic normalization

- CRLF/LF/CR만 physical line boundary로 사용하고 ANSI escape를 정규화합니다.
- NUL과 표시 불가능한 control character를 제거합니다.
- VT, FF, NEL, Unicode line/paragraph separator는 새 line으로 증폭하지 않고 공백으로 바꿉니다.
- 원본 line number를 유지합니다.
- bearer token, quoted/JSON key-value secret, private-key block 같은 명백한 secret을 best-effort로 마스킹합니다.
- 로그 문자열은 지시가 아니라 신뢰하지 않는 데이터로 취급합니다.

### 3. Deterministic detection

기본 detector:

- assertion, panic, fatal
- HardFault, BusFault, UsageFault, MemManage
- stack overflow
- watchdog expiry/reset/timeout
- brownout와 reset cause
- out of memory
- timeout와 explicit failure

`watchdog initialized`처럼 정상 설정 문구는 watchdog 장애로 분류하지 않습니다. detector 결과는 모델 결과보다 우선합니다.

반복 오류 storm이 report와 memory를 증폭하지 않도록 rule별 전체 match count는 유지하되, 상세 `Signal`은 각 rule의 처음 16개와 마지막 16개만 보존합니다. report의 `signals_truncated`가 이 sampling 여부를 표시합니다.

### 4. Evidence windows

탐지 지점 앞 80행, 뒤 40행을 기본으로 선택합니다. 겹치는 구간은 합치고 중요도 순 최대 3개, 총 300행과 약 3,000 estimated tokens로 제한합니다. 선택된 window의 signal anchor를 문맥 행보다 먼저 예약하며, 단일 장문 행은 marker를 붙여 token guardrail 안으로 자릅니다.

탐지가 없으면 마지막 session tail을 제한적으로 triage에 전달합니다. 전체 로그를 통째로 prompt에 넣지 않습니다.

```text
8,192 context
  - system and safety contract
  - JSON schema
  - selected log text, target <= 3,000 estimated tokens
  - model output allowance
```

tokenizer dependency를 피한 보수적 추정:

```python
estimated_tokens = max(len(text) // 4, len(text.encode("utf-8")) // 3)
```

이는 billing 또는 정확한 tokenizer count가 아닙니다. input cap을 위한 guardrail입니다.
보고서의 `estimated_selection_reduction`도 같은 근사치로 전체 sanitized log와 선택된 line text만 비교하며, system prompt·schema·model output과 2단계 호출 비용은 포함하지 않습니다.

### 5. 4B triage

`qwen3.5:4b`는 작은 schema만 반환합니다.

- classification
- severity
- components
- evidence line numbers
- deep analysis 필요 여부
- missing evidence
- confidence

4B가 schema를 위반하면 9B로 자동 우회하지 않고 `model_output_rejected`로 종료하며 detector 결과는 보존합니다. 작은 model의 실패를 큰 model 호출로 숨기지 않기 위해서입니다.

### 6. Deterministic escalation gate

다음 중 하나면 9B를 한 번 호출합니다.

- critical deterministic pattern
- high 또는 critical triage
- possible anomaly 또는 insufficient evidence
- 4B가 deep analysis를 요청
- confidence가 0.65 미만

`no_anomaly`이고 detector가 비critical이며 confidence가 충분한 경우 4B에서 종료할 수 있습니다.

### 7. 9B analysis

9B는 다음을 분리합니다.

- observed facts
- hypotheses와 supporting/contradicting line
- missing evidence
- 허용된 read-only check ID
- confidence와 human-review 필요 여부

자유형 shell command 대신 enum check ID만 반환합니다.

### 8. Validation

JSON schema만 통과하면 충분하지 않습니다.

- 모든 line number가 전달한 bundle에 존재
- quote가 해당 sanitized line의 실제 substring
- observed fact에 최소 한 개 evidence line
- non-none severity에 evidence 존재
- critical detector가 모델에 의해 삭제되지 않음
- 실행 가능한 command field가 없음
- verdict, missing evidence, check rationale, limitation의 URL, absolute path, 명백한 hardware/write action을 후검증
- 어떤 모델 출력도 실행 경로에 연결하지 않음

실패한 모델 출력은 `model_output_rejected`로 남기고 detector 결과만 보존합니다.

자유형 자연어 필터는 완전한 정책 판별기가 아닙니다. 정확한 log quote에는 command-like 문자열이 들어갈 수 있고, 반대로 새로운 표현은 blacklist를 피할 수 있습니다. 권위 있는 후속 행동은 enum `check_id`뿐이며, narrative는 항상 비권위 자문입니다.

## 결과 상태

| 상태 | 의미 |
|---|---|
| `complete` | triage와 필요한 deep analysis가 검증됨 |
| `analysis_only` | 명시적인 direct-analysis 요청의 9B 결과가 검증됨 |
| `triage_only` | 4B 결과로 종료 |
| `deterministic_only` | model 없이 detector 결과만 생성 |
| `model_unavailable` | API/model 접근 실패 |
| `model_output_rejected` | schema 또는 evidence 검증 실패 |

capture가 읽는 도중 변경되면 JSON report를 만들지 않고 CLI가 stderr에 `input_changed_during_read`를 기록한 뒤 exit code 4로 종료합니다.

## Structured output contract

[triage schema](../schemas/triage.schema.json)와 [analysis schema](../schemas/analysis.schema.json)를 Ollama `format` 필드에 전달합니다. 같은 schema를 prompt에도 포함해 model을 grounding합니다.

요청은:

- `stream: false`
- `keep_alive: 0`
- `num_ctx: 8192`
- low temperature와 fixed seed
- no `tools` field

를 사용합니다. seed와 temperature는 완전한 determinism을 보장하지 않습니다.

## 토큰 절감의 정확한 의미

이 구조는 원본 전체 대신 선별된 window를 보내므로 input token 상한을 낮춥니다. 그러나 이 저장소는 절감률을 제시하지 않습니다.

향후 측정식:

```text
input_reduction = 1 - selected_input_tokens / whole_log_tokens
total_compute_delta = two_stage_total_duration - direct_9b_total_duration
```

입력 token이 줄어도 4B와 9B를 모두 호출하면 총 latency 또는 energy가 늘 수 있습니다. 따라서 token, wall time, energy, accuracy를 함께 측정해야 합니다.

## 왜 vector DB가 없는가

초기 문제는 대규모 지식 검색이 아니라 한 capture의 이상 구간 분석입니다. vector DB와 RAG는:

- 운영 복잡성
- 추가 memory와 index lifecycle
- 오래된 context가 현재 로그와 섞일 위험

을 더합니다. known-good 비교는 우선 hash가 검증된 작은 artifact와 명시적 metadata로 구현하고, 실제 recall 요구가 측정된 뒤 검색 계층을 추가합니다.
