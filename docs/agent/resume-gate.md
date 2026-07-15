# Resume gate checklist

## Classifications

| Result | Meaning |
|---|---|
| `MATCH` | repository, target, toolchain, firmware, and evidence match |
| `MINOR_DRIFT` | documented non-functional metadata drift only |
| `MATERIAL_DRIFT` | source, target, toolchain, firmware, or test setup changed |
| `CANNOT_RESUME` | invalid state, missing evidence, hash failure, unknown target, or conflicting instruction |

## Validation order

- [ ] YAML parses and the schema version is supported.
- [ ] Active state contains no `null`, placeholder hash, or example value.
- [ ] `source_commit` is a real 40-character Git SHA.
- [ ] Descendant commits, if any, change only metadata allowlist paths.
- [ ] Worktree digest includes staged, unstaged, and untracked files.
- [ ] Known-good ID exists and has approved status.
- [ ] Toolchain is identified by immutable digest or manifest.
- [ ] Board, MCU, probe firmware, and fixture match the physical target.
- [ ] Firmware file hash matches the state record.
- [ ] The DUT build ID or equivalent identity was read when supported.
- [ ] UART/HIL artifacts exist and their size and SHA-256 match.
- [ ] Each fact has an artifact and line, byte, test, or time locator.
- [ ] Facts and hypotheses are separate.
- [ ] HIL result includes wrapper, exit status, pass/fail count, and report hash.
- [ ] No absolute local path, user name, token, key, customer name, or serial is committed.
- [ ] There is exactly one next action with preconditions and expected evidence.
- [ ] No arbitrary shell string is stored as an automatic action.
- [ ] Approval carry-over is false.
- [ ] Hardware-changing actions require new exact approval.
- [ ] Completion includes required target evidence, not only a successful build.

## Exit policy

- `MATCH`: resume read-only work. Get fresh approval for side effects.
- `MINOR_DRIFT`: record the difference, then continue read-only work.
- `MATERIAL_DRIFT`: do not execute the old next action. Re-baseline.
- `CANNOT_RESUME`: stop and request human resolution.
