---
name: setup-matt-pocock-skills
description: "Configure this repo's issue tracker, triage labels, domain docs and shared glossary for the engineering skills."
disable-model-invocation: true
---

# Setup Matt Pocock's Skills

Scaffold the per-repo configuration that the engineering skills assume:

- **Issue tracker**: where issues live (GitHub by default; local markdown is also supported out of the box)
- **Triage labels**: the strings used for the five canonical triage roles
- **Domain docs**: where `GLOSSARY.md` and ADRs live, and the consumer rules for reading them
- **Shared glossary**: the bundled starter vocabulary, even in repos without Excel

This is a prompt-driven skill, not a deterministic script. Explore, present what you found, confirm with the user, then write.

## Process

### 1. Explore

Look at the current repo to understand its starting state. Read whatever exists; don't assume:

- `git remote -v` and `.git/config`: is this a GitHub repo? Which one?
- `AGENTS.md` and `CLAUDE.md` at the repo root: does either exist? Is there already an `## Agent skills` section in either?
- `GLOSSARY.md` and `GLOSSARY-MAP.md` at the repo root, their mapped context glossaries, and the legacy `CONTEXT.md` / `CONTEXT-MAP.md`. If a legacy file exists, offer to `git mv` it to its `GLOSSARY` name and rewrite those names in `docs/agents/domain.md`. Base the glossary proposal on the layout after any separately approved rename; do not create a competing glossary over an unresolved legacy location.
- `docs/adr/` and any `src/*/docs/adr/` directories
- `docs/agents/`: does this skill's prior output already exist?
- `.scratch/`: a sign that a local-markdown issue tracker convention is already in use
- Is the `triage` skill installed? (a `triage` skill folder alongside this one, or `triage` in your available skills.) This decides whether Section B runs at all.
- Monorepo signals: a `pnpm-workspace.yaml`, a `workspaces` field in `package.json`, or a populated `packages/*` with its own `src/`. These are present only in a genuinely large multi-package repo; their absence means single-context, which is almost every repo.
- Note existing Excel repo rules or workbook-versioning layout and any current or planned Excel work the user mentioned. No workbook inspection is needed.

### 2. Present findings and ask

Summarise what's present and what's missing. Then take the sections in order. One section, one answer, then the next.

Lead each section with the recommended answer so the user can accept it in a word. Give a one-line explainer only when the choice genuinely branches; skip the section entirely when exploration already settled it (Section B when `triage` isn't installed, Section C when there's no monorepo).

Keep established tracker, triage, wiki, glossary and ADR conventions unless the user explicitly requests a change. Follow existing pointers to their authoritative homes rather than creating competing copies. Surface any unresolved conflicts and omit dependent edits from the proposal.

**Section A: Issue tracker.**

> Explainer: The "issue tracker" is where issues live for this repo. Skills like `to-tickets`, `triage`, and `to-spec` read from and write to it. They need to know whether to call `gh issue create`, write a markdown file under `.scratch/`, or follow some other workflow you describe. Pick the place you actually track work for this repo.

Recommend the established Issue tracker, even when `git remote` points to a different service. Only if there is no established tracker, use the remote as a hint for GitHub or GitLab (`gitlab.com` or a self-hosted host). For a fresh repo without a tracker or remote, recommend Local Markdown. Offer alternatives when no choice is established or the user requests a change:

- **GitHub**: issues live in the repo's GitHub Issues (uses the `gh` CLI)
- **GitLab**: issues live in the repo's GitLab Issues (uses the [`glab`](https://gitlab.com/gitlab-org/cli) CLI)
- **Local markdown**: issues live as files under `.scratch/<feature>/` in this repo (good for solo projects or repos without a remote)
- **Other** (Jira, Linear, etc.): ask the user to describe the workflow in one paragraph; the skill will record it as freeform prose

Keep the existing tracker guide in its authoritative location. For a new guide, use `docs/agents/issue-tracker.md`. If a consumer requires that default path but the guide already lives elsewhere, propose only a pointer, not a second guide. The GitHub and GitLab templates carry a "PRs as a request surface" flag, defaulted **off**. Leave it off and don't raise it: a user who wants external PRs in the triage queue can flip the flag in the file later.

A GitHub or GitLab tracker needs a reachable repo. If the user selects one without a matching remote, confirm the project URL and check that it is reachable without writing. Connecting the remote (or initialising Git if needed) is a separate change: describe it and wait for specific approval before doing it. If the project cannot be verified, report the missing dependency.

**Section B: Triage label vocabulary.** Skip this section entirely if the `triage` skill isn't installed (exploration told you), since an uninstalled skill needs no labels.

If it is installed and there is no existing mapping, ask exactly one question:

> Do you want to keep the default triage labels? (recommended: **yes**)

The defaults are the five canonical roles, each label string equal to its name: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. On **yes**, write them as-is. Only if the user says no, usually because their tracker already uses other names (e.g. `bug:triage` for `needs-triage`), collect the overrides so `triage` applies existing labels instead of creating duplicates.

**Section C: Domain docs.** Reuse existing glossary and ADR locations. For a fresh repo, default to **single-context** (root `GLOSSARY.md` and `docs/adr/`) without asking a layout question. Record the chosen layout in the domain guide; glossary changes require separate approval. Section D supplies the paths if using a wiki.

Preserve an existing `GLOSSARY-MAP.md` and its multi-context layout regardless of monorepo signals. Offer a new **multi-context** layout only when exploration found monorepo signals. Then confirm which layout they want.

**Section D: Wiki mode.** Ask in every repo, including one with no `wiki/` yet — an LLM wiki is
cheap to start and expensive to retrofit.

> Does this repo keep its knowledge in an LLM wiki? (recommend the existing wiki if any, **no** if the
> repo already has non-wiki domain or ADR conventions, and **bootstrap it** only if neither exists)

Three answers, not two:

- **Yes, exists** — read `wiki/index.md` and record the paths that are really there.
- **Yes, bootstrap** — create the minimum: `wiki/index.md`, `wiki/decisions/`,
  `wiki/processes/grill/`, `wiki/processes/governance.md`. Nothing else: an empty page nobody
  maintains is worse than no page, and a wiki that starts as a graveyard is abandoned in a month.
- **No**: keep the repo's non-wiki paths if present; otherwise default to `docs/adr/` and `docs/agents/grill/`. Do not draft a `## Wiki` block.

For a new wiki, use `wiki/decisions/` for ADRs and `wiki/processes/grill/<slug>.md` for ledgers.
For an existing wiki, use its actual paths in the domain guide and instruction pointers, even when
they differ from [the wiki seed](./wiki-layout.md). Read the seed for bootstrap and frontmatter when needed.

**The decisions register has one shape, and setup must respect the one the repo already has.**

- New decisions follow the established ADR convention; the new-wiki default is `wiki/decisions/NNNN-<slug>.md`.
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

**Section F: Excel repository setup.** Before showing any diff, offer a clear choice to include workbook versioning, even if the repo has no workbook. Recommend it when the user mentioned Excel work or exploration found an Excel scaffold. Record explicit opt-in to use the shared Excel procedure in step 3. Do not invoke or install `/setup-excel-repo`. On refusal or no opt-in, leave Excel rules, pointers, standard and artifacts untouched.

### 3. Propose and confirm

Use the drafting rules below to prepare one proposal with the exact diff, including new files. With Excel opt-in, merge the general and Excel edits to shared files before showing the diff, and include the Excel findings and unresolved dependencies. The decision to include Excel is not approval to write these files, publish an Issue or operate on a workbook.

In every explicit run, follow the [shared glossary procedure](./shared-glossary-setup.md). Show its exact diff in the same proposal as a separately approvable part. Before writing, get explicit approval of the exact setup diff and separate approval for any glossary changes. A declined or unapproved part is left untouched. If that changes edits in the approved part, show the revised diff and get fresh approval. Report an empty diff without writing.

**Pick the file for the proposal:**

- Use the existing instruction file the harness reads, following any pointer to the canonical file. If Excel is included, use that same file for both sets of guidance.
- If neither exists, ask the user which one to create; don't pick for them.
- When the user chose to create one, start from `agents-template.md` in this skill's directory.
  It covers what these skills expect (tracker, wiki, provenance, git discipline) plus the generic
  rules a repo needs and no skill owns: autonomy limits, safe text editing, change boundaries,
  versioning, and retention. Leave the template's Excel and Power Query sections out; only the
  shared Excel procedure supplies the Excel pointer after opt-in. Fill in the `<...>` placeholders,
  **delete the sections that don't apply**, and append the `## Agent skills` / `## Wiki` blocks.
  Never ship the template with placeholders: a dead section reads as a requirement.

Keep one authoritative set of instructions. If the harness does not read the existing canonical file, propose a native pointer to it rather than copying its rules.

Once the instruction target and engineering choices are settled, follow [Discover and Plan in the shared Excel procedure](./excel-setup.md) if the user opted in. Use those choices instead of standalone defaults.

If an `## Agent skills` block already exists in the chosen file, update its contents in-place rather than appending a duplicate. Don't overwrite user edits to the surrounding sections.

Editing an existing instruction file is surgery, not a rewrite:

- **Append, never reorder.** The file is a governance document; its existing sections may carry rules
  you cannot see the reason for. New blocks go at the end under their own heading.
- **Match the file's language**, including headings. A Polish repo gets `## Wiki`, not `## Wiki (LLM wiki)`
  bolted onto English prose.
- **Idempotent by heading.** Two runs must leave one `## Agent skills` and one `## Wiki`, not four.
- If the file has `USER_CONFIRMED` markers or similar, treat them as immutable: your block is a new
  section, not an edit to their decisions.

The block (use the actual guide locations; these are defaults):

```markdown
## Agent skills

### Issue tracker

[one-line summary of where issues are tracked]. See `docs/agents/issue-tracker.md`.

### Triage labels

[one-line summary of the label vocabulary]. See `docs/agents/triage-labels.md`.

### Domain docs

[one-line summary of layout: "single-context" or "multi-context"]. See `docs/agents/domain.md`.
```

That is one section. When Section D said yes, use a **second, separate** section. Reuse an existing `## Wiki` block and substitute the actual wiki paths:

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

Preserve existing triage guidance. Draft a missing `### Triage labels` sub-block or guide only when `triage` is installed; link the established mapping or the new guide from Section B.

Draft missing docs using the seed templates in this skill folder as a starting point. Keep existing valid docs and links rather than regenerating them:

- [issue-tracker-github.md](./issue-tracker-github.md): GitHub issue tracker
- [issue-tracker-gitlab.md](./issue-tracker-gitlab.md): GitLab issue tracker
- [issue-tracker-local.md](./issue-tracker-local.md): local-markdown issue tracker
- [triage-labels.md](./triage-labels.md): label mapping (only if `triage` is installed)
- [domain.md](./domain.md): domain doc consumer rules + layout

Replace template defaults with confirmed locations in all draft files, including existing non-wiki ADR paths and indexes. If the GitHub or GitLab project differs from the remote, record the confirmed project explicitly and replace remote inference in its draft tracker guide.

For a new "other" issue tracker guide, use the user's description instead of a template.

### 4. Apply

Recheck the proposed files and dependencies. If they changed and invalidate the diff, stop and obtain approval for the revised diff. Write only approved changes and skip identical files. [Apply approved glossary edits](./shared-glossary-setup.md#apply) separately. With Excel opt-in, use the shared procedure's Apply and Check step for its portion.

If triage is configured on GitHub or GitLab, check the approved or existing mapping, including on reruns that skip the mapping question. In every label command target the verified configured project explicitly, not the inferred remote. Report any missing labels and the target project. Create them only with separate approval for that exact project and those labels. If the project cannot be verified, report it and skip the operation. Diff approval alone does not cover a tracker mutation.

### 5. Done

Tell the user what setup changed and which engineering skills will read those files. The user can edit `docs/agents/*.md` directly later. Checking for shared glossary updates requires another explicit setup run.

Before you say it's done, prove it — read back what you wrote and report the result, not the intention:

- The engineering links resolve to the claimed guides (list their actual locations).
- The instruction file has exactly one `## Agent skills` block, and one `## Wiki` block when wiki mode
  is on.
- In wiki mode: the configured ADR location is correct, and the decisions index is either new or untouched apart
  from the added links.
- `git diff --check` passes. For brand-new files git has nothing to check, so run
  `git diff --no-index --check -- NUL <file>` (or `/dev/null` on unix) on each one.
- Show the actual diff, including new files. Report any Excel changes or blockers from the shared procedure's check. Distinguish those repo edits from what setup does not do: commit, publish Issues, touch workbooks or migrate wiki content.

Configuring a repo is not a milestone. If the repo records milestones, say plainly that this run
 consumed none.
