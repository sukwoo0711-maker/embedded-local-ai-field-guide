# Curated evidence register

Snapshot window: 2026-06-14 to 2026-07-14
Primary-source recheck: 2026-07-15
Second-brain supplement recheck: 2026-07-22

이 register는 원 조사에서 실제 설계 판단에 사용한 출처만 선별합니다. 원본 소셜 dump 전체는 포함하지 않습니다. 기간 내 신호와 기간 밖 기술 baseline의 구분, 관찰일, 알려진 게시일은 [source provenance](source-provenance.csv)에 기록했습니다. 수집 범위와 비공개 raw의 hash는 [research manifest](research-manifest.json)에 있습니다.

등급:

- A: 공식 문서, release, registry
- B: 병합된 PR 또는 실행 가능한 구현
- C: issue, Show HN, practitioner self-report
- D: 관심도와 홍보 신호

## Ollama, Qwen3.5, 8GB hardware

| ID | Source | Grade | 뒷받침하는 내용 | 한계 |
|---|---|---:|---|---|
| OLL-REL-032 | [Ollama v0.32.0 release](https://github.com/ollama/ollama/releases/tag/v0.32.0) | A | 2026-07-11 non-prerelease, interactive agent experience | agent 안전성이나 성능 보증 아님 |
| OLL-PR-17017 | [cmd: agent UI PR #17017](https://github.com/ollama/ollama/pull/17017) | B | agent UI 구현과 2026-07-10 merge | 출시 초기 구현 한 건 |
| OLL-GPU | [Ollama hardware support](https://docs.ollama.com/gpu) | A | RTX 3050은 sm_86, driver 550 이상 | 처리량과 VRAM fit 수치는 없음 |
| OLL-CTX | [Ollama context length](https://docs.ollama.com/context-length) | A | 24GiB 미만 기본 4K, 긴 agent/coding에는 64K 권고 | 8GB에서 64K가 효율적이라는 뜻 아님 |
| OLL-FAQ | [Ollama FAQ](https://docs.ollama.com/faq) | A | concurrency memory scaling, loaded-model limit, Flash Attention, q8_0 KV cache, no-cloud | model/task별 품질은 별도 실험 필요 |
| OLL-STRUCT | [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) | A | `format`에 JSON Schema 제공 가능 | schema 준수가 사실 정확도를 보장하지 않음 |
| OLL-TOOLS | [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling) | A | single, parallel, multi-turn agent loop 지원 | 이 repository는 tools를 사용하지 않음 |
| QWEN-TAGS | [Qwen3.5 model tags](https://ollama.com/library/qwen3.5/tags) | A | 4B Q4 3.4GB, 9B Q4 6.6GB, 9B Q8 11GB, 27B Q4 17GB | registry size는 runtime VRAM이 아님 |
| OLL-CHAIN | [small/large model chain and VRAM unload self-report](https://www.reddit.com/r/ollama/comments/1uqxbe0/i_made_a_tool_that_chains_a_small_local_model/) | C | 순차 model routing이 실제 관심사임 | 자가보고, 통제 benchmark 아님 |

## Git과 상태 파일 인수인계

| ID | Source | Grade | 뒷받침하는 내용 | 한계 |
|---|---|---:|---|---|
| OAI-HARNESS | [Harness engineering](https://openai.com/index/harness-engineering/) | A | 짧은 AGENTS.md, versioned docs/plans, repository knowledge as system of record, worktree isolation | 2026-02-11 자료로 30일 trend 근거가 아닌 architecture baseline |
| CODEX-29356 | [Codex issue #29356](https://github.com/openai/codex/issues/29356) | C | compaction 뒤 operational continuity 손실 보고 | issue 한 건으로 발생률을 알 수 없음 |
| CODEX-28866 | [Codex issue #28866](https://github.com/openai/codex/issues/28866) | C | 큰 local JSONL resume의 memory failure 보고 | 특정 환경의 bug report |
| GROUNDTRUTH | [Groundtruth snapshot](https://github.com/akahkhanna/groundtruth/tree/67238fa5717774791979b32245fe38a0456558e6) | C | agent claim을 Git diff와 대조하는 구현 | broad adoption 근거 아님 |
| GIT-TEMP | [git-temp snapshot](https://github.com/sebmellen/git-temp/tree/fb0b47c48cb00bab117eeff83998c6afbcdcdd2b) | C | agent scratchpad를 Git status에서 분리 | 직접 handoff 표준은 아님 |
| CODEALMANAC | [CodeAlmanac snapshot](https://github.com/AlmanacCode/codealmanac/tree/4dc6949cfaec98130facea45bc2e7d39dba138d5) | C | local, self-updating repository knowledge | freshness/accuracy를 별도 검증해야 함 |
| ENOLA | [Enola snapshot](https://github.com/enola-labs/enola/tree/0182470079be1e5993b3e87d84fe3c81df6fd9fa) | C | deterministic architecture graph 접근 | project existence가 효과를 증명하지 않음 |
| PROMPTLINGS | [Promptlings snapshot](https://github.com/dfinson/promptlings/tree/22fcbea0f4ed3fba4722fcbc99e6aa8d8510b05a) | C | portable agent guidance 사례 | state validation 표준은 아님 |
| SESSION-RECOVER | [cc-session-recover snapshot](https://github.com/softcane/cc-session-recover/tree/9244d9a8f7763514ea92cdb7a8c32f1a37269c33) | C | session 중단과 recovery가 실제 문제임 | Claude-specific self-hosted tool |
| TASK-WEDDING | [TaskMasterWedding snapshot](https://github.com/TrevorHumble/TaskMasterWedding/tree/c90384dc1ad743661ce30383acbd9573e93e3ec0) | C | shared task state의 실제 구현 사례 | 범용성 검증 없음 |
| HANDOFFKIT | [HandoffKit snapshot](https://github.com/dyngai/handoffkit/tree/cff7bcae9de5787bfaf8d322d2b7b2473bbabed9) | C | coding-agent handoff 규칙 구현 | 프로젝트별 설계 |
| MULTI-AGENT-THREAD | [multiple agents on one project](https://www.reddit.com/r/AI_Agents/comments/1uv8u5g/working_on_the_same_project_with_different_ai/) | C | shared-workspace 충돌에 대한 사용자 관심 | 제목·댓글 기반 qualitative signal |

## Embedded metadata와 검증

| ID | Source | Grade | 뒷받침하는 내용 | 한계 |
|---|---|---:|---|---|
| ZEPHYR-TWISTER | [Zephyr Twister](https://docs.zephyrproject.org/latest/develop/test/twister.html) | A | hardware map, device test metadata를 외부화할 기존 체계 | 이 repository의 handoff schema 자체를 표준화하지 않음 |
| R3 | [R3 snapshot](https://github.com/hyperlogue/r3/tree/97b7530593762f3466b40b566aeada8dd8e481bb) | C | 작은 local model 기반 bounded review 사례 | embedded-log 정확도 근거 아님 |
| HALO | [Halo snapshot](https://github.com/context-labs/halo/tree/17aadca5feb681c59b4da1e9fea5455f58c31b6e) | C | local trace debugging이라는 좁은 workflow | UART/HIL과 동일한 domain은 아님 |

## 좁은 local/personal automation

| ID | Source | Grade | 관찰된 use case | 한계 |
|---|---|---:|---|---|
| LOQI | [Loqi snapshot](https://github.com/danterolle/loqi/tree/5631152ed22dab39f7de9f1aed93dc88fbc616e9) | C | local-first translation | 채택률과 품질 미측정 |
| SELORA | [Selora snapshot](https://github.com/SeloraHomes/ha-selora-ai/tree/69fa589b8fc7670567c33cee4c7c358570a65ec0) | C | local Home Assistant model | home domain, embedded debug와 다름 |
| PII-GUI | [PII GUI snapshot](https://github.com/sophia486/pii-gui/tree/5b0804829c19cb0e1088a8c739582e25f07f1ac1) | C | local data de-identification | 보안 보증 아님 |
| USEFUL-AGENTS | [useful agent practitioner thread](https://www.reddit.com/r/AI_Agents/comments/1uosa8b/whats_the_most_useful_ai_agent_youve_actually/) | C | 구체 workflow discussion | self-selected answers |
| PERSONAL-AGENTS | [personal-life agent thread](https://www.reddit.com/r/AI_Agents/comments/1uuv9dm/how_have_you_been_using_and_deploying_ai_agents/) | C | 개인 반복 업무 사례 | 비용/정확도 미측정 |
| DISCOMFORT | [actions users hesitate to delegate](https://www.reddit.com/r/AI_Agents/comments/1uv46ud/for_people_running_ai_automations_what_actions/) | C | side-effect action에 대한 불편 | 작은 표본 |

## Agent security context

| ID | Source | Grade | 뒷받침하는 내용 | 한계 |
|---|---|---:|---|---|
| GITLOST | [GitLost case study](https://noma.security/blog/gitlost-how-we-tricked-githubs-ai-agent-into-leaking-private-repos/) | C | agent가 untrusted content와 repository 권한을 함께 가질 때의 위험 | Ollama 사건이 아니며 일반 threat 사례로만 사용 |

## 2026-07-22 second-brain supplement

| ID | Source | Grade | 뒷받침하는 내용 | 한계 |
|---|---|---:|---|---|
| PROJECTMEM | [PROJECTMEM paper](https://arxiv.org/abs/2606.12329) | C | append-only typed event log와 deterministic projection 구현 | 10 projects/207 events의 저자 self-study; 일반 효익 미입증 |
| TAKTILE-WIKI | [Taktile LLM Wiki](https://engineering.taktile.com/blog/llm-wiki-agent-memory/) | C | persistent wiki, source validation, stale/contradiction lint 사례 | 단일 조직 engineering report |
| CLANG-CDB | [Clang compilation database](https://clang.llvm.org/docs/JSONCompilationDatabase.html) | A | translation unit별 실제 compile arguments와 multi-configuration 표현 | runtime control/data flow는 제공하지 않음 |
| GCC-DEPS | [GCC dependency generation](https://gcc.gnu.org/onlinedocs/gcc/Preprocessor-Options.html) | A | `-MD`/`-MMD`/`-MF` dependency artifact semantics | vendor compiler마다 option이 다름 |
| GCC-MAP | [GCC linker options](https://gcc.gnu.org/onlinedocs/gcc/Link-Options.html) | A | GNU linker map 전달 방식 | map 형식과 의미는 linker별 상이 |
| GEMINI-QUOTA | [Gemini quota documentation](https://docs.cloud.google.com/gemini/docs/quotas) | A | Enterprise 2,000 requests/day, prompt 하나가 여러 model request 가능 | 조직별 계약/변경 가능; 비용표 아님 |
| GEMINI-PRIVACY | [Gemini Code Assist security and privacy](https://docs.cloud.google.com/gemini/docs/codeassist/security-privacy-compliance) | A | Customer Data, stateless processing, optional logging, telemetry와 security controls | 실제 조직 설정은 별도 감사 필요 |
| COLIBRI | [Colibri repository](https://github.com/JustVugg/colibri) | B | disk-streamed MoE expert engine의 공개 구현 | 초기 구현, 특정 model/format, target PC 실측 없음 |

## 낮은 가중치 또는 배제한 근거

- 조회수 높은 TikTok/Instagram의 “full local agent stack” 홍보: 관심도 D, 기술 검증 아님
- `vLLM -> Langflow -> Mem0` 같은 대형 stack: 8GB target과 초기 use case에 과도함
- model이 다른 frontier model과 동급이라는 SNS benchmark 주장: 독립 검증 없음
- 2025년 YouTube tutorial: architecture 배경은 될 수 있지만 30일 trend 근거에서 제외
- repository star와 open issue 수: 생태계 규모 신호일 뿐 품질과 안정성 점수 아님
- 자동 transcript의 손상된 직접 인용: 의미 왜곡 위험 때문에 보고서 결론에서 제외

## 검증 가능한 정량 자료가 아직 없는 주장

다음은 evidence가 추가되기 전까지 주장하지 않습니다.

- RTX 3050 tokens/s 또는 p95 latency
- Qwen3.5 4B/9B embedded-log 정확도
- token 또는 비용 절감률
- 4B-to-9B routing의 energy 절감
- Git handoff의 조직 생산성 향상률
- Personal AI 자동화의 시장 정착 또는 실패율
