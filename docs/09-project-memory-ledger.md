# Wiki, event ledger, handoff

이 세 파일은 서로 대체하지 않는다.

| 계층 | 질문 | 갱신 규칙 |
|---|---|---|
| Wiki | 지금 재사용할 수 있는 지식은 무엇인가 | 근거가 바뀌면 재검증 또는 stale 처리 |
| Event ledger | 무엇을 관찰하고 시도했으며 결과가 어땠는가 | append-only; 과거 행 수정 금지 |
| Handoff | 다음 작업자가 지금 무엇을 해야 하는가 | task 경계마다 교체, hash와 resume gate 적용 |

이 설계는 PROJECTMEM의 `issue / attempt / fix / decision / note` typed event log와
결정론적 projection 아이디어를 참고하지만 구현을 복제하지 않는다. PROJECTMEM의 공개 평가는
10개 프로젝트, 207개 이벤트의 저자 self-study이므로 일반적인 생산성 향상 근거로 사용하지
않는다. [PROJECTMEM paper](https://arxiv.org/abs/2606.12329)

LLM Wiki의 장점은 이미 조사한 내용을 다시 원문 전체에서 합성하지 않는 데 있다. 그러나
source 재검증을 생략하면 stale claim이 재사용될 수 있다. Taktile의 공개 사례도 wiki-only
응답과 source-validation 응답을 별도로 비교하고 contradiction/staleness lint를 둔다.
[Taktile LLM Wiki](https://engineering.taktile.com/blog/llm-wiki-agent-memory/)

## 이 저장소의 최소 ledger

한 줄에 한 JSON object를 기록한다. `samples/project-memory.synthetic.jsonl`은 공개 가능한
합성 예제다.

```powershell
python -m embedded_log_analyzer validate-ledger `
  .\samples\project-memory.synthetic.jsonl
```

검증기는 다음 invariant만 결정론적으로 확인한다.

- event ID 중복 금지
- reference는 앞서 기록된 event만 가리킴
- attempt와 result는 이전 사건을 참조
- verified 사건은 artifact hash와 locator를 포함
- source commit은 null 또는 40자리 lowercase Git hash
- 모델 생성 여부와 sensitivity를 명시

JSON Schema는 개별 event의 모양을 정의한다. JSONL 전체의 순서, 중복, backward reference는
`validate-ledger`가 검사한다.

## 신뢰 규칙

`verified`는 모델 confidence가 높다는 뜻이 아니다. hash로 식별된 artifact의 locator가
주장을 지지하고, 필요한 경우 build/test/measurement가 통과했다는 뜻이다. 모델이 만든
event는 기본 `proposed`이며 모델 자신이 `verified`로 승격할 수 없다.

수정이 필요하면 이전 행을 고치지 않는다.

1. 새 `result` 또는 `decision` event를 추가한다.
2. 이전 event ID를 `references`에 넣는다.
3. Wiki의 active claim을 새 event로 다시 projection한다.
4. 기존 claim은 `stale` 또는 `superseded`로 표시한다.

민감한 원본 로그와 사내 source path는 public ledger에 넣지 않는다. public repository에는
synthetic artifact와 공개 가능한 hash/locator만 둔다.
