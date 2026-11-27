## What it does

`setup-matt-pocock-skills` records a repo's Issue tracker, triage labels and domain layout in markdown, using `docs/agents/` by default and preserving established locations. If you opt in to Excel versioning, it includes the Excel scaffold in the same proposal without requiring a second command or a workbook.

The files vary by repo; the skills do not. They follow the repo's tracker guidance rather than assuming GitHub. This fork's setup also offers shared Issue tracker, Kilo Code in VS Code, Excel and general workflow terminology in the existing project glossary (default: root `GLOSSARY.md`), even when the repo does not use Excel.

It is a prompt-driven skill, not a deterministic script. It reads your active instructions, glossary and Git remote, proposes changes and waits for you to confirm before it writes anything.

## When to reach for it

You invoke this by typing `/setup-matt-pocock-skills`; the [agent](https://www.aihero.dev/ai-coding-dictionary/agent) won't reach for it on its own. Its metadata marks it non-invokable on purpose, so no other skill can fire it for you.

- Run it before the first use of an engineering skill that needs tracker and domain configuration, even if the project is already underway. For example, [triage](https://aihero.dev/skills-triage) should not have to guess your tracker or its labels.
- Rerun it explicitly to review updates to the shared glossary. The skill reads the existing glossary and proposes only targeted changes.

- Opt in to Excel versioning to include the scaffold and the Excel section of `CODING_STANDARDS.md` in the same proposal, even before the first workbook. Opt-in selects the scope; applying the exact diff still requires approval. No workbook is created or registered.
- Use the standalone `/setup-excel-repo` beta from the source checkout or a link to it if you want only Excel setup and the missing engineering minimum. Both keep existing repo conventions and use the same glossary and Excel standard.

## Prerequisites

It writes into the repo you run it in:

| It writes | Default location if not already configured |
| --- | --- |
| `issue-tracker.md` | `docs/agents/` |
| `domain.md` | `docs/agents/` |
| `GLOSSARY.md` and, for an existing map, a link in `GLOSSARY-MAP.md` | repo root, only for approved glossary changes |
| `triage-labels.md` | `docs/agents/`, only when the `triage` skill is installed |
| An `## Agent skills` block | the active instruction file, following any existing pointer to it |
| Excel pointer, repo contract and shared Excel section | active instructions, existing runbook (default `docs/agents/excel.md`) and root `CODING_STANDARDS.md`, only after opt-in and diff approval |

You commit all of it as markdown. There is no user-level or global mode. The config lives in the repo, so every repo gets its own copy.

## Setup choices

It keeps choices that are already established and recommends defaults when choices are missing. Excel is a separate, explicit opt-in.

| Decision | What it proposes | When it asks |
| --- | --- | --- |
| **Issue tracker** | existing tracker, or one matching your `git remote` | when a tracker choice needs confirmation |
| **Triage labels** | keep the five canonical names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) | only if the `triage` skill is installed |
| **Domain docs** | preserve an existing `GLOSSARY-MAP.md`; otherwise default to single-context | only if it spots monorepo signals and there is no map, and then it offers a multi-context layout |
| **Excel setup** | include versioning guidance and the shared Excel standard | before proposing changes, even without a workbook |

The tracker options:

| Option | Where issues live | Needs |
| --- | --- | --- |
| **GitHub** | the repo's GitHub Issues | the `gh` CLI |
| **GitLab** | the repo's GitLab Issues | the `glab` CLI |
| **Local markdown** | files under `.scratch/<feature>/` in this repo | nothing, not even a remote |
| **Other** | wherever you say | one paragraph from you describing the workflow |

The first three ship as templates in the skill and work out of the box. Local markdown is a full option, not a fallback. The skill supports a solo project with no remote. One caveat: don't use local markdown if you use GitHub. They are alternatives, so pick one.

"Other" is a full option too. It is how Jira, Linear, Azure DevOps and Beads all work. You describe the workflow, the skill records your prose in `docs/agents/issue-tracker.md`, and the downstream skills follow the prose. Users have already built this: a Jira-over-[MCP](https://www.aihero.dev/ai-coding-dictionary/mcp) variant, a Gitea CLI shaped like `gh`, a hand-built local dashboard.

## Common questions

**Do I have to use GitHub?**

No. GitHub, GitLab and local markdown under `.scratch/` all ship as ready-made templates, and anything else works through the "other" path. This is the most-repeated question, in roughly these words: *"hard locked to github"*, *"can I use GitLab / Jira"*, *"what about Azure DevOps"*. The answer is always the same: setup chooses the tracker, not the skill.

**Do I need to re-run it after updating the skills?**

No update runs setup for you. Run it explicitly to review new shared terms or proposed updates to entries you previously adopted. A run with no approved glossary changes leaves the glossary and map untouched.

**What if I already have a glossary?**

What setup can propose depends on where the term lives:

- In the root glossary, it can propose replacing a conflicting local definition. Without explicit approval, the local entry stays where it is.
- In a mapped context, it leaves local definitions untouched. The context definition takes precedence there.

In the proposal you can see:

- Shared terms missing from the root `GLOSSARY.md`.
- The current and proposed versions of previously adopted entries that changed.
- Both definitions when a local term conflicts with a shared one.

Only approved changes are written, with the bundled source and adopted version recorded for each shared entry.

**Which instruction file gets the links?**

The proposal targets the file your [harness](https://www.aihero.dev/ai-coding-dictionary/harness) reads, following any pointer to a canonical file. If neither file exists, the skill asks which to create. With Excel opt-in, both sets of links go into the same file.

**It didn't create my triage labels.**

`docs/agents/triage-labels.md` is a *mapping*: it tells `/triage` which strings in your tracker correspond to the five canonical roles. On GitHub or GitLab, creating missing labels requires separate approval; approving the file diff is not enough. Two consequences:

- If your tracker already uses the canonical names, the mapping is an identity table and there is nothing to configure. That is the intended common case, not a missing step.
- This skill does not create [wayfinder](https://aihero.dev/skills-wayfinder)'s `wayfinder:map` and `wayfinder:<type>` labels either, and `gh issue create --label <missing>` fails instead of creating the label. Create them by hand before the first wayfinder run on a GitHub repo.

**Can I configure the other skills' behaviour here ([grilling](https://www.aihero.dev/ai-coding-dictionary/grilling) cadence, question format, tone)?**

No. It configures repo conventions, not individual skill preferences. The skills stay opinionated and take no per-user config. Preferences belong in the active instruction file as plain instructions.

**Can I keep the config in `~/.claude` instead of committing it to every repo?**

Not today. A user who runs the skills across many repos has an open request for this, but no user-level mode exists. Every repo carries its own `docs/agents/`.

**Isn't it strange to have a skill that configures the other skills?**

One long-standing complaint says yes, in these words: *"having a skill to set up the other skill does not feel right to me: that means the LLM is configuring its own skills."* The trade-off is real. Without a setup step, every skill that touches issues would need its own copy of the tracker instructions. The output is markdown you can read and edit, and that limits the risk. You can read every file it wrote and change it by hand. Make day-to-day changes that way, not with another run.

## It's working if

- An `## Agent skills` section in the instruction file your harness reads points to the active tracker and domain guides, plus the triage mapping if it is configured.
- Adopted shared entries appear in a separate section. Unapproved definitions and existing context mappings are preserved, and a rerun with no approved changes leaves the glossary files untouched.
- With Excel opt-in, you see one proposal, with separate approval for the glossary diff. Declining Excel leaves any existing Excel setup intact.
- The tracker it proposed matches the one you use, and the label strings match labels that exist in your tracker or that you separately approve creating.
- Afterwards, `/to-tickets` publishes without asking you where issues live, and `/triage` applies labels rather than inventing them.
- Nothing in the skill files themselves changed. If setup edited a `SKILL.md`, something went wrong.

## Where it fits

`setup-matt-pocock-skills` is the **initial setup** for the engineering flow, with explicit reruns for shared glossary updates. Its neighbours are [triage](https://aihero.dev/skills-triage), which uses the label vocabulary, and [domain-modeling](https://aihero.dev/skills-domain-modeling), which adds project-specific terms and decisions as they are resolved. [ask-matt](https://aihero.dev/skills-ask-matt) routes the whole set.
