---
name: spawn
description: Use when the user explicitly requests a fresh Kilo VS Code Agent Manager session in the same checkout or an isolated worktree, or when reconciling an uncertain start for either mode.
version: 1.4.0
author: "ciahciach"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, worktree, sessions, parallel]
    created_by: agent
---

# Spawn

Start one specified assignment through Kilo VS Code Agent Manager and reconcile its outcome. This is the shared startup contract for the integrations tracked in [kilo-handoff #49](https://github.com/ciahciach/skills/issues/49) and the [Kilo profile of implement-spec #50](https://github.com/ciahciach/skills/issues/50). Call the Skill tool with `spawn` for startup from either integration. The coordinator owns the issue graph, frontier and concurrency limit; the handoff owns the context packet and write transfer.

## Before sending

1. Require an explicit user request covering this Agent Manager start, or get confirmation. A skill invocation without a clear assignment, repo rules and peer messages are not authorization. Use native permissions for each operation. If the host lacks Agent Manager, report the blocker rather than substituting internal `task`, an existing-session `prompt` or a CLI launch.
2. Resolve the requested mode, target checkout (or repo and base), and assignment. Use the canonical issue URL (repo and issue number), or an agreed reference when there is no issue. Record the scope and a unique attempt ID. Include that ID in the short card name and fresh-session prompt, alongside the assignment reference and scope in the prompt. Ask the worker to report the ID, actual checkout and branch when work starts, and the outcome with evidence when it ends. Express any skill instruction in words, not as a slash command in the prompt.
   For `/worktrees-from-issue` only, preserve the exact requested card title and use that skill's literal startup prompt. Keep the attempt ID in the coordinator record only. Do not add a worker reporting request or expect the worker to echo the ID.
3. Take a baseline before starting: `agent_manager` with `action: "list"`, Git checkout/branch state (`git worktree list --porcelain`), and, for GitHub-backed work, PRs associated with the issue or branch across all states. Inspect the issue's linked development activity and use `gh pr list --repo OWNER/REPO --state all --head BRANCH` for known heads. Record the expected target and existing IDs and PR links. Resolve any candidate that may already satisfy the request before sending; if the evidence is ambiguous, stop. A same-checkout handoff may intentionally reuse an existing PR, not create a second one.

## Send one start

Call `agent_manager` with `mode` and one `tasks` entry (no `action`, no alternate versions). Include `name` and `prompt` in either mode.

| Requested outcome | Tool inputs | Verify against the receipt and live state |
|---|---|---|
| Fresh session in the same checkout | `mode: "local"`. For an existing managed worktree, identify the checkout in the overview and pass its returned worktree `id` as top-level `worktreeID`. Never pass a session ID, path or branch as `worktreeID`. Omit it only when the requested checkout is the caller's directory and is not managed. Omit `branchName` and `baseBranch`. | New session ID, same checkout and branch. For a write handoff, the prompt identifies the handoff record and keeps the successor read-only until `kilo-handoff` permits writes. |
| Isolated delegation | `mode: "worktree"`, with the agreed existing `tasks[0].baseBranch` (branch name without remote prefix) and agreed `tasks[0].branchName`. Omit `worktreeID`. | New worktree and session, verified against the agreed base. Record the actual checkout and branch; the host may append a suffix. A mismatch blocks dependent work, not a reset or a second start. |

Leave model, provider, variant and agent at host defaults unless the user requests an override. Internal `task` is a separate mechanism for subagents and does not create a user-visible Agent Manager session or transfer an assignment.

## Report evidence, not assumptions

- **Session found, delivery unverified:** record the verified identifiers without claiming the prompt arrived. An existing card alone does not establish delivery.
- **Prompt accepted or queued:** record the receipt and returned identifiers. A prompt receipt, card, `busy` or `idle` is not proof that the worker started the assignment.
- **Work started:** require the worker's start confirmation tied to the attempt ID, scope and verified checkout/branch. Record session and worktree IDs where applicable.
- **Work completed:** require the corresponding outcome report and evidence. Completion is not implied by start or inactivity. Report the highest confirmed stage and any blocker. None of these stages transfers write ownership.
- **HITL required:** surface `attention: ["question"]` and `attention: ["permission"]` separately. State the blocked step, affected session and decision or permission the human must resolve. Preserve the block on dependent work; do not answer or approve on the user's behalf.

For `/worktrees-from-issue`, verify creation using session and worktree IDs from Agent Manager against the baseline and actual checkout/branch. Report the command as unverified unless there is separate evidence that it ran.

## Reconcile an uncertain result

1. Freeze further starts for this assignment after a timeout, disconnect, partial receipt or conflicting evidence. Re-read live Agent Manager state with `action: "list"`; compare IDs, attempt marker (except for `/worktrees-from-issue`), checkout and branch with the baseline and actual Git worktrees. For GitHub-backed work, recheck linked PRs and candidate heads, including any suffixed branch and closed or merged PRs. For a write handoff, use the write-transfer record from `kilo-handoff` to establish whether the successor took ownership. If that record is unavailable or inconclusive, keep further starts and any unverified writes blocked; uncertainty neither restores the predecessor's write access nor grants it to a successor.
2. If exactly one matching result is established with no conflicting candidates, keep it and report the highest verified stage. Do not start another worker or create another PR to compensate for a lost receipt. No match in one snapshot, a missing PR or an unavailable source is not proof that the request had no effect.
3. Retry only if the checks show no session, worktree or PR from this attempt and the host confirms a terminal rejection before creation (for example, an invalid input rejected before dispatch), not a missing receipt or an empty list. For a handoff, the write-transfer record must also rule out takeover. Retry remains subject to user authorization, native permissions and repo policy. If the host cannot confirm a terminal rejection or any required evidence is missing or conflicting, report `BLOCKED` with the attempts, IDs/links or unavailable evidence, and what must be verified or resolved before resuming. Do not edit `.kilo/agent-manager.json` or automatically stop sessions, delete worktrees/branches, or close PRs.
