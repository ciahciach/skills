# Wiki mode: running the engineering skills against an LLM wiki

Some repos keep their knowledge in an LLM wiki (Markdown pages + `index.md` + `log.md`, Karpathy
style) instead of loose docs. The skills' default paths (`docs/adr/`, `docs/agents/grill/`,
`.scratch/`) then compete with the wiki for the same content.

**Rule that makes it work: one artifact, one home.** A decision lives in exactly one file; other
places link to it instead of restating it. Pick the layout below when the repo has a wiki, and write
the choice into `docs/agents/domain.md` so every later skill reads it from there.

## Layout

| Artifact | Written by | Default | **Wiki mode** |
|---|---|---|---|
| Decisions ledger from an interview | `grilling` | `docs/agents/grill/<slug>.md` / `.scratch/grill/<slug>.md` | `wiki/processes/grill/<slug>.md` |
| ADR (hard to reverse, surprising, real trade-off) | `domain-modeling` | `docs/adr/NNNN-<slug>.md` | `wiki/decisions/NNNN-<slug>.md` |
| Glossary of canonical terms | `domain-modeling` | `GLOSSARY.md` at root | **unchanged** — `GLOSSARY.md` at root |
| Multi-context glossary map | `domain-modeling` | `GLOSSARY-MAP.md` at root | **unchanged** |
| Spec / PRD | `to-spec` | tracker issue | tracker issue; the wiki page links to it, never copies it |
| Tickets | `to-tickets` | tracker | tracker |
| Issue tracker config | setup skill | `docs/agents/issue-tracker.md` | **unchanged** — config, not knowledge |
| Triage labels | setup skill | `docs/agents/triage-labels.md` | **unchanged** |
| Wiki schema / catalog / log | wiki skill | `wiki/SCHEMA.md`, `wiki/index.md`, `wiki/log.md` | same, created by the wiki |
| Milestones, plans, status | project convention | — | `wiki/processes/milestones.md` |
| Governance rules | project convention | — | `wiki/processes/governance.md` |

Why the glossary stays at the repo root: it is a *lookup table* an agent greps in one call
(`read_file GLOSSARY.md`), not a page in a graph. Burying it in `wiki/concepts/` costs an index read
before every use and gains nothing. Link it from `wiki/index.md` so humans still find it.

Why the ledger moves into `wiki/processes/`: an interview ledger is a process record, it is dated,
and it is superseded by later decisions — exactly what a wiki page with frontmatter is for. It also
puts it next to `milestones.md`, where the plan it feeds already lives.

## Merged frontmatter (one block, both conventions)

```yaml
---
title: <page title>
type: entity | concept | comparison | decision | process | grill | query
status: ACTIVE | UNCERTAIN | DEPRECATION_CANDIDATE | APPROVED_FOR_REMOVAL
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
last_verified: YYYY-MM-DD
verified_against_snapshot: <snapshot id or authorization id>
related_objects: []
tags: [from the taxonomy in wiki/SCHEMA.md]
sources: [raw/articles/<file>.md]
confidence: high | medium | low
contested: true            # only when it contradicts another page
contradictions: [<page-slug>]
---
```

- `last_updated` moves on every edit. `last_verified` moves **only** after re-checking the page
  against `verified_against_snapshot`. Document mtime and commit date are not verification: a page
  edited for a typo is not a page that was re-checked.
- Staleness lint reads `last_verified`, never `updated` or git log.
- `status` and `type` are independent: a `DEPRECATION_CANDIDATE` decision is still a decision.

## Provenance vocabulary: one scheme, not two

Keep the project's fact markers as the canonical words, and derive the wiki's `confidence` from
them. Do not invent a third vocabulary.

| Fact marker (canonical) | Meaning | `confidence` |
|---|---|---|
| `USER_CONFIRMED` | the user stated it, with a date/authorization id | `high` |
| `OBSERVED` | read from the artifact or run, reproducible | `high` |
| `INFERRED` | follows from evidence, not stated | `medium` |
| `PROPOSED` | an option under discussion | `low` (+ `contested` if it conflicts) |

Coverage markers belong to extraction work, not to wiki pages:
`EXTRACTED` / `PARTIAL` / `NOT_ACCESSIBLE`, `STALE`, `UNKNOWN`. A page whose only support is
`NOT_ACCESSIBLE` is `confidence: low` and says so in the body.

## Bootstrapping a repo (idempotent, one pass)

Run after `setup-matt-pocock-skills` has written `docs/agents/`:

```bash
# 1. wiki skeleton — skip every file that already exists
mkdir -p wiki/{processes,decisions,concepts}
[ -f wiki/SCHEMA.md ] || cp <llm-wiki skill>/SCHEMA-template wiki/SCHEMA.md
[ -f wiki/index.md ]  || printf '# Index\n\n## Processes\n\n## Decisions\n\n## Concepts\n' > wiki/index.md
[ -f wiki/log.md ]    || printf '# Log\n\n## [%s] create | wiki initialized\n' "$(date +%F)" > wiki/log.md

# 2. tell the skills where things live
cat >> docs/agents/domain.md <<'EOF'

## Wiki mode
- Decisions ledger: wiki/processes/grill/<slug>.md
- ADRs: wiki/decisions/NNNN-<slug>.md
- Glossary: GLOSSARY.md at the repo root (link it from wiki/index.md)
- Every maintained page carries status, last_updated, last_verified,
  verified_against_snapshot, related_objects; facts are marked
  USER_CONFIRMED / OBSERVED / INFERRED / PROPOSED.
- Provenance vocabulary and frontmatter: see wiki/SCHEMA.md.
EOF
```

Nothing here overwrites an existing file: the repo may already have a schema and pages, and a
bootstrapper that rewrites them destroys exactly the knowledge it was meant to protect.

## The `## Wiki` block for a project's AGENTS.md

Portable across projects — paste it once, keep it short. It states the rules the skills must not
re-derive each session:

```markdown
## Wiki (LLM wiki)
- Knowledge lives in `wiki/` as interlinked Markdown. `wiki/index.md` is the catalog; read it first.
- Every page: frontmatter with status, last_updated, last_verified, verified_against_snapshot,
  related_objects, tags, sources. Links via [[wikilinks]]; 2+ outbound per page.
- One artifact, one home: decisions in wiki/decisions/, interview ledgers in wiki/processes/grill/,
  glossary in GLOSSARY.md at the root. Nothing is restated in two places.
- Facts are marked USER_CONFIRMED / OBSERVED / INFERRED / PROPOSED. Never present INFERRED as fact.
- last_verified changes only after a real re-check against verified_against_snapshot.
- Write in the language of this file. Do not translate the project's terms.
```

## Working with a repo whose AGENTS.md is curated

Some `AGENTS.md` files are governance documents: frontmatter with `status`/`last_updated`, sections
marked `USER_CONFIRMED`, explicit authorization scope. Treat them as user-owned text.

- **Append, never rewrite.** Add the `## Agent skills` and `## Wiki` blocks at the end; do not
  reorder, re-word, or "tidy" existing sections.
- **If a section carries `USER_CONFIRMED` and a date, it outranks the skill's default.** A skill
  default that contradicts it loses, and the conflict goes into the report rather than into an edit.
- **Respect the file's language.** A Polish `AGENTS.md` means Polish ledger, Polish ADRs, Polish
  wiki pages — including headings. The skills' own instructions stay English; their output does not.
- **Tell the user what you added**, by section name, in the closing message.

## Interop with the `llm-wiki` skill

`llm-wiki` owns the mechanics: schema, ingest, query, lint, log rotation, `raw/` immutability.
The engineering skills own *when* a page is written:

| Event | Skill | Wiki action |
|---|---|---|
| a decision settles in an interview | `grilling` | append to the ledger page, bump `last_updated` |
| a term is resolved | `domain-modeling` | `GLOSSARY.md`; add a concept page only if it meets the page threshold |
| a trade-off is hard to reverse | `domain-modeling` | new `wiki/decisions/NNNN-*.md` + `index.md` + `log.md` |
| a milestone closes | `retro` / project convention | changelog page: changes, decisions with reasons, open items |

Lint after a batch of these, not during: run `llm-wiki`'s lint once at the end, so `index.md` and
`log.md` reflect the finished batch instead of every intermediate write.

## Decisions register: keep the shape the repo has

New decisions are files under `wiki/decisions/NNNN-<slug>.md`. A repo that already keeps a single
register (`wiki/decisions.md`) keeps it — it becomes the index, not a casualty of tidying:

- Do not rename or move it. Links point at it from the repo and from outside it.
- Do not split its history in the setup run. Split one decision when that decision is next touched.
- The index carries the table of ADRs; the ADRs carry the reasoning.
- `docs/adr/` is never created in wiki mode.

An index entry without an ADR file behind it is a bug: the decision exists only as a line someone
will later misquote.

## Minimum bootstrap, and nothing more

When wiki mode is turned on for a repo that has no wiki, create exactly:

| File | Why |
|---|---|
| `wiki/index.md` | the one entry point every skill reads first |
| `wiki/decisions/` | where ADRs land; empty until the first real decision |
| `wiki/processes/grill/` | where interview ledgers land |
| `wiki/processes/governance.md` | the rules for editing pages: status, `last_verified`, provenance |

Do not invent component pages, glossaries or backlogs. A wiki that starts as a graveyard of empty
templates is abandoned in a month; one that starts with an index and three folders grows.

## Two queues, two scopes

`.scratch/` holds work items these skills drive — specs, tickets, grill ledgers when there is no
wiki. `wiki/` holds knowledge — decisions, components, processes, milestones. The same ticket never
lives in both: the wiki links to the tracker, the tracker links to the wiki. When a repo already has
a backlog in the wiki, say out loud which queue it belongs to instead of migrating it.

## Editing an instruction file (AGENTS.md / CLAUDE.md)

Append at the end under a new heading, in the file's own language; never reorder existing sections,
never rewrite a `USER_CONFIRMED` line. Idempotent by heading: two runs leave one `## Agent skills`
and one `## Wiki`. The file is governance, not a scratchpad.
