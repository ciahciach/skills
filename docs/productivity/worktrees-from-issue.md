## What it does

`worktrees-from-issue` prepares one Kilo VS Code Agent Manager worktree per selected GitHub ticket. It uses GitHub's native issue hierarchy to distinguish a decision ticket from an implementation ticket before choosing the startup prompt.

## When to reach for it

Type `/worktrees-from-issue <github-issue-url>` to start the selected sessions. The agent does not invoke this skill on its own. Add `--dry-run` to preview the tickets, prompts and section without creating worktrees.

| What you have | What the skill prepares |
| --- | --- |
| A Wayfinder map | One `/wayfinder <ticket-url>` prompt per open, direct `wayfinder:grilling` child by default |
| An implementation spec | One `/implement <ticket-url>` prompt per ready, direct implementation ticket |
| An individual ticket | One prompt for the verified route, without picking its siblings |

## Prerequisites

Open the target repository in Kilo VS Code with Agent Manager available. The GitHub CLI needs read access to the issue hierarchy and dependencies.

## Common questions

**Do the startup prompts run automatically?**

Not necessarily. Agent Manager can deliver the slash line as plain text. The start report distinguishes worktree creation from command execution and shows the exact command to run manually if needed. Carry over any requested worker instructions separately if you run it by hand.

**Can I skip a ticket or add an instruction for just one session?**

Yes. Add `skip #91` to exclude that ticket, or say `For #92, also tell me which alternatives were considered` to add an instruction below the command in that session only. Without an explicit worker instruction, the whole startup prompt is the command and the ticket URL on one line.

**What if Agent Manager shortens the card title?**

The skill checks the displayed title separately from the branch and section. If it cannot use the Rename control, it reports the title to paste without duplicating the session.

## It's working if

- Every selected ticket has its own worktree and the prompt names that ticket, not its parent.
- Closed tickets, grandchildren, blocked implementation tickets and tickets you excluded do not get worktrees.
- If you request a section, each new worktree appears there and has the exact issue title or a reported naming discrepancy.

## Where it fits

This is a one-time dispatch. [spawn](https://aihero.dev/skills-spawn) handles each start and its verification; [implement-spec](https://aihero.dev/skills-implement-spec) is for coordinating the entire graph through delivery. [ask-matt](https://aihero.dev/skills-ask-matt) maps the wider workflow.
