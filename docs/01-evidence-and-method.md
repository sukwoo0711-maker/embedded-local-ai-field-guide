# 조사 방법과 근거 경계

## 조사 질문

다음 세 가지가 GeForce RTX 3050 8GB와 RAM 64GB 환경에서 실용적인지 검토했습니다.

1. Ollama와 로컬 모델을 이용한 임베디드 로그 분석
2. 여러 AI 사이의 작업 상태를 Git과 상태 파일로 인수인계
3. 범용 비서가 아닌 작고 반복적인 Personal AI 자동화

조사 기간은 2026-06-14부터 2026-07-14까지이며, 2026-07-15에 핵심 1차 출처를 다시 확인했습니다.

## 수집 범위

last30days v3.11.1 원 조사에는 7개 source의 107개 항목이 포함됐습니다. 이 수치는 비공개 raw의 collector output이며 독립적인 107개 기술 근거를 뜻하지 않습니다. 파일 hash, 크기, source별 개수는 [research manifest](../research/research-manifest.json)에 기록했습니다.

| Source | 항목 | 원 조사에 기록된 engagement |
|---|---:|---:|
| Reddit | 20 | 2,607 points, 1,021 comments |
| YouTube | 10 | 2,618,810 views, 59,886 likes |
| TikTok | 15 | 349,829 views, 15,541 likes |
| Instagram | 7 | 20,753,204 views, 2,290 likes |
| Hacker News | 26 | 1,602 points, 590 comments |
| GitHub | 1 | Ollama repository snapshot |
| Digg clusters | 28 | 157 posts, 110 authors |

X는 수집되지 않았고 arXiv와 Techmeme 결과는 0개였습니다.

## 근거 등급

| 등급 | 의미 | 이 보고서에서의 용도 |
|---|---|---|
| A | 공식 문서, release, model registry | 기술 사실과 버전 확인 |
| B | 병합된 PR, 실행 가능한 구현 | 기능이 실제 구현됐다는 근거 |
| C | issue, 사용자 자가보고, Show HN | 실패 가능성 또는 사용 패턴 신호 |
| D | 조회수, star, 짧은 SNS 홍보 | 관심도 신호만 제공 |

설계 권고는 별도 표기합니다. A 등급 사실이 있어도 해당 설계가 최적이라는 뜻은 아닙니다.

## 합성 원칙

- 공식 문서와 release가 소셜 게시물보다 우선합니다.
- 소셜 engagement는 품질, 정확도, 안전성, 비용 절감의 증거로 사용하지 않습니다.
- “프로젝트가 존재한다”와 “보편적으로 채택됐다”를 구분합니다.
- 모델 파일 크기와 실행 중 전체 VRAM 사용량을 구분합니다.
- 8GB GPU에서 실행 가능하다는 것과 충분히 빠르다는 것을 구분합니다.
- 관찰된 구현 패턴을 산업 표준이나 시장 정착으로 표현하지 않습니다.
- 사실, 관찰, 추론, 권고를 가능한 한 분리합니다.

## 원 조사에서 수정한 내용

원 조사 요약은 `v0.32.0-rc0`를 네이티브 agent가 처음 들어간 프리릴리스라고 기록했습니다. 1차 출처 재검증 결과:

- `v0.32.0`은 2026-07-11 공개된 non-prerelease GitHub release입니다.
- release note는 interactive agent experience를 명시합니다.
- `ollama agent` 구현 PR #17017은 2026-07-10 merge됐습니다.

따라서 이 저장소는 “agent가 RC라서 제외”하지 않습니다. 대신 출시 초기 기능이며 호스트 도구 권한이 넓다는 별개의 이유로 핵심 로그 분석 경로에서 제외합니다.

## 알려진 한계

1. 일부 fallback 결과는 2025년 또는 2026년 2월 자료로 조사 기간 밖입니다.
2. 상당수 ranked item은 score 0 또는 entity-miss fallback이었습니다.
3. 일부 Reddit 항목은 제목만 보존돼 구체 주장에 사용할 수 없습니다.
4. 자동 생성 transcript에는 전사 오류와 문자 인코딩 손상이 있습니다.
5. 보충 검색 요약 일부는 원 raw에 개별 URL이 남지 않았습니다.
6. RTX 3050 자체의 tokens/s, latency, energy, 실제 VRAM 통제 benchmark는 없습니다.
7. Qwen3.5의 embedded-log 정확도와 비교 model 대비 품질은 측정하지 않았습니다.
8. 토큰 또는 비용 절감률을 계산할 대조군 자료가 없습니다.
9. Git handoff 사례는 반복 관찰됐지만 표준화나 시장 채택률을 뜻하지 않습니다.
10. Personal AI 사례는 자가보고 중심이므로 성공률과 절감 효과를 추정할 수 없습니다.

## 원 raw를 공개하지 않은 이유

원 raw에는 조사 범위를 벗어난 항목, 긴 자동 transcript, 손상된 문자, 홍보성 문구, 신뢰하지 않는 외부 텍스트가 섞여 있습니다. 저작권·개인정보·prompt-injection 표면을 줄이기 위해 저장소에는 링크, 짧은 요약, 근거 등급만 선별해 넣었습니다.

이 결정은 결과를 숨기기 위한 것이 아닙니다. [source provenance](../research/source-provenance.csv)와 [evidence register](../research/evidence-register.md)에 채택한 URL, 기간 관계, 용도, 한계를 공개하고, 정량 주장은 재현 가능한 측정이 생길 때만 추가합니다.

## 가장 강하게 말할 수 있는 결론

8GB GPU에서 작은 quantized model과 제한된 context를 사용한 구조화 로그 분석은 실험 가능한 구성입니다. 복수 AI의 연속성을 채팅보다 Git 상태와 검증 가능한 artifact에 두는 구현도 반복해서 관찰됩니다. 다만 이는 성능, 정확도, 시장 채택 또는 비용 절감을 입증한 결과가 아니라 보수적인 reference architecture입니다.
