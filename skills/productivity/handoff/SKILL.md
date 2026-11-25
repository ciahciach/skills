---
name: handoff
description: Compact the conversation for a fresh Kilo VS Code session or a portable handoff document.
argument-hint: "[--portable] What will the next session be used for?"
disable-model-invocation: true
---

Choose the route before writing anything:

1. If the user passes `--portable`, requests a document only, or needs the context in another checkout or tool, use the portable route below. Outside Kilo VS Code, also use the portable route.
2. Otherwise in Kilo VS Code, for continuation of the same assignment in the same checkout, call the Skill tool with `kilo-handoff` and carry over the user's focus. Follow that skill's authorization and write-transfer checks. Send the condensed context to the successor without writing a portable file. If the Kilo route applies but the skill or Agent Manager is unavailable, report the blocker instead of silently falling back. If neither route is clear, confirm the destination before acting.

## Portable route

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save it to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows), not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments other than `--portable`, treat them as a description of what the next session will focus on and tailor the doc accordingly.
