# RTX 3050 8GB 적용 결정표

이 문서는 “실행 가능한가”와 “업무에 쓸 가치가 있는가”를 분리합니다.

| 구성 | 현재 판단 | 허용 범위 | 중단 조건 |
|---|---|---|---|
| deterministic detector | 바로 적용 가능 | CI와 로컬 read-only 분석 | signal false-positive가 운영 부담을 늘림 |
| Qwen3.5 4B Q4 triage | pilot 권장 | 4K/8K, 동시 요청 1, synthetic/비식별 로그 | OOM, citation 실패, 사람 검토 시간이 baseline 초과 |
| Qwen3.5 9B Q4 direct | 조건부 | background 또는 nightly 분석 | latency SLA 초과, CPU offload, 반복 schema rejection |
| 4B→gated 9B | 측정 후 판단 | 4B가 실제 9B 호출 수를 줄일 때만 | 두 model의 합산 시간/energy가 direct 9B보다 나쁨 |
| Ollama native agent | 실제 DUT 경로에서는 제외 | disposable VM과 synthetic repo 평가만 | shell/file/web 권한 또는 broad approval 필요 |
| Git + state-file handoff | 바로 적용 가능 | hash·resume gate·approval 비승계 | stale state 또는 artifact hash mismatch |
| 좁은 Personal AI 자동화 | pilot 권장 | 분류·요약·초안·read-only 비교 | 자동 send/publish/flash/reset이 필요 |

## 왜 9B는 기본 interactive 경로가 아닌가

8GB에 model이 적재될 가능성과 응답 시간이 실용적인지는 다른 질문입니다.
대상 장비가 아닌 RTX 3070 Ti 8GB의 단 한 번의 smoke test에서도 9B direct
analysis는 load를 포함해 97.776초가 걸렸습니다. 이 관찰로 RTX 3050의
시간을 계산할 수는 없지만, 3050에서 interactive SLA를 가정할 근거도
없습니다.

따라서 기본 운영은:

1. detector-only 결과를 즉시 반환
2. 4B는 짧은 triage에만 사용
3. 9B는 명시적 escalation과 background queue에서만 평가
4. SLA가 맞지 않으면 9B 단계를 제거

입니다. RAM 64GB는 부분 CPU offload의 안전망일 뿐 GPU generation latency를
해결하지 않습니다.

## 토큰 절감의 올바른 판정

“전체 로그 대신 window를 사용한다”는 구조는 입력량을 줄일 수 있지만,
항상 절감되는 것은 아닙니다. 공개 synthetic watchdog fixture는 14행이어서
detector가 전체를 선택했고, 이 사례의 line-selection 절감은 0%입니다.

실제 절감 판단에는 최소 다음을 함께 기록해야 합니다.

```text
whole_log_estimated_tokens
selected_log_estimated_tokens
schema_and_system_prompt_tokens
triage_prompt_tokens + triage_output_tokens
analysis_prompt_tokens + analysis_output_tokens
4B_total_duration + 9B_total_duration
```

선택된 로그 token만 줄고 schema와 2단계 호출이 추가되면 총 token, latency,
energy는 오히려 늘 수 있습니다. 이 저장소가 절감률을 주장하지 않는
이유입니다.

## 3단계 도입

### 0단계 — 모델 없음

- synthetic fixture로 detector rule 검증
- known-good와 failure label 정의
- 원본 hash와 handoff state 도입
- 사람의 기존 분석 시간 기록

### 1단계 — 4B pilot

- 비식별 로그에만 적용
- schema pass, citation pass, critical recall 기록
- 모델 출력은 issue/report 초안으로만 사용
- 4B가 사람 검토 시간을 실제로 줄이는지 비교

### 2단계 — 9B conditional

- 4B escalation rate와 direct-9B baseline 비교
- 3050에서 load/prompt/eval duration과 `ollama ps` 기록
- background SLA 안에서만 유지
- 실제 효익이 없으면 detector+4B로 축소

이 결정표는 모델 우월성이나 시장 채택을 주장하지 않습니다. target hardware,
fixture, label, operator SLA가 달라지면 결론도 다시 측정해야 합니다.
