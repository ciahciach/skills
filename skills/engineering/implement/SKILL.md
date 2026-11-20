---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Call the Skill tool with "tdd" where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, call the Skill tool with "code-review" to review the work.

Commit your work to the current branch.

## Wiki mode

Read `docs/agents/domain.md` before the first slice: it names the tracker and, when present, the
`## Wiki mode` section that moves interview ledgers to `wiki/processes/grill/` and ADRs to
`wiki/decisions/`. Do not create `docs/adr/` in a wiki repo, and do not restate a decision that
already has a page: link to it.

<!-- next-step-pointer -->
> **Before you finish:** name the next step with the `co-dalej` skill (it reads the repo state
> and picks one), or state it yourself in one line with the exact command.
