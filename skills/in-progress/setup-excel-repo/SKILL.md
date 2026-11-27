---
name: setup-excel-repo
description: Configure a new or existing repository for versioning Excel workbook logic and structure.
disable-model-invocation: true
---

# Setup Excel Repo

Run only when the user explicitly invokes `/setup-excel-repo`. Configure the current Git repository without running Excel. Setup is independent of Matt's setup and does not require a workbook. After setup, agents start from the repo instructions, not this command.

Resolve the loaded skill directory to its source checkout, following any symlink or Windows junction. From there, read the [shared Excel procedure](../../engineering/setup-matt-pocock-skills/excel-setup.md). If the reference is missing, report the incomplete source bundle and stop rather than inventing a contract. The procedure plans Excel changes without invoking another skill. Use the active instruction file and existing knowledge layout found there.

1. **Plan:** Follow Discover, then identify the tracker and draft only the missing minimum using [engineering conventions](engineering-conventions.md), not Matt's setup interview or template. Then follow the shared Excel Plan using that tracker. Combine edits to a shared instruction file before showing the diff.
2. **Confirm:** Show one proposal with the exact Excel and minimum engineering diff, marking the glossary diff for separate explicit approval. Report the shared procedure's findings and unresolved dependencies. If there is no change, write nothing. A revised diff needs fresh approval. Standalone invocation is not consent to write, publish Issues or operate on a workbook.
3. **Apply and check:** Follow the shared procedure's Apply and Check step for the approved diff, and the glossary procedure for separately approved glossary edits. Read back the engineering links and next ADR location, and show the actual diff including new files. Do not install anything, mutate the tracker or publish Git changes.
