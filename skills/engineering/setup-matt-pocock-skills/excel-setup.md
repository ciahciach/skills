# Shared Excel Setup Procedure

This is a reference, not a skill. Read it only for a user-selected Excel scope, either within Matt's setup or in standalone Excel setup. Plan Excel edits without writing anything; the caller owns the combined proposal and exact diff approval. Use the seeds bundled beside this file, not target-repo copies or downloads. If a seed is unavailable, report the missing source and leave the dependent edit out.

## Discover

Identify the repo root and inspect the instructions the harness actually reads, following pointers to their canonical file. Check for user changes and local instructions. Follow existing workbook pointers, manifests, text sources, inventories, tooling and retention rules. Reuse existing knowledge locations and the caller's engineering choices. Report three independent findings with evidence:

- **Scaffold:** trace the active instruction and link chain to [the repo contract seed](./repo-contract.md)'s applicable rules, and compare representative saved text sources, inventories and metadata with the documented requirements of intended operations. Cite observed differences and affected operations, not a scaffold version. Use the new-scaffold path only when no Excel scaffold exists. An unrelated `src/`, generic Excel safety rules or a workbook alone is not a scaffold.
- **Onboarding:** distinguish no workbook identified, candidate not onboarded, and registered workbook with evidence of an approved sync point. No workbook or export not yet due is not a scaffold defect. Setup does not open, move, create, register or import a workbook.
- **Runtime readiness:** identify the shared Excel router from the environment or repo rules, if available. Report whether evidence matches the operation, workbook profile and actual interface/version, or mark readiness not assessed if no operation/profile is in scope. Report missing authorization separately from qualification. Missing evidence, router or authorization blocks the dependent operation, not setup or passive review of a current export. Do not launch Excel or substitute another route.

## Plan

For adoption, add missing links and rules and replace only unambiguously outdated rules in their authoritative file. Keep existing filenames, IDs, source and inventory paths and compatible stronger safety rules. For a new scaffold, use the contract seed to draft one local contract (default `docs/agents/excel.md`, or the existing knowledge layout) and one short pointer covering onboarding, export, text review and controlled import. Add the pointer to the same active instruction file as the engineering pointers, reusing any existing Excel pointer. If no instruction file exists and the caller has not already chosen one, propose `AGENTS.md` or the harness's native file. Record future export and inventory locations without creating empty directories, placeholder workbook records or stub exports.

Separate configuration fixes from authority conflicts and artifact migrations:

- If active authoritative sources contradict each other about a rule, responsibility or path, leave them intact and block only dependent operations. If a format serves text review but fails the documented import contract, leave the artifact intact, block only the dependent import and keep text review available if the export is current.
- Report the competing rules, paths or formats and the blocked operation. Check the conversation and configured tracker for a matching proposal or Issue before drafting; reference a match. On a known rerun without earlier context, report the blocker without redrafting. In a fresh session where prior handling cannot be established, confirm a new draft is needed before producing one. For a new blocker, draft an Issue in the response with testable acceptance criteria. Keep independent safe edits in the diff. Do not create a local ledger, migrate artifacts or publish Issues. Publication requires separate approval.

For both paths, compare the [canonical Excel section](./excel-standard.md) with the target root `CODING_STANDARDS.md`. Identify the shared section by its heading, through the next heading at the same or higher level or end of document. Preserve separate local rules and other content. If the section is duplicated or its identity or boundary is ambiguous (including a version line under a renamed heading or ambiguous nested rules), surface the conflict and ask the owner to identify the shared block before proposing an edit.

- **Missing:** create the file or append the complete source section with its heading and version, verbatim.
- **Matching:** no edit if version and content match, ignoring line endings and surrounding blank lines.
- **Older:** propose replacing only that section with the bundled one. Show removals and replacements and identify verified local deviations. If the old baseline is unavailable, flag that removed text may include local edits.
- **Same version, different content:** report local divergence in the diff. Let the user keep it or explicitly approve replacement, including removals, or a revised diff preserving local rules separately.
- **Newer or unclear version:** report the mismatch and leave it unchanged pending clarification.

No extra standards file or instruction pointer is needed. Authors and the Standards axis of `code-review` use the copy in the revision under review, not the bundle or remote source.

## Apply and Check

Before writing approved edits, recheck targets and the instructions, links and evidence the proposal depends on. If they invalidate it, stop and return any revised diff for approval. Preserve unrelated text, encodings and user changes. Skip identical files; do not reinitialize the repo or replace the scaffold wholesale.

After writing, read back the active instruction chain and verify its Excel target and changed contract against the approved diff. Verify any copied standards section against the bundled source and confirm unrelated text is unchanged. Report scaffold, onboarding and runtime readiness separately, including unresolved blockers on a no-op. Report no diff on an unchanged rerun.
