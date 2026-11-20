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

**In the message, as text.** Numbered, each followed by your recommended answer. Never through the
harness's interactive question prompt, even when it is offered:

- Those prompts are capped per session (Kilo allows a handful), so an interview dies at the third
  question — exactly when it starts to get useful.
- A prompt collapses a question into options, so the user picks one instead of telling you what they
  actually know. The reasons are the material you came for.
- A prompt ends the turn and waits on a UI click; text lets the user answer three questions in one
  message, half-answer the fourth, and correct a term on the way.

Use the `❓ **Q1**` template above, each question followed by `➡️` and your recommended answer. Ask
one round, then wait. If the answer arrives as a normal message — partial, out of order, with a
correction — take what you got, recompute the frontier, and ask the next round the same way.

## Waiting on an answer

Wait without a deadline. Silence is **not** an answer:

- Never treat no reply, a closed prompt, or a timeout as agreement with your recommendation.
- Never continue "with the defaults" because a question did not come back.
- If a round gets no reply, say so in one line and re-ask the **same** round once, not a shorter one.
  Do not shorten the round to make it more likely to be answered: the frontier is the point.
- Do not end the turn to "let the user come back to it later" — that ends the interview with the
  decision unmade.

The frontier stays open until the user answers it or explicitly parks it. Parking is a decision the
user states, not one you infer.

<!-- next-step-pointer -->
> **Before you finish:** name the next step with the `co-dalej` skill (it reads the repo state
> and picks one), or state it yourself in one line with the exact command.
