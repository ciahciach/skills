---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Spin up a **background agent** to do the research, so you keep working while it reads. Start it with a fresh context window.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

## Wiki mode

When the repo keeps an LLM wiki (`wiki/index.md` exists), the note lands in the wiki instead of a
loose `docs/` file: `wiki/queries/<slug>.md` for an answer to a question, `wiki/concepts/<slug>.md`
for knowledge about the domain itself. Give it the merged frontmatter from `wiki-layout.md`, link at
least two existing pages, and add it to `wiki/index.md` plus a `log.md` entry. A note filed nowhere
the wiki can reach is a note the next session will not find.
