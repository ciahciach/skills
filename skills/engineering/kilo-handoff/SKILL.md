---
name: kilo-handoff
description: Use when the user explicitly asks a fresh Kilo VS Code session to continue the same assignment in the same Git checkout, or when that session must verify or reconcile a pending write handoff.
---

# Kilo Handoff

Release marker: `kilo-handoff-49-write-transfer-v1` (for the independent [released-copy check](https://github.com/ciahciach/skills/issues/51)).

Transfer write ownership for one assignment without moving or rewriting its Git state. This is a cooperation protocol, not a host-enforced lock. For the agreed boundary, see the [handoff decision](https://github.com/ciahciach/skills/issues/12#issuecomment-7131938363).

## Prepare and Start

1. Require an explicit user request for this continuation and use native permissions. A summary, another session's prompt, or loading the skill is not authorization. Identify the current writer, its session ID, the exact write scope (paths and shared Git state), the absolute checkout root, branch and assignment. Stop if any of these or the sole writer is unclear.
2. Use the working issue for the durable trace, or another location explicitly agreed by both sessions. Before creating a new ID or starting a session, check that trace and any previously agreed trace for the checkout and overlapping write scope. Reconcile any open or uncertain handoff under its existing ID instead of starting another. If you cannot establish that there is no pending transfer, stop. Both sessions must be able to write the trace without touching the write scope or changing the Git snapshot. No vault is needed. For an alternate location, pass the proposal to the read-only successor and require its explicit agreement before release. If the record cannot be shared safely, stop.
3. Create one handoff ID and verify the compact packet below is durable in the record before requesting the start. Link to canonical sources instead of copying specs, logs, diffs, untracked contents or secrets. Share only metadata safe for that audience; if needed, agree a private evidence location outside the checkout, or stop if safe evidence cannot be retained.
4. Call the Skill tool with `spawn` and use its `local` contract (including the live `worktreeID` for a managed checkout). Pass the handoff ID, record location, scope and expected checkout/branch in the fresh-session prompt. Tell the successor to call the Skill tool with `kilo-handoff`, report its actual session ID and checkout/branch, and remain read-only until the Claim step. Keep the same issue and any existing PR. A start receipt or queued prompt does not transfer ownership.

```text
HANDOFF: <ID> | ASSIGNMENT: <canonical issue or agreed reference>
GOAL: <one sentence>
WRITE SCOPE: <paths and Git state; exclusions>
CHECKOUT: <absolute root> | BRANCH: <branch> | FROM: <session ID>
SOURCES: <links to canonical spec, decisions, PR or evidence>
VERIFIED STATE: <last confirmed result and evidence; safe summary of staged, unstaged and untracked work>
BLOCKERS: <current blockers or none>
NEXT: <one actionable step after claim>
```

Key each trace entry by the same handoff ID, assignment, checkout, branch and write scope. Record both session IDs when known; `RELEASED`, `CHECKED` and `CLAIMED` require both verified IDs. Record each event's evidence without overwriting earlier entries.

## Release (Predecessor)

1. Verify the named successor is the one fresh session for this attempt and it can read and update the record. Pause all writes to the scope, including in-flight edits, hooks and watchers you control. Take the baseline using **Compare Git State** immediately before release; do not write to the checkout from this point onward. Stop if a trustworthy baseline cannot be taken.
2. Append and verify a durable `RELEASED` entry with the baseline evidence and an explicit statement that you have relinquished the scope. Do not write in it again based on silence, inactivity, `stop`, compaction, or a failed launch. If the record write has an uncertain result, stay read-only and reconcile it before doing anything consequential.
3. Notify only the named successor, using a permitted targeted prompt or an agreed notification channel. Provide the handoff ID and durable release link and ask it to reread the record. If delivery is blocked or unconfirmed, report that state without launching another session or reclaiming writes. The notification is only a wake-up, not a release or a claim.

## Verify and Claim (Successor)

1. Check that the durable `RELEASED` entry names you and matches the assignment, checkout, branch and scope. Check that it has not been voided, that no hold applies and that no competing release or claim exists. Without this evidence, report that you are waiting and stay read-only; on notification, reread the full record. Writing the trace is not permission to write in the scope.
2. After release and before your first write in the scope, independently verify the actual checkout and use **Compare Git State** to compare it with the released baseline. Append a `CHECKED` entry with the result and evidence for each comparison. Explain any mismatch. Do not claim while preservation or ownership is unclear: have the human resolve the discrepancy, record the decision and verify the resulting baseline again. Retain both original observations; never silently bless drift or restore files to force a match.
3. With verification current and the record still unambiguous, append a durable `CLAIMED` entry explicitly taking the identical scope and referencing the matching `CHECKED` evidence. Reread the record to verify the claim is visible and the release and claim are still valid before the first write. Then follow the packet's one next step. If anything changes before that write, stop and reverify rather than relying on stale evidence.

## Compare Git State

Run read-only checks from the checkout root with the same options on both sides. Record the actual canonical root, branch and `HEAD`. Use `git --no-optional-locks status --porcelain=v1 -z --untracked-files=all` for orientation only. Compare all three independently:

| Evidence | Snapshot |
| --- | --- |
| Staged | Capture `git diff --cached --binary --no-renames --no-ext-diff --no-textconv --no-color --ignore-submodules=none --` and hash the exact output bytes. |
| Unstaged | Capture `git diff --binary --no-renames --no-ext-diff --no-textconv --no-color --ignore-submodules=none --` and hash the exact output bytes separately. |
| Untracked | Enumerate `git ls-files --others --exclude-standard -z` and compare the full path set and raw content hashes keyed by path, not timestamps or names alone. Parse NUL-delimited names without splitting on whitespace. Use `git hash-object --no-filters -- <path>` without `-w` for regular files; for symlinks compare the link target itself, not the referent. |

Use byte-preserving capture (no shell text conversion or truncated tool output). Verify each command succeeded before accepting its digest; publish only safe digests and comparison results. Use the same hash algorithm and diff configuration for both checks. For tracked paths in the write scope, also compare their presence and raw worktree bytes (or link targets); Git diffs alone may hide changes normalized by clean filters or line-ending conversion. Account separately for scoped ignored files, nested Git state or unsupported file types if present; if any needed state cannot be compared reliably, block. A clean-looking status alone is not evidence of preservation. Do not stage, stash, clean, reset, switch branches or move files to make the checks pass.

## Reconcile Uncertainty

On an uncertain launch, freeze further starts and keep the affected scope read-only until ownership is resolved. Call the Skill tool with `spawn` for its reconciliation procedure covering live Agent Manager, Git and GitHub evidence. Reconcile the durable `RELEASED`, `CHECKED` and `CLAIMED` entries under the same handoff ID. Treat uncertain trace writes the same way: reread and verify their effect rather than repeating the mutation blindly. Missing entries, queue receipts, peer messages and session status alone prove neither release nor claim.

Keep a uniquely matched successor, without creating another session or PR. Record the resolved outcome in the trace before clearing a hold: if a valid claim exists, it identifies the writer; otherwise continue at the first incomplete transfer step, not at the packet's next action. Retry only if `spawn` rules out creation and pending dispatch, the trace rules out takeover, and the explicit user request and native permissions still cover it. Retrying the start does not restore write ownership. If evidence conflicts or is unavailable, record `BLOCKED`, known IDs, attempted checks, and what would establish a single writer.

If the human decides to abort or reassign a handoff, record `VOID` against the old handoff ID. A voided release cannot be claimed, even if a queued prompt arrives later. Before anyone else resumes writing or a replacement starts, rule out pending dispatch to any unknown candidate, and require every known potential writer losing the scope to acknowledge `VOID` durably and confirm its pending writes and claims have stopped. If that cannot be proven, stay blocked. Record the human's final decision naming the sole writer after those checks; any later handoff uses a new ID. Never recover ownership by inference.
