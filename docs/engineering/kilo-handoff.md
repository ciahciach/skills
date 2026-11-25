## What it does

`kilo-handoff` passes one assignment to a fresh Kilo VS Code Agent Manager [session](https://www.aihero.dev/ai-coding-dictionary/session) in the same Git checkout. It keeps staged and unstaged changes separate and verifies that untracked file contents survive. The new session may write only after the previous writer releases the scope and the successor checks the checkout and records its claim.

## When to reach for it

Type `/handoff` or `/kilo-handoff` in Kilo VS Code, or explicitly ask to continue the same assignment in a fresh session. No custom command in the user's Kilo profile is needed. A summary-only request does not start a session.

The new session receives a focused summary in its starting prompt: goal, user-specified focus, verified state, blockers, next action and suggested skills. Existing artifacts are linked and sensitive data is redacted. The issue or agreed record keeps the write-transfer trace; there is no portable Markdown file to locate or forward.

| Your situation | What to use |
| --- | --- |
| Same assignment, same checkout, new writer | `kilo-handoff` |
| A separate assignment that needs its own worktree | [spawn](https://aihero.dev/skills-spawn) |
| A portable briefing for a colleague, a different checkout or another tool | [`/handoff --portable`](../productivity/handoff.md) |

## Prerequisites

Use Kilo VS Code with Agent Manager and a Git checkout. For `/handoff`, install `handoff`, `kilo-handoff` and `spawn`; `/kilo-handoff` needs only the latter two. For a selective installation, run `npx skills@latest add ciahciach/skills --agent kilo --skill handoff kilo-handoff spawn` (add `--global` for a user-level install).

Give the agent explicit permission to continue the assignment in a fresh session. Both sessions need access to the working issue or another agreed place for the transfer record that does not change the files or Git state being handed over. Keep the record limited to the identifiers and evidence needed to reconcile the transfer. No vault is required.

## Common questions

**Do I have to commit or stash before handing off?**

No. The successor checks the staged diff, unstaged diff and untracked contents against the predecessor's baseline. The record keeps evidence of the comparison, not copies of the changes.

**What if the start times out?**

A timeout does not tell you whether the new session exists or has claimed the scope. The agent checks the live session, Git and PR state and the transfer record. While ownership is unclear, neither session writes in the scope and no second successor is started.

## It's working if

- The new session reports a different session ID but the same checkout and branch, and continues the same issue and existing PR, if any.
- One handoff ID links the predecessor's release, the comparison of all three kinds of local changes, and the successor's claim before it writes.
- The transfer record names one next action and links to the issue, decisions or evidence instead of duplicating them.

## Where it fits

This is a standalone handoff for work already in flight. [Spawn](https://aihero.dev/skills-spawn) handles starting the new session; `kilo-handoff` handles who can write. Use [ask-matt](https://aihero.dev/skills-ask-matt) to find the right route if you only need to carry context forward.
