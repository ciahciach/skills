---
name: setup-matt-pocock-skills
description: "Configure this repo for the engineering skills: set up its issue tracker, triage label vocabulary, and domain doc layout. Run once before first use of the other engineering skills."
disable-model-invocation: true
---

# Setup Matt Pocock's Skills

Scaffold the per-repo configuration that the engineering skills assume:

- **Issue tracker**: where issues live (GitHub by default; local markdown is also supported out of the box)
- **Triage labels**: the strings used for the five canonical triage roles
- **Domain docs**: where `GLOSSARY.md` and ADRs live, and the consumer rules for reading them

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm with the user, then write.

## Process

### 1. Explore

Look at the current repo to understand its starting state. Read whatever exists; don't assume:

- `git remote -v` and `.git/config`: is this a GitHub repo? Which one?
- `AGENTS.md` and `CLAUDE.md` at the repo root: does either exist? Is there already an `## Agent skills` section in either?
- `GLOSSARY.md` and `GLOSSARY-MAP.md` at the repo root, and the legacy `CONTEXT.md` / `CONTEXT-MAP.md`. If a legacy file exists, offer to `git mv` it to its `GLOSSARY` name and rewrite those names in `docs/agents/domain.md`.
- `docs/adr/` and any `src/*/docs/adr/` directories
- `docs/agents/`: does this skill's prior output already exist?
- `.scratch/`: a sign that a local-markdown issue tracker convention is already in use
- Is the `triage` skill installed? (a `triage` skill folder alongside this one, or `triage` in your available skills.) This decides whether Section B runs at all.
- Monorepo signals: a `pnpm-workspace.yaml`, a `workspaces` field in `package.json`, or a populated `packages/*` with its own `src/`. These are present only in a genuinely large multi-package repo; their absence means single-context, which is almost every repo.
- Note existing Excel repo rules or workbook-versioning layout and any current or planned Excel work the user mentioned. No workbook inspection is needed.

### 2. Present findings and ask

Summarise what's present and what's missing. Then take the sections in order. One section, one answer, then the next.

Lead each section with the recommended answer so the user can accept it in a word. Give a one-line explainer only when the choice genuinely branches; skip the section entirely when exploration already settled it (Section B when `triage` isn't installed, Section C when there's no monorepo).

**Section A: Issue tracker.**

> Explainer: The "issue tracker" is where issues live for this repo. Skills like `to-tickets`, `triage`, and `to-spec` read from and write to it. They need to know whether to call `gh issue create`, write a markdown file under `.scratch/`, or follow some other workflow you describe. Pick the place you actually track work for this repo.

Default posture: these skills were designed for GitHub. If a `git remote` points at GitHub, propose that. If a `git remote` points at GitLab (`gitlab.com` or a self-hosted host), propose GitLab. Otherwise (or if the user prefers), offer:

- **GitHub**: issues live in the repo's GitHub Issues (uses the `gh` CLI)
- **GitLab**: issues live in the repo's GitLab Issues (uses the [`glab`](https://gitlab.com/gitlab-org/cli) CLI)
- **Local markdown**: issues live as files under `.scratch/<feature>/` in this repo (good for solo projects or repos without a remote)
- **Other** (Jira, Linear, etc.): ask the user to describe the workflow in one paragraph; the skill will record it as freeform prose

Record the choice in `docs/agents/issue-tracker.md`. The GitHub and GitLab templates carry a "PRs as a request surface" flag, defaulted **off**. Leave it off and don't raise it: a user who wants external PRs in the triage queue can flip the flag in the file later.

A GitHub or GitLab tracker needs a reachable repo. When the user picks one and no `git remote` points at that host, get the repo URL from them and wire it up (`git init` if needed, `git remote add origin <url>`) before going further. Done when `gh repo view` / `glab repo view` prints the project from inside this directory; if it can't, stop and tell the user what's missing.

**Section B: Triage label vocabulary.** Skip this section entirely if the `triage` skill isn't installed (exploration told you), since an uninstalled skill needs no labels.

If it is installed, ask exactly one question:

> Do you want to keep the default triage labels? (recommended: **yes**)

The defaults are the five canonical roles, each label string equal to its name: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. On **yes**, write them as-is. Only if the user says no, usually because their tracker already uses other names (e.g. `bug:triage` for `needs-triage`), collect the overrides so `triage` applies existing labels instead of creating duplicates.

**Section C: Domain docs.** Default to **single-context** (one `GLOSSARY.md` + `docs/adr/` at the repo root). This fits almost every repo; write it without asking. If Section D turns wiki mode on, the ADR half of that layout is `wiki/decisions/` — write that path, not `docs/adr/`.

Offer **multi-context** (a root `GLOSSARY-MAP.md` pointing to per-context `GLOSSARY.md` files) only when exploration found monorepo signals. Then confirm which layout they want.

**Section D: Wiki mode.** Ask in every repo, including one with no `wiki/` yet — an LLM wiki is
cheap to start and expensive to retrofit.

> Does this repo keep its knowledge in an LLM wiki? (recommended: **yes** when `wiki/index.md`
> exists, **bootstrap it** when the repo has neither `wiki/` nor `docs/adr/`, **no** otherwise)

Three answers, not two:

- **Yes, exists** — read `wiki/index.md` and record the paths that are really there.
- **Yes, bootstrap** — create the minimum: `wiki/index.md`, `wiki/decisions/`,
  `wiki/processes/grill/`, `wiki/processes/governance.md`. Nothing else: an empty page nobody
  maintains is worse than no page, and a wiki that starts as a graveyard is abandoned in a month.
- **No** — ADRs go to `docs/adr/`, ledgers to `docs/agents/grill/`, and no `## Wiki` block is written.

On **yes** (either flavour), the ADR path in `docs/agents/domain.md` becomes `wiki/decisions/`, the
interview ledger becomes `wiki/processes/grill/<slug>.md`, and `GLOSSARY.md` stays at the repo root
because an agent reads it in one call. The full mapping, the merged frontmatter and the idempotent
bootstrap live in `wiki-layout.md` in this skill's directory: read it before writing.

**The decisions register has one shape, and setup must respect the one the repo already has.**

- New decisions are files: `wiki/decisions/NNNN-<slug>.md`.
- If a single-file register already exists (`wiki/decisions.md`, `docs/decisions.md`), it becomes the
  **index**: link the new ADRs from it, leave its history in place. Do not rename it, do not move it,
  and do not split its old content in this run — a rename breaks links across the repo and in whatever
  points at it from outside.
- Splitting an old register entry into its own ADR happens one decision at a time, when that decision
  is next touched. Until then the index points at the section instead of copying it.
- `docs/adr/` is never created in wiki mode, and one decision never lives in two places.

Three rules matter more than the paths: **one artifact, one home** (a decision that exists in both
`docs/adr/` and `wiki/decisions/` will drift apart within a week), **`last_verified` moves only after
a real re-check** (never on a typo edit, never because a commit exists), and **two queues with two
scopes** — `.scratch/` for the work items these skills drive, `wiki/` for the repo's knowledge. The
same ticket never lives in both: the wiki links to the tracker, the tracker links to the wiki.

**Section E: Repo rules worth recording.** Two lines that cost nothing now and save a mess later.
Write them into the `## Wiki` block only when wiki mode is on, and phrase them in the repo's language:

- **Configuration is not a milestone.** Tooling setup goes to `CHANGELOG.md` if the repo has one; it
  does not consume a milestone number, because numbers are for work whose outcome someone can verify.
  Never renumber milestones that are already written down — leave the gap and apply the rule from now on.
- **Facts carry provenance.** Wherever the repo writes observations, use the vocabulary it already
  has. If it has none, propose `USER_CONFIRMED / OBSERVED / INFERRED / PROPOSED` rather than
  inventing a ranking like `confidence: high` that no one can check against anything.

### 3. Confirm and edit

Show the user a draft of:

- The `## Agent skills` block to add to whichever of `CLAUDE.md` / `AGENTS.md` is being edited (see step 4 for selection rules)
- When a new instruction file is being created: the whole filled `agents-template.md`, with the
  sections that don't apply already removed, not just the block
- The contents of `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, and `docs/agents/triage-labels.md` (the last only when `triage` is installed)

Let them edit before writing.

### 4. Write

**Pick the file to edit:**

- If `CLAUDE.md` exists, edit it.
- Else if `AGENTS.md` exists, edit it.
- If neither exists, ask the user which one to create; don't pick for them.
- When the user chose to create one, start from `agents-template.md` in this skill's directory.
  It covers what these skills expect (tracker, wiki, provenance, git discipline) plus the generic
  rules a repo needs and no skill owns: autonomy limits, safe text editing, change boundaries,
  versioning, and retention. Leave the Excel and Power Query sections out of new instruction files;
  the optional Excel handoff below is separate. Fill in the `<...>` placeholders,
  **delete the sections that don't apply**, and append the `## Agent skills` / `## Wiki` blocks.
  Never ship the template with placeholders: a dead section reads as a requirement.

Never create `AGENTS.md` when `CLAUDE.md` already exists (or vice versa); always edit the one that's already there.

If an `## Agent skills` block already exists in the chosen file, update its contents in-place rather than appending a duplicate. Don't overwrite user edits to the surrounding sections.

Editing an existing instruction file is surgery, not a rewrite:

- **Append, never reorder.** The file is a governance document; its existing sections may carry rules
  you cannot see the reason for. New blocks go at the end under their own heading.
- **Match the file's language**, including headings. A Polish repo gets `## Wiki`, not `## Wiki (LLM wiki)`
  bolted onto English prose.
- **Idempotent by heading.** Two runs must leave one `## Agent skills` and one `## Wiki`, not four.
- If the file has `USER_CONFIRMED` markers or similar, treat them as immutable: your block is a new
  section, not an edit to their decisions.

The block:

```markdown
## Agent skills

### Issue tracker

[one-line summary of where issues are tracked]. See `docs/agents/issue-tracker.md`.

### Triage labels

[one-line summary of the label vocabulary]. See `docs/agents/triage-labels.md`.

### Domain docs

[one-line summary of layout: "single-context" or "multi-context"]. See `docs/agents/domain.md`.
```

That is one section. When Section D said yes, write a **second, separate** section at the end of the
file — two headings, not one merged block:

```markdown
## Wiki

- Knowledge lives in `wiki/`; start from `wiki/index.md`.
- Artifact locations and reading rules: `docs/agents/domain.md`.
- Maintenance and verification rules: `wiki/processes/governance.md`.
- [one line: two queues — tracker for work items, wiki for knowledge]
- [one line: configuration is not a milestone]
```

The two bracketed lines come from Section E; fill them in the repo's language, or drop them when the
repo has neither milestones nor a second backlog to disambiguate.

Include the `### Triage labels` sub-block, and write `docs/agents/triage-labels.md`, only when `triage` is installed and Section B ran. When it isn't, both are omitted.

When Section B ran on GitHub or GitLab, create each configured label the tracker lacks (`gh label create` / `glab label create`).

Then write the docs files using the seed templates in this skill folder as a starting point:

- [issue-tracker-github.md](./issue-tracker-github.md): GitHub issue tracker
- [issue-tracker-gitlab.md](./issue-tracker-gitlab.md): GitLab issue tracker
- [issue-tracker-local.md](./issue-tracker-local.md): local-markdown issue tracker
- [triage-labels.md](./triage-labels.md): label mapping (only if `triage` is installed)
- [domain.md](./domain.md): domain doc consumer rules + layout

For "other" issue trackers, write `docs/agents/issue-tracker.md` from scratch using the user's description.

### 5. Done

Tell the user the setup is complete and which engineering skills will now read from these files. Mention they can edit `docs/agents/*.md` directly later; re-running this skill is only necessary if they want to switch issue trackers or restart from scratch.

Before you say it's done, prove it — read back what you wrote and report the result, not the intention:

- `docs/agents/` holds the files you claim (list them).
- The instruction file has exactly one `## Agent skills` block, and one `## Wiki` block when wiki mode
  is on.
- In wiki mode: `wiki/decisions/` exists, and the decisions index is either new or untouched apart
  from the added links.
- `git diff --check` passes. For brand-new files git has nothing to check, so run
  `git diff --no-index --check -- NUL <file>` (or `/dev/null` on unix) on each one.
- Report what you deliberately did **not** do: no commit, no renames, no binary or Excel-adjacent
  files touched, no migration of existing wiki content.

Configuring a repo is not a milestone. If the repo records milestones, say plainly that this run
consumed none.

If the user wants to version Excel logic or structure, or exploration found an Excel scaffold,
offer the optional `/setup-excel-repo` beta. If Excel intent is unknown, mention that the option
also works before the first workbook. On explicit opt-in, give exactly one next step: run
`/setup-excel-repo` themselves in this repo if available in their harness. This satisfies the
next-step pointer below. On refusal, leave the Excel scaffold untouched. Matt's setup does not
invoke or install the beta, create or edit its scaffold, or onboard a workbook. The beta reuses
the tracker and knowledge layout configured here.
