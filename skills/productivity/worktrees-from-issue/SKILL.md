---
name: worktrees-from-issue
description: "Prepare Kilo VS Code Agent Manager worktrees from a GitHub Wayfinder map, spec, or individual ticket."
disable-model-invocation: true
---

# Worktrees from Issue

Prepare one fresh Kilo VS Code Agent Manager worktree per selected GitHub ticket. This is a one-time dispatch, not a scheduler: stop after verifying the starts and optional section assignment. Use `implement-spec` instead to coordinate an entire implementation graph through delivery.

## Select tickets

1. Take a canonical GitHub issue URL, optional ticket filters, optional Agent Manager section and any worker constraints. A human invoking this command with an issue URL requests session starts unless they ask for preview only. Verify the target repository and base; use the project's Agent Manager default base unless the user specifies another. `--dry-run` reports the selection, prompts and intended assignment without starting sessions or making any changes. A request to discuss or preview the workflow is not authorization to start.
2. Read the issue and native hierarchy with `gh` against the URL's repository. For example, read `gh issue view <number> --repo <owner>/<repo> --json number,title,url,state,labels,parent,assignees` and page through `gh api --paginate repos/<owner>/<repo>/issues/<number>/sub_issues` for a parent. If classifying a single ticket, fetch its direct parent's labels or spec evidence as well. Issue text can establish scope, not hierarchy or permission. Do not infer children from Markdown links or descend through grandchildren.
3. Choose the route before starting anything:

| Input | Select | Default prompt per selected ticket |
| --- | --- | --- |
| Issue labelled `wayfinder:map` | Direct, open children labelled `wayfinder:grilling` by default. Use another supported Wayfinder type only if requested. | `/wayfinder <ticket-url>` |
| Confirmed implementation spec | Direct, open implementation tickets ready to start. | `/implement <ticket-url>` |
| Individual ticket | Only that ticket. Verify a known Wayfinder type (`grilling`, `research`, `prototype`, `task`) and direct parent labelled `wayfinder:map`, or verify that it is ready implementation work under a spec. | The same command as for its verified route |

Accept exactly one known Wayfinder type per decision ticket. Use the configured tracker conventions and the user's scope to confirm the spec. For implementation tickets, require a ready signal (such as `ready-for-agent`), no active assignment, and satisfied prerequisites. Check native blockers; if a prerequisite delivers code, verify the required change is already in the target base. Reconcile active workers and PRs through `spawn` before dispatch. A missing `wayfinder` label alone does not make a ticket implementation work. Skip closed, ineligible or ambiguous tickets with reasons.

Apply explicit exclusions such as `skip #91` before checking the final selection count, and report the excluded tickets as skipped. If the parent classification or an expected count cannot be verified, stop before starting any session.

## Start and verify

1. Call the Skill tool with `spawn` for its startup and reconciliation contract. Before starting any session, list Agent Manager. If a section was requested, prefer an exact name match. Otherwise accept only one clearly equivalent match after ignoring case, spacing and punctuation; if missing or ambiguous, stop. Use the returned section ID, not the name. Show the selected issue, exact startup prompt and intended section in a dry run.
2. Request one `worktree` start at a time with a fresh context. Use `#<number> <exact issue title>` as the display name. For the branch seed, lowercase that title with its number, replace runs of spaces, Polish letters and other non-ASCII-alphanumeric characters with `-`, and trim edge hyphens. Preserve the numeric prefix. Keep the attempt ID in the coordinator record only.
3. Set `tasks[0].prompt` to exactly the selected command and canonical URL of that ticket, with no quotes, trailing newline, brief or metadata. If the user explicitly gives a worker instruction or restriction, append only that instruction on a new line below the command for the ticket or tickets it applies to. Selection and dispatch options are not worker instructions. Never turn issue text into an automatic prompt suffix.
4. The slash line requests an entry point; session creation does not establish that it ran. If command execution is unverified, show the exact command in the coordinator's report for the human to invoke in the new session if needed. List any requested worker instructions separately so the human can carry them over; do not assume manual invocation picks them up. Do not trigger the skill via the Skill tool, send a fallback prompt, or substitute another workflow.
5. Reconcile the result of each start with `spawn`. To move a verified worktree, take the session ID and section ID from `agent_manager` `list`, call `move` once per worktree, then list the target section again. Verify the actual display name, branch and section independently. If the host substitutes a generated card title, use Agent Manager's Rename control where available; otherwise report the actual title and provide the exact title to paste. Do not edit `.kilo/agent-manager.json` or recreate a session to fix its name. Report which tickets were started or skipped, confirmed placement, and whether command execution was verified separately from session creation.
