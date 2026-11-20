---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

## Wiki mode

When the repo keeps an LLM wiki (`wiki/index.md` exists), the decisions ledger goes to
`wiki/processes/grill/<slug>.md` instead of `docs/agents/grill/` or `.scratch/grill/`. A ledger is a
dated process record, so it lives beside `milestones.md`. Paths and frontmatter: `wiki-layout.md` in
`setup-matt-pocock-skills`.

## Where the questions go

A harness may offer an interactive question prompt (Kilo's `question` tool, a UI with selectable
options). When it exists, use it **for the questions of the round** instead of duplicating them as
prose: one prompt per question, with your recommendation as the first option. Still ask one round at
a time, and still wait for the answers before recomputing the frontier. Do not write `Q1 / Q2 / Q3`
in the message and then also fire the prompt: that is the same question twice.

Without such a tool, fall back to the numbered round: each question numbered, followed by `➡️` and
your recommended answer, all in one message, then wait.

## Waiting on an answer

Ask the round through the interactive question prompt when the harness has one, then **wait without a
deadline**. A closed, dismissed, or timed-out card is **not** an answer:

- Never treat silence, a closed prompt, or a timeout as agreement with your recommendation.
- Never continue "with the defaults" because a question did not come back.
- If a card closes with no response, say so in one line, re-ask the same question once, and if it
  closes again, restate the round as plain numbered questions in the message and wait there.
- Do not end the turn to "let the user come back to it later" — that ends the interview with the
  decision unmade.
- Do not shorten the round to a single question to reduce the chance of losing it: ask the whole
  frontier, then wait.

The frontier stays open until the user answers it or explicitly parks it. Parking is a decision the
user states, not one you infer.

<!-- next-step-pointer -->
> **Before you finish:** name the next step with the `co-dalej` skill (it reads the repo state
> and picks one), or state it yourself in one line with the exact command.
