## What it does

`implement-spec` coordinates a [spec](https://www.aihero.dev/ai-coding-dictionary/spec) split into implementation issues. It reads them as a **task graph**, not a list: the **frontier** is the work whose blockers have landed. The host profile determines how work lands:

| Host | Landing model |
| --- | --- |
| Kilo VS Code | The coordinating [agent](https://www.aihero.dev/ai-coding-dictionary/agent) uses `spawn` for isolated Agent Manager sessions. Each issue gets its own PR; a human merges it. |
| Other hosts | Implementer [subagents](https://www.aihero.dev/ai-coding-dictionary/subagent) work across the frontier and land on one **integration branch**, with [code-review](https://aihero.dev/skills-code-review) over the result. |

## When to reach for it

You invoke this by typing `/implement-spec`, and the agent won't reach for it on its own.

| Your situation | Reach for |
| --- | --- |
| Kilo VS Code: a closed list of issues to coordinate with separate PRs | `/implement-spec` with the issue list and agreed base |
| Other hosts: a spec with blocking edges to land on one integration branch | `/implement-spec` with the spec pointer |
| One ticket at a time, in your own [context window](https://www.aihero.dev/ai-coding-dictionary/context-window), [clearing](https://www.aihero.dev/ai-coding-dictionary/clearing) between tickets | [implement](https://aihero.dev/skills-implement) |
| A spec that isn't split into tickets yet | [to-tickets](https://aihero.dev/skills-to-tickets) first |
| A small piece of work with no real graph to it | [implement](https://aihero.dev/skills-implement) directly |

## Prerequisites

- **An issue tracker.** The skill reads the issues from the tracker [setup-matt-pocock-skills](https://aihero.dev/skills-setup-matt-pocock-skills) configured. If none has been configured, it stops and tells you to run that first rather than guessing.
- **Issues with blocking edges**, as [to-tickets](https://aihero.dev/skills-to-tickets) writes them. Without edges the graph is flat, but Kilo still applies its execution limit.
- **Kilo VS Code:** Agent Manager, an explicit commission covering a closed issue list and worktree starts, an agreed base, and a tracker with verifiable PR merges.
- **Other hosts:** A [harness](https://www.aihero.dev/ai-coding-dictionary/harness) that runs subagents in the background and gives each one a git worktree.

## The Kilo Frontier

In Kilo VS Code, invoke `/implement-spec` with the spec, the exact issues to execute, the target base, and any override to the default of three active execution slots. Specify whether workers may commit, push, and open PRs. The coordinator distinguishes a queued prompt from actual work and a finished worker from a merged issue. A ready PR or green CI cannot unlock dependent work. After a verified human merge it refills the frontier without waiting for an entire wave. An integration branch is a separately agreed exception.

## The Integration Branch on Other Hosts

Everything lands on one branch. Each implementer:

1. confirms its worktree is based on the integration branch before it starts,
2. builds its ticket with [tdd](https://aihero.dev/skills-tdd), red-green one slice at a time,
3. merges the integration branch tip into its own branch before reporting done, so landing it is a fast-forward.

The tracker decides whether a pull request exists at all. If your tracker closes work through PRs, or you ask for one, the skill opens a draft PR after the first merge and marks it ready at the end. Otherwise the run stops on the integration branch with every ticket resolved the way your tracker closes work, which works fully offline against a local markdown tracker.

Implementers talk to the orchestrator through [context pointers](https://www.aihero.dev/ai-coding-dictionary/context-pointer) (the spec, the ticket, shared exploration notes, earlier commits) rather than pasted summaries. This keeps each subagent's prompt small and leaves room in the orchestrator's window for the graph.

## Common questions

**What happens while Kilo waits for a human or a merge?**

`HITL wymagany` identifies the native question, permission or merge that needs human action. Independent work can continue. The coordinator returns on a verifiable notification or a scheduled recheck; if neither is available, it reports that automatic continuation is unavailable. Sessions, worktrees and branches stay in place for separate cleanup.

The questions below about the integration branch and whole-spec review describe the other-host profile. Kilo reviews each candidate before commit and reviews changes together when they affect a shared contract or accumulate risk. A PR awaiting required combined review stays unpublished or in draft. If review on an open PR becomes stale:

- **Authorized to change PR status:** The coordinator returns the PR to draft.
- **Not authorized:** The coordinator asks the human to hold the merge.

**How is this different from running `/implement` on each issue myself?**

With `implement` you are the dispatcher: one [session](https://www.aihero.dev/ai-coding-dictionary/session) per issue, clearing in between and keeping track of what is unblocked. `implement-spec` hands dispatch to one coordinator. In Kilo VS Code you explicitly commission the issue list and worktree starts, and still own every merge. On other hosts you start with a spec pointer and review the integration branch at the end. For a small change with no real graph, use `implement` directly.

**Does it need GitHub? I want it to stop at the branch.**

- **Kilo VS Code:** The tracker must provide verifiable PR merges. A local branch on its own cannot unlock dependencies.
- **Other hosts:** The workflow can run offline and stop at the integration branch. A PR opens only when the configured tracker closes work through PRs or you ask for one.

**Its review and fix loop ran for hours, or kept "fixing" tickets that hadn't been built yet.**

Both happen when `code-review` runs anywhere other than the one point the skill gives it. It compares the code against the whole spec, so it only makes sense once every ticket has landed. If it runs mid-run, every unbuilt ticket reads as a failure. The agent then builds that ticket, and that triggers another review. At the end, the skill runs `code-review` once and sends every finding to one fix subagent, but it doesn't yet say when to stop after that fix. One user reported a five-ticket feature where "the review and fix loop took roughly four hours". If you see a second broad review start, tell it to run focused checks for the fixed findings and stop. Expect that first review to find real problems. The run's output is a draft that the review completes, not something to ship on its own.

**Does it drive tdd like implement does?**

It does now, though it didn't at first. Users running the in-progress version noticed that "the implementer subagents don't inherit the /tdd directive", so red-green stopped as soon as they scaled up from one ticket to a whole spec. Each implementer now builds its ticket with `tdd`. There is still no step where you agree seams interactively, as there is in an `implement` session, so name the seams in the spec or the tickets if you want them pinned.

**Two implementers running in parallel collided on the same file, or picked different names for the same thing.**

Worktrees don't remove collisions; they postpone them to merge time. A blocking edge written from ticket text is a guess about which files each ticket will touch, and two tickets on "different parts of the codebase" still share a message catalogue, a config registry, or a type. Each implementer sees only its own ticket and the shared notes, never the other's work in progress, so one user's web and mobile tickets added the same string as `blockedSince` and `blockedOn`. When two frontier tickets touch one shared file, either add a blocking edge between them so they run one after the other, or have the exploration notes fix the exact names each ticket adds.

**Blocked tickets never start, even after their blocker has merged.**

This is a known problem on GitHub. The tracker's blocked-by count only drops when a blocker *closes*, and tickets typically close when the PR merges, which is the end of the run. The tracker is the right source for the starting graph but a stale one mid-run. Tell the orchestrator to track which tickets have merged into the integration branch itself and compute the frontier from that.

**Does this replace Sandcastle or an AFK script?**

No. People ask because the skills now reach into implementation: "is Sandcastle still relevant? Your skills now seem to be able to handle implementation as well." `implement-spec` puts an agent in charge of orchestration inside one harness session, which needs no infrastructure and lets you watch and steer. For work that is truly [AFK](https://www.aihero.dev/ai-coding-dictionary/afk), a deterministic loop ([Sandcastle](https://github.com/mattpocock/sandcastle), a shell script, a CI job) is faster, cheaper, and more reliable, because no agent makes the orchestration decisions.

**A ticket's key test was skipped inside its worktree, and it reported green.**

A worktree holds only what git tracks. Tests that read gitignored fixtures, local databases, or credentials can silently skip there. For a ticket whose verification depends on untracked material, tell the orchestrator to run it in the main checkout instead.

## It's working if

- Several implementers are running at once whenever the graph and host allow.
- In Kilo VS Code, a dependent issue starts only after the last verified human merge. Each PR shows review evidence for its published diff.

On other hosts:

- An issue starts as soon as its last blocker lands on the integration branch, not when the whole run ends.
- Every issue's trace shows `tdd` running, with a failing test before the code.
- Merges into the integration branch are fast-forwards, not conflict resolutions.
- The run ends on one branch with every issue resolved, and a PR only if your tracker wanted one.

## Where it fits

`implement-spec` is the build step of the main chain, as the parallel alternative to running [implement](https://aihero.dev/skills-implement) once per ticket:

```txt
grill-with-docs → to-spec → to-tickets → implement-spec → retro
```

Its neighbours are [to-tickets](https://aihero.dev/skills-to-tickets), which declares blocking edges, and [code-review](https://aihero.dev/skills-code-review), which checks the candidate PR diff in Kilo VS Code or the integration branch on other hosts. [ask-matt](https://aihero.dev/skills-ask-matt) routes between workflows.
