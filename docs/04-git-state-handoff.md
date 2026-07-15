# Git과 상태 파일 기반 AI 인수인계

## 주장 범위

최근 구현과 issue에서 Git, worktree, 상태 문서, resume validation 패턴이 반복 관찰됐습니다. 이것은 사실상의 산업 표준이라는 뜻이 아닙니다. 이 저장소는 그 실패 양상을 줄이기 위한 reference contract를 제안합니다.

## 채팅 대신 외부화할 상태

채팅 transcript는:

- tool과 vendor에 종속되고
- compaction 또는 resume에서 손실될 수 있으며
- 현재 Git/DUT 상태와 일치하는지 검증하기 어렵습니다.

인수인계에는 다음만 남깁니다.

- branch와 source commit
- staged, unstaged, untracked를 포함한 worktree digest
- board revision, MCU, probe, fixture
- toolchain digest
- firmware SHA-256과 DUT에서 관찰한 build ID
- UART/HIL artifact hash와 time slice
- 실행한 verification wrapper와 결과
- observed facts와 hypotheses
- rejected approaches
- 정확히 한 개의 next action
- fresh approval가 필요한 action

## Source-of-truth 순서

1. hash가 검증되는 immutable artifact
2. Git commit과 worktree state
3. 승인된 known-good record
4. machine-readable task state
5. decision ledger
6. narrative와 chat

## `source_commit` 자기참조 문제

handoff file을 포함한 commit은 자신의 SHA를 미리 알 수 없습니다. 따라서 `source_commit`은 인수인계 대상 source가 확정된 직전 commit을 가리킵니다.

그 이후 commit이 handoff metadata만 바꿨다면 허용할 수 있지만, diff path가 `AGENTS.md`와 `docs/agent/**` 같은 allowlist에만 있는지 검사해야 합니다. 기능 코드가 섞이면 `MATERIAL_DRIFT`입니다.

## Resume gate

| 결과 | 조건 | 허용 행동 |
|---|---|---|
| `MATCH` | commit/worktree, target, toolchain, firmware, artifact가 일치 | read-only 계획 재개 |
| `MINOR_DRIFT` | 문서 시간, agent version 같은 비기능 차이만 존재 | 차이를 기록하고 read-only만 진행 |
| `MATERIAL_DRIFT` | commit, toolchain, board/probe/fixture, firmware, test 설정 차이 | 기존 계획 중단, 재기준화 |
| `CANNOT_RESUME` | schema invalid, artifact/hash 실패, DUT identity 불명, 지시 충돌 | 작업 중지와 사람 판단 |

검사 순서:

1. YAML/schema와 필수 필드
2. source commit 존재와 branch 관계
3. metadata-only descendant path
4. worktree digest
5. known-good approval
6. board, probe firmware, fixture
7. toolchain digest
8. firmware file hash와 DUT build ID
9. UART/HIL artifact hash
10. 기존 approval의 비승계
11. 결과와 diff 기록

## Embedded-specific 상태

안정적으로 commit할 값:

- board family와 revision
- MCU
- opaque DUT/probe alias
- probe firmware version
- fixture ID/revision
- UART baud와 logical interface
- build configuration
- toolchain image 또는 manifest digest
- firmware hash
- test suite와 report hash

로컬에만 둘 값:

- COM port
- 사용자 absolute path
- USB serial number
- credential과 key
- 고객/제품 confidential identifier

machine mapping은 ignored `docs/agent/local/` 아래에 둡니다.

## Artifact 계보

원본 UART bytes를 먼저 hash합니다. ANSI 제거, timestamp normalization, secret redaction은 별도 파생 artifact입니다.

```text
uart_raw sha256:A
  -> normalize v1 -> uart_normalized sha256:B
  -> redact v1    -> uart_public_excerpt sha256:C
  -> analyze      -> report sha256:D
```

각 파생본은 `derived_from`과 transform version을 기록합니다. 원본을 정규화본으로 덮어쓰지 않습니다.

## Approval는 상태가 아니다

approval는 다른 AI나 세션으로 승계하지 않습니다. handoff는 모든 미실행 approval을 `pending`으로 되돌립니다.

새 approval에는 최소 다음이 있어야 합니다.

- action
- physical target
- firmware hash
- parameters
- expiry

flash, erase, reset, power, fuse, key, protection state 변경은 broad approval로 묶지 않습니다.

## 제공 템플릿

- [runtime state](agent/STATE.yaml)
- [known-good registry](agent/known-good.yaml)
- [decision ledger](agent/DECISIONS.md)
- [task handoff](agent/tasks/_template/HANDOFF.yaml)
- [artifact manifest](agent/tasks/_template/ARTIFACTS.yaml)
- [resume-gate checklist](agent/resume-gate.md)

템플릿은 표준이 아니라 출발점입니다. 실제 CI에는 YAML parser와 JSON Schema validator를 추가하고, repository-specific wrapper ID를 정의해야 합니다.
