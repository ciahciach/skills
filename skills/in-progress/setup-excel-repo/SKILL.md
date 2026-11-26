---
name: setup-excel-repo
description: Configure a new or existing repository for versioning Excel workbook logic and structure.
disable-model-invocation: true
---

# Setup Excel Repo

Run only when the user explicitly invokes `/setup-excel-repo`. Configure the current Git repository without running Excel. Setup is independent of Matt's setup and does not require a workbook. After setup, agents start from the repo instructions, not this command.

## 1. Discover

Identify the repository root and inspect the active `AGENTS.md` / `CLAUDE.md` (including any pointer between them). Follow existing workbook pointers, manifests, text sources, inventories, tooling, retention and knowledge conventions. Inspect `docs/agents/`, any existing wiki, glossary, ADRs and issue-tracker conventions before proposing writes. Check for user changes and local instructions.

Report two independent findings:

- **Scaffold:** adopt if the repo already organizes Excel work, even partially and without a workbook. Identify what each existing path covers and what is missing. Use the new-scaffold path only if no Excel scaffold exists. An unrelated `src/`, generic Excel safety rules without repo-specific organization, or a workbook alone is not a scaffold. Conflicting authoritative paths or instructions require a human decision, not a second scaffold.
- **Workbook:** none, or explicitly identified candidates. A workbook is not permission to open, move, register, or import it. If the user wants onboarding, treat it as a separate operation after setup; identify one workbook and its profile, retention and initial synchronization plan before proceeding.

## 2. Propose

Read [the repo contract seed](repo-contract.md). In the adopt path, map its requirements to what is already present and propose only missing rules or links. Keep existing filenames, workbook IDs, source and inventory locations, and stronger local safety rules. In the new path, propose one instruction pointer and one local contract (default `docs/agents/excel.md`, or the existing knowledge layout). Record where future editable exports and inventory will live, but don't create empty directories, placeholder workbook records or stub exports.

Complete the repo's engineering configuration in the same proposal. Read [engineering conventions](engineering-conventions.md) to seed missing tracker, triage mapping and domain guidance without invoking Matt's setup. Preserve any choices already made, including wiki mode and nonlocal trackers. This step applies whether the Excel scaffold is new or adopted.

Identify the shared Excel router from the environment or existing repo rules. Record its actual entry point if available. If unavailable, mark it pending and block workbook operations that require it. Do not invent a router name or substitute an Excel backend. Text-only review of an already current export remains possible.

For both scaffold paths, read the [canonical Excel section](excel-standard.md) bundled beside this skill and inspect the target repo's root `CODING_STANDARDS.md`. Use the source heading to identify the shared section, through the next heading at the same or higher level or the end of the document. Keep separate local Excel rules and all other content untouched. If the shared section is duplicated or its identity or boundary is ambiguous, report the conflict and ask the user to identify the shared block before proposing an edit. This includes a recognizable Excel standard version line without the source heading (possible local rename) or nested local rules whose boundary is unclear. Do not treat these cases as missing.

- **Missing:** propose creating the file or appending the section to the existing document. Copy the complete source section, including its heading and version, without paraphrasing.
- **Matching:** if version and content match (ignoring line-ending style and surrounding blank lines), propose no standards edit.
- **Older version:** propose replacing only the shared section with the complete bundled one. Show all removals and replacements. Identify any local deviations you can verify; if you cannot verify the old baseline, say that the removed text may include local edits.
- **Same version, different content:** report local divergence and identify the differences in the proposed diff. Require explicit approval of the replacement, including its removal of local changes. Let the user keep the existing section or agree on a revised diff that preserves those rules separately.
- **Newer or unclear version:** report the mismatch and leave the section unchanged pending clarification.

The author and the Standards axis of `code-review` use the copy in the revision under review, not the skill's copy or a remote source. No additional standards file or `AGENTS.md` pointer is needed.

Show the exact proposed edits and any unresolved dependencies. Use the root instruction file the target harness actually reads, following any existing pointer to the canonical file. If neither instruction file exists, propose `AGENTS.md` (or the harness's native file) for approval. Add a short pointer that covers workbook onboarding, export, text review and controlled import; reuse an existing pointer when possible. The contract or pointer may be omitted from the diff if its current form already meets the criteria.

If there is no required change, report a no-op and write nothing. Otherwise wait for approval of the shown diff. Setup approval covers only those repo changes, not workbook onboarding or later runtime.

## 3. Apply and Check

Recheck proposed targets before applying only the approved edits. Preserve unrelated text, encodings, existing files and user changes. Stop on a conflicting concurrent edit. Don't reinitialize the repo or replace a scaffold wholesale.

Read back the root pointers and their targets (Excel, tracker, triage and domain), verify the documented path for the next ADR, and show the actual diff, including newly created files. Report the scaffold path, the separate workbook status and any unavailable capabilities. On an unchanged rerun, produce no diff. No installation, workbook runtime, remote tracker mutation, ticket creation or Git publication are part of setup.

If the approved diff changed `CODING_STANDARDS.md`, read it back: verify the copied section against the bundled source and confirm unrelated content is unchanged.
