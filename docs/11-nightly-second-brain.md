# Bounded nightly second-brain pipeline

목표는 밤새 자유롭게 코드를 고치는 agent가 아니다. 원본을 변경하지 않고 evidence를
정규화하고, project memory 초안을 만들고, 어려운 항목만 제한적으로 상위 worker에 보내는
batch pipeline이다.

```text
immutable code/log/build artifacts
  -> deterministic collect, hash, build/test and index
  -> event-ledger proposals
  -> fast local triage
  -> at most N slow-local jobs
  -> at most M approved Gemini escalations
  -> morning brief and handoff draft
  -> human review
```

## Worker policy

| 계층 | 기본 역할 | 외부 전송 | 자동 side effect |
|---|---|---|---|
| deterministic | hash, diff, build/test, bounded selection | 없음 | read-only/build workspace만 |
| fast local | 분류, Wiki/ledger 초안 | 없음 | 없음 |
| slow local | 모순 탐지, 대안 반박, 장기 분석 | 없음 | 없음 |
| Gemini escalation | 승인된 최소 evidence packet의 2차 검토 | 있음 | 없음 |
| morning Codex | 사람이 승인한 구현 작업 | 제품 정책에 따름 | 별도 승인 경계 |

Slow-local은 제품명이 아니라 교체 가능한 interface다. Colibri는 대형 MoE expert를
디스크에서 streaming하는 실험적인 선택지이며, 모델/format과 storage bandwidth에 강하게
종속된다. 따라서 기본 backend나 SLA 경로가 아니라 `max_jobs`가 작은 실험 slot으로만 둔다.
[Colibri repository](https://github.com/JustVugg/colibri)

```yaml
slow_local:
  enabled: false
  max_jobs_per_night: 3
  deadline_local: "05:00"
  filesystem: read_only
  tools: disabled
  output_status: proposed
```

## Gemini escalation gate

Gemini Code Assist Enterprise의 Gemini CLI/agent-mode quota는 현재 사용자당 하루 최대 2,000
model requests이며, 한 prompt가 여러 model request를 만들 수 있다. 그러므로 prompt 수를
비용/쿼터 단위로 간주하지 않는다.
[Google quota documentation](https://docs.cloud.google.com/gemini/docs/quotas)

Standard/Enterprise는 prompt, response, 주변 file snippet을 Customer Data로 처리한다.
공식 문서는 stateless service가 prompt/response를 저장하지 않는다고 설명하지만, 선택적
Cloud Logging, telemetry, 조직별 access/network control은 별도 점검 대상이다.
[Google security and privacy documentation](https://docs.cloud.google.com/gemini/docs/codeassist/security-privacy-compliance)

```yaml
gemini_escalation:
  enabled: false
  authorization: organization-approved-oauth-only
  concurrency: 1
  max_jobs_per_night: 10
  max_model_requests_per_night: 30
  retry_per_job: 1
  send_full_repository: false
  send_raw_device_logs: false
  web_and_external_mcp: false
  stop_on:
    - authentication_mode_changed
    - quota_warning
    - request_accounting_unavailable
    - sensitive_pattern_detected
```

실제 model request 수를 관측하지 못하면 Gemini 단계는 fail-closed로 비활성화한다. ccusage의
추정 달러와 실제 청구액을 동일시하지 않고, 조직의 Cloud billing/audit source로 확인한다.

## Morning acceptance

야간 결과는 다음 조건을 만족할 때만 morning brief에 포함한다.

- 입력 artifact hash가 실행 전후 동일
- citation/locator validation 통과
- 모델 output이 command나 tool invocation으로 연결되지 않음
- `verified` 승격은 deterministic evidence 또는 사람 review가 수행
- 실패한 attempt는 다음 run의 반복 방지 입력으로 포함

자동 code edit, commit, push, issue 전송, flash/reset은 이 pipeline의 범위 밖이다.
