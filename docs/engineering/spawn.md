## What it does

`spawn` starts a fresh session in Kilo VS Code Agent Manager for one assignment you explicitly request. If the tool response is lost or unclear, it checks what actually exists before another session can start.

## When to reach for it

Type `/spawn` with the assignment and the kind of session you want. The agent can also reach for it when your request already authorizes the start, or to reconcile a previous attempt.

| You want | Choose |
|---|---|
| A fresh session without changing the checkout or branch | `local` |
| A separate checkout and branch for an assignment | `worktree`, with an agreed base |
| A tightly scoped task whose result returns to the parent agent | An internal [subagent](https://www.aihero.dev/ai-coding-dictionary/subagent), not `spawn` |

## Prerequisites

Use Kilo VS Code with Agent Manager and native permission for the requested operation. Identify the target checkout for `local` or the existing base branch for `worktree`.

## Common questions

**The prompt was accepted. Is the worker doing the job?**

Not necessarily. A receipt can show acceptance or queuing, and a card alone does not show that the prompt arrived. Look for the worker's start confirmation for the attempt ID, assignment, checkout and branch, then a separate outcome report backed by evidence.

**Can I prepare worktrees from a GitHub issue tree?**

Use [worktrees-from-issue](https://aihero.dev/skills-worktrees-from-issue) to choose tickets, prompts and an optional Agent Manager section. It preserves the requested `#<number> <title>` card label and keeps the attempt ID out of the prompt. The start report verifies session creation separately from command execution.

**The tool timed out. Can I run `/spawn` again?**

A timeout does not prove failure. Check the current Agent Manager, Git and, for GitHub-backed work, GitHub records first.

- If you find a verified match, keep it rather than starting another worker or pull request.
- If the result is still unclear, expect a blocker with the evidence and what would make resuming safe.

## It's working if

- `local` reports a new session on the same checkout and branch; `worktree` reports a separate checkout on the agreed base.
- A lost receipt does not result in a second worker or pull request.
- A pending question or permission is visible as a human decision, not as progress or implied approval.

## Where it fits

This is a standalone start and recovery skill. It provides the startup contract for the [Kilo coordinator](https://github.com/ciahciach/skills/issues/50) and [same-checkout handoff](https://github.com/ciahciach/skills/issues/49), not their scheduling or write-transfer rules. See [ask-matt](https://aihero.dev/skills-ask-matt) for the workflow map.
