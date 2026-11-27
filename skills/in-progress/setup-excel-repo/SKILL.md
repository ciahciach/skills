---
name: setup-excel-repo
description: Configure a new or existing repository for versioning Excel workbook logic and structure.
disable-model-invocation: true
---

# Setup Excel Repo

Run only when the user explicitly invokes `/setup-excel-repo`. Configure the current Git repository without running Excel. Setup is independent of Matt's setup and does not require a workbook. After setup, agents start from the repo instructions, not this command.

## 1. Discover

Identify the repository root and inspect the active `AGENTS.md` / `CLAUDE.md` (including any pointer between them). Follow existing workbook pointers, manifests, text sources, inventories, tooling, retention and knowledge conventions. Inspect `docs/agents/`, any existing wiki, glossary, ADRs and issue-tracker conventions before proposing writes. Check for user changes and local instructions.

Report three independent findings and cite their evidence:

- **Scaffold:** adopt if the repo already organizes Excel work. Trace the active instruction and link chain to [the repo contract seed](repo-contract.md)'s applicable rules, and compare representative saved text sources, inventories and metadata with the documented requirements of their intended operations. Report what is current, what needs a rule or link update, and what operation is blocked, citing paths and observed differences rather than a scaffold version. Use the new-scaffold path only if no Excel scaffold exists. An unrelated `src/`, generic Excel safety rules without repo-specific organization, or a workbook alone is not a scaffold.
- **Onboarding:** distinguish no workbook identified, candidate not onboarded, and a registered workbook with evidence of an approved sync point. A workbook is not permission to open, move, register, or import it. Treat onboarding as a separate operation. No workbook or export not yet due is not a scaffold defect.
- **Runtime readiness:** identify the shared Excel router from the environment or existing repo rules and report the actual entry point, if available. Report whether existing evidence matches the requested operation, workbook profile and actual interface/version, or mark readiness not assessed if no operation/profile is in scope. Report missing or disputed authorization separately from qualification; setup never authorizes workbook work. Missing evidence, router or authorization blocks the dependent runtime operation, not setup or passive review of a current text export. Do not launch Excel or substitute another route.

## 2. Propose

In the adopt path, use the discovery findings to add missing rules or links and replace only unambiguously outdated rules in the authoritative file, rather than leaving contradictory instructions side by side. Keep existing filenames, workbook IDs, source and inventory locations, and compatible stronger local safety rules. In the new path, use [the repo contract seed](repo-contract.md) to propose one instruction pointer and one local contract (default `docs/agents/excel.md`, or the existing knowledge layout). Record where future editable exports and inventory will live, but don't create empty directories, placeholder workbook records or stub exports.

Complete the repo's engineering configuration in the same proposal. Read [engineering conventions](engineering-conventions.md) to seed missing tracker, triage mapping and domain guidance without invoking Matt's setup. Preserve any choices already made, including wiki mode and nonlocal trackers. This step applies whether the Excel scaffold is new or adopted.

Separate configuration fixes from authority conflicts and artifact migrations:

- If active authoritative sources contradict each other about a rule, responsibility or path, leave both intact. Block only dependent operations until the owner resolves the conflict. Do not replace either source as merely outdated.
- If a format serves text review but fails the documented import contract, leave the artifact intact and block only the dependent import. Keep text review available if the export is current.

Report each conflict or migration with the competing instructions, paths or formats and the blocked operation. Before drafting an Issue, check the conversation and configured tracker for a matching proposal or Issue; reference a match instead of drafting again. On a known rerun without the earlier context, report the blocker without redrafting. In a fresh session where prior handling cannot be established, report the blocker and confirm it needs a new draft before producing one. For a new blocker, draft the Issue in the response with testable acceptance criteria. Keep independent safe edits in the diff. Setup neither creates a local ledger nor migrates artifacts or publishes Issues. Publication needs separate approval.

For both scaffold paths, read the [canonical Excel section](excel-standard.md) bundled beside this skill and inspect the target repo's root `CODING_STANDARDS.md`. Use the source heading to identify the shared section, through the next heading at the same or higher level or the end of the document. Keep separate local Excel rules and all other content untouched. If the shared section is duplicated or its identity or boundary is ambiguous, report the conflict and ask the user to identify the shared block before proposing an edit. This includes a recognizable Excel standard version line without the source heading (possible local rename) or nested local rules whose boundary is unclear. Do not treat these cases as missing.

- **Missing:** propose creating the file or appending the section to the existing document. Copy the complete source section, including its heading and version, without paraphrasing.
- **Matching:** if version and content match (ignoring line-ending style and surrounding blank lines), propose no standards edit.
- **Older version:** propose replacing only the shared section with the complete bundled one. Show all removals and replacements. Identify any local deviations you can verify; if you cannot verify the old baseline, say that the removed text may include local edits.
- **Same version, different content:** report local divergence and identify the differences in the proposed diff. Require explicit approval of the replacement, including its removal of local changes. Let the user keep the existing section or agree on a revised diff that preserves those rules separately.
- **Newer or unclear version:** report the mismatch and leave the section unchanged pending clarification.

The author and the Standards axis of `code-review` use the copy in the revision under review, not the skill's copy or a remote source. No additional standards file or `AGENTS.md` pointer is needed.

Show the exact proposed edits and any unresolved dependencies. Use the root instruction file the target harness actually reads, following any existing pointer to the canonical file. If neither instruction file exists, propose `AGENTS.md` (or the harness's native file) for approval. Add a short pointer that covers workbook onboarding, export, text review and controlled import; reuse an existing pointer when possible. The contract or pointer may be omitted from the diff if its current form already meets the criteria.

If there is no required change, report a no-op and write nothing, even if a blocker remains. Otherwise wait for approval of the exact diff. Declining or changing the proposal leaves files untouched until the exact revised diff is approved. Setup approval covers only those repo changes, not Issue publication, workbook onboarding or later runtime.

## 3. Apply and Check

Recheck proposed targets and the active instructions, links and other evidence each edit depends on. If a change invalidates the proposal or exposes a conflict, stop before writing and return any revised diff for approval. Apply only approved edits. Preserve unrelated text, encodings, existing files and user changes. Don't reinitialize the repo or replace a scaffold wholesale.

Read back the active instruction chain and its targets (Excel, tracker, triage and domain), verify the documented path for the next ADR and the changed contract against the approved diff, and show the actual diff, including newly created files. Report scaffold, onboarding and runtime readiness separately, retaining any unresolved blockers. On an unchanged rerun, produce no diff. No installation, workbook runtime, tracker mutation, Issue creation or Git publication is part of setup.

If the approved diff changed `CODING_STANDARDS.md`, read it back: verify the copied section against the bundled source and confirm unrelated content is unchanged.
