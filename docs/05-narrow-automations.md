# 좁고 반복적인 Personal AI 자동화

## 조사에서 관찰된 신호

원 조사 표본에는 로컬 번역, Home Assistant, PII 비식별화, 로컬 문서 처리, 코드 review, trace debugging처럼 경계가 작은 도구가 반복해서 나타났습니다. Reddit의 practitioner thread도 요약, 분류, draft-only workflow, fail-closed human review에 집중됐습니다.

이를 “Personal AI가 이미 좁은 자동화에 정착했다”고 일반화할 수는 없습니다. 표본은 self-selected이고 성공률, 유지 비용, 절감 시간을 측정하지 않았습니다. 정확한 표현은 “이 조사 표본에서 좁은 workflow가 두드러졌다”입니다.

## 자동화 단계

| 단계 | 모델 역할 | 외부 효과 | 기본 정책 |
|---|---|---|---|
| 0 Observe | log와 metadata를 읽음 | 없음 | 자동 가능 |
| 1 Classify | severity, component, 유형 분류 | 없음 | schema 검증 후 자동 가능 |
| 2 Recommend | read-only next check 제안 | 없음 | allowlisted ID만 |
| 3 Draft | issue, handoff, release note 초안 | 아직 없음 | 사람 review 필수 |
| 4 Execute | send, flash, reset, publish | 있음 | 이 reference stack에서 제외 |

## RTX 3050 profile에 맞는 후보

| Workflow | 반복성 | Context 요구 | 위험 | 권장 |
|---|---:|---:|---:|---|
| nightly HIL 실패 요약 | 높음 | 낮음 | 낮음 | 우선 |
| UART anomaly 분류 | 높음 | 낮음 | 낮음 | 우선 |
| known-good diff 설명 | 중간 | 낮음 | 낮음 | 우선 |
| firmware/test handoff 초안 | 중간 | 낮음 | 낮음 | 우선 |
| issue/release-note 초안 | 중간 | 낮음 | 중간 | draft-only |
| email 초안 | 중간 | 낮음 | 중간 | draft-only |
| receipt/document 분류 | 높음 | 낮음 | 개인정보 검토 필요 | 별도 domain 평가 |
| 범용 일정·메일 비서 | 높음 | 높음 | 높음 | 제외 |
| 자동 flash/HIL actuator | 반복적 | 낮음 | 매우 높음 | 제외 |

## 좋은 첫 workflow의 조건

- 입력과 출력 schema가 작다.
- 성공/실패를 deterministic code로 확인할 수 있다.
- source evidence를 line 또는 hash로 가리킬 수 있다.
- 잘못된 결과를 사람이 쉽게 발견한다.
- 아무것도 하지 않는 fail-closed 결과가 허용된다.
- 실행하지 않고 draft로 끝낼 수 있다.
- 한 번의 local model 호출 또는 4B에서 종료되는 경우가 많다.

## 피해야 할 구조

- “알아서 처리해” 같은 open-ended goal
- email, issue, PR, hardware에 직접 side effect
- 전체 repository와 전체 log를 매번 context에 삽입
- 여러 model을 동시에 상주시킨 multi-agent swarm
- chat history를 유일한 memory로 사용
- model이 자유형 shell command를 생성하고 실행
- 성공 기준 없이 “완료”를 선언

## 측정 항목

자동화는 모델 demo가 아니라 운영 loop로 평가해야 합니다.

- 사람이 처리한 baseline 시간
- model 포함 end-to-end 시간
- detector-only, 4B-only, 4B-to-9B 비율
- schema rejection 비율
- evidence citation validity
- false positive와 false negative
- 사람이 수정한 필드 수
- 실행하지 않은 안전한 abort 수
- artifact당 input/output token
- 평균과 p95 latency

시간 또는 token 절감은 이 값을 수집한 뒤에만 주장합니다.
