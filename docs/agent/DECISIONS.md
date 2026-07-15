# Decision Ledger

Decision records are append-only. A change of direction creates a new decision
that supersedes an older one; history is not rewritten.

## D-0001 - Externalize handoff state

- Status: accepted
- Date: 2026-07-15
- Context: chat history is incomplete, tool-specific, and difficult to verify.
- Decision: use Git-tracked state, immutable artifact hashes, and explicit next
  actions as the handoff boundary.
- Alternatives considered:
  - transfer the complete chat transcript
  - maintain only a narrative status document
- Evidence: [research evidence register](../../research/evidence-register.md)
- Consequences:
  - resumption can be checked against repository and artifact state
  - state files require schema and drift validation
- Supersedes: none

## D-0002 - Keep model output advisory

- Status: accepted
- Date: 2026-07-15
- Context: structured output constrains shape but does not establish truth.
- Decision: deterministic signals and evidence validation outrank model output.
- Alternatives considered:
  - direct whole-log model analysis
  - native agent with file and shell tools
- Evidence: [log analysis architecture](../03-log-analysis-stack.md)
- Consequences:
  - the system remains useful without a model
  - model responses can be rejected without losing detector evidence
- Supersedes: none

## Record template

### D-NNNN - Title

- Status: proposed | accepted | rejected | superseded
- Date:
- Context:
- Decision:
- Alternatives considered:
- Evidence:
- Consequences:
- Supersedes:
