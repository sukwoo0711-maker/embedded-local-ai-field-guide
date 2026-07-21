# Second-brain auto-grill decision log

검토일: 2026-07-22

## Repository placement

새 repository는 만들지 않는다. 이 저장소가 이미 로컬 분석, handoff, decision record,
security boundary, evaluation을 포함하고 있어 별도 second-brain repository는 문서와 정책을
중복시킨다. `agent-token-ledger`는 token/cost attribution이라는 독립 책임으로 유지한다.

## Survivors

| 후보 | 최강 반론 | 방어와 외부 검증 | 판정 |
|---|---|---|---|
| Wiki + event ledger + handoff | stale 또는 hallucinated summary를 장기 사실로 만들 수 있음 | verified event에 artifact hash/locator를 강제하고 ledger를 append-only로 검증 | 채택 |
| Compiler-native index | call graph 전체나 runtime timing을 제공하지 못함 | 목표를 variant/include/link provenance로 제한하고 runtime claim을 금지 | 채택 |
| Slow-local slot | 느린 대형 모델이 잘못된 결론을 더 오래 생성할 수 있음 | read-only, tools 없음, 3 jobs/night, proposed-only | 조건부 채택 |
| Gemini escalation | 외부 전송, quota, 조직이 예상하지 않은 headless 사용 | 기본 disabled, 조직 승인, 최소 packet, model-request hard cap, accounting 불가 시 중단 | 조건부 채택 |
| Graph-based code index | stale graph, build variant mismatch, supply-chain/agent-hook 위험 | source of truth가 아닌 재생성 가능한 cache로만 A/B 평가 | 보류된 선택지 |

## Rejected expansions

- 새 repository: 기존 field-guide와 중복
- Graphify dependency 또는 skill 자동 설치: 보안 승인과 A/B 근거 없음
- Gemini 호출 implementation: 조직 정책과 실제 request accounting contract가 repository 밖에 있음
- Colibri 전용 integration: 현재 특정 model/format에 종속되고 target PC 실측 없음
- 야간 자동 수정·commit·push·flash: read-only second-brain 목적을 벗어남

## External-verifier results

| 주장 | 검증 |
|---|---|
| event ledger 형식이 기계 검증 가능 | `validate-ledger`와 unit tests |
| forward reference와 근거 없는 verified event를 거부 | negative unit tests |
| 기존 log pipeline 회귀 없음 | 전체 offline test suite |
| compiler index의 variant 근거 | Clang/GCC 공식 문서 |
| Gemini hard cap 필요 | Google 공식 quota: prompt 1개가 여러 request 가능 |

## 남는 리스크

- 같은 모델이 제안·반박·판정을 수행한 상관성 한계
- target compiler/vendor가 GCC/Clang과 다른 경우의 portability
- 실제 회사 Gemini 계약과 공개 문서 간 차이
- target PC에서 slow-local의 latency, energy, SSD wear 미측정
- Wiki projection과 stale invalidation은 아직 reference implementation이 없음

따라서 이 변경은 production system이 아니라 검증 가능한 최소 substrate와 운영 계약이다.
