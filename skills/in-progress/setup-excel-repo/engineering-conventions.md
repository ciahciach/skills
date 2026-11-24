# Engineering Conventions

Use the same discovery files as Matt's engineering skills. Reuse the contents of existing files; add only missing guidance or root pointers. If existing conventions are split between files, point to their authoritative homes instead of copying them. If settings disagree, surface the conflict before writing.

## Root Instructions

Keep `AGENTS.md` (or the harness's active file) short. Under `## Agent skills`, link the actual authoritative files for tracker operations, triage roles, and terminology and ADRs. Reuse an existing section. For missing guidance, the defaults are `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, and `docs/agents/domain.md`. If a consumer requires a default path but the guidance already lives elsewhere, add only a pointer at that path, not a copy. Add a separate Excel pointer for onboarding, export, formula review, editing and controlled import. The Excel contract belongs in `docs/agents/excel.md` or the existing runbook; the glossary defines terms, not procedures.

## Tracker Seed

If `docs/agents/issue-tracker.md` exists, keep its tracker and link it. For a fresh repo with no tracker or repo remote, propose **Local Markdown**. Where a remote or existing convention points elsewhere, confirm the actual tracker and document its operations instead of creating a second one. Do not create remote projects, labels or tickets.

For Local Markdown, write these rules in `docs/agents/issue-tracker.md`:

- Specs: `.scratch/<feature>/spec.md`. Implementation tickets: one file per ticket, `.scratch/<feature>/issues/NN-<slug>.md`, starting at `01`. Fetch tickets by their paths (resolve numbers within the relevant feature). Use a `Status:` line with the mapped triage role and append comments under `## Comments`.
- Wayfinding: `.scratch/<effort>/map.md` and `.scratch/<effort>/issues/NN-<slug>.md`. A child has `Type:` (`research`, `prototype`, `grilling`, `task`) and `Status:`. Record blockers as `Blocked by: NN, NN`; the frontier is the open, unclaimed children with all blockers resolved, in number order. Claim with `Status: claimed` before work. Resolve via `## Answer`, `Status: resolved`, and a named link with a gist in the map's Decisions so far.

For a new `docs/agents/triage-labels.md`, document the five roles and their mappings. For the default local tracker they map to themselves: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Reuse established mappings when the tracker already has them.

## Domain Seed

For a new single-context repo without an existing wiki, write `docs/agents/domain.md` with these rules:

- Read root `GLOSSARY.md` for vocabulary and relevant ADRs from `docs/adr/` before work in that domain. If a `GLOSSARY-MAP.md` exists, follow it to the relevant glossary instead. Use established terms and flag a proposed change that contradicts an ADR.
- Create `GLOSSARY.md` when the first domain term is agreed. Create `docs/adr/NNNN-<slug>.md` when a real decision warrants an ADR; start at `0001` or use the next number. Create the directory then, not at setup. Use `docs/agents/grill/` for interview ledgers when needed.
- Tracker artifacts and domain knowledge have distinct homes. Link a decision or ticket rather than keeping a second copy. Do not create an empty glossary, an example ADR, an empty tracker directory or an unused wiki.

When a wiki or multi-context layout is already in use, document its actual paths and keep its ADR index, naming and governance. Do not migrate it to these defaults. When recording existing wiki mode in a new domain doc, use `## Wiki mode` and link the existing ledger and decisions locations.
