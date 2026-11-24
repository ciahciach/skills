# Windows Kilo rollout (#59)

Status: repository and decision-only acceptance complete; profile rollout and fresh-session discovery deferred until the user's batched `npx` update. No Excel backend, workbook, Office policy, or MCP configuration was exercised or changed by this work.

## Evidence

- [BEFORE #72](https://github.com/ciahciach/versuni-search-ecosystem/issues/72#issuecomment-7110136886) was recorded and its collection conditions subsequently confirmed before work on the profile. [#76](https://github.com/ciahciach/versuni-search-ecosystem/issues/76) owns the shared rules; coordinate the two Excel-only rule hunks there. Do not reintroduce a separate MCP-first rule.
- With explicit profile authorization, the eight touched files were copied byte-for-byte to `%LOCALAPPDATA%\Kilo-excel-router-59-v1-before` and compared by SHA-256. A temporary router copy was read back against its repo source. On the user's instruction to defer rollout, all eight files were restored and checked against the checkpoint hashes; the two temporary skill files were removed. The patch is not active. No completed fresh-session discovery result was used.
- The read-only Kilo acceptance test used the absolute path to [SKILL.md](SKILL.md), not the skill resolver (`ses_df13509bdffeUA1MlslDv5Mjhs`, marker `EXCEL-59-PATH END`). G01: current export used without a recipe. G02: scoped, hypothetically evidenced new XLSX write selected `xlsx`; XLSX with PQ/model and XLAM parser writes blocked. G03: no passive access, blocked. G04: Negokaz-only access for a Sbroenne request, blocked. Routine runtime and save without qualification, blocked. #40: candidate selection only, `NOT_VERIFIED`, runner `NOT_RUN`. None is a runtime PASS or proof of automatic discovery.

## Migrate after the batch update

1. Install/update the skill from the approved repository revision via the user's normal `npx` batch. The single entry is `excel-router`, version from `SKILL.md` metadata. Do not install/update any backend as part of this step.
2. Coordinate the Excel-only rule changes with #76. Before editing, capture raw SHA-256 and backup copies of every target in [`profile.patch`](profile.patch), plus the installed router files. The patch is relative to the user profile, not to this repo. From the repo, check applicability with `$p = (Resolve-Path 'skills/in-progress/excel-router/profile.patch').Path; git -C "$HOME" apply --check --ignore-space-change $p`. If bytes/context differ after the update, inspect and reconcile the individual hunks; do not force a partial apply. Only after authorization, apply with the same command without `--check` or integrate equivalent hunks in #76.
3. Read back the effective paths, hash the results, and compare the trigger/rule diff. In a fresh local Kilo VS Code session, ask an ordinary Excel question about an adequate current export without naming a skill. Verify the session discovers `excel-router`, actually loads it, reports its version, loads no competing broad Excel recipe and does not start Excel. Verify the conditional recipes remain discoverable when selected. Record extension version, session, effective paths and trace, not just the answer. If validation fails, restore backed-up targets only if their hashes still match this rollout's output; otherwise reconcile concurrent edits. Remove a newly installed router only if it did not exist before and no one else changed it.

## Control migration

| Previous location | Preserved or corrected destination |
| --- | --- |
| Global MCP-first rule and tool-first generic trigger | One `excel-router` pointer. Path validation, Python UTF-8, finance preflight, unrelated rules, and retry budget remain. |
| Global COM, VBA, locks and readback rules | Owned instance, scoped settings, locks, bounded wait, no foreground, protected ranges and independent reopen in [runtime.md](runtime.md) and COM recipe. Replace mandatory unmerge with structure preservation. |
| `passive-excel-audit`, `xlsx` | Bounded saved-state inspection without project paths; library writes only for simple documents. Preserve formula/cache caveats and modern functions; LibreOffice is optional on an authorized disposable copy, not an Excel proof. |
| `excel-mcp`, `excel-cli` | Sbroenne identity and exact schemas/session syntax; scoped refresh, visibility, AutoSave/shutdown, independent reopen and no automatic installation or fallback. Shared runtime controls override unscoped examples. |
| `vba-compile-cycle` | Preserve export, target checks, bounded readiness and behavior assertion; distinguish compilation from run, keep FRM/FRX together, do not rewrite dependencies or claim module restore undoes all effects. |

## Handoff to #40

Before rollout use this prompt from the target checkout: `Read the absolute path to this checkout's skills/in-progress/excel-router/SKILL.md directly. Decide only: use explicit direct COM (pywin32 DispatchEx) as candidate for the separately authorized synthetic simple XLSX formula-save qualification in ciahciach/skills#40. Confirm candidate identity/version from available non-runtime metadata. Do not run the qualification.` After rollout use the same request with `skill(name: "excel-router")` in place of direct file read.

Read the line beginning `Excel route | router=excel-router@1.0.0`. Expect class `save`, profile `simple`, mode `qualification`, selected recipe `excel-com-safe`, observed backend version (or an explicit blocker if missing), scoped authorization and `qualification=NOT_VERIFIED` for the selection. Report `NOT_RUN` separately. Installed `pywin32` metadata reported 312 here, without opening Excel. This is neither a measured Excel build nor evidence of a compliant `Open`, save, reopen or re-export. The actual runner and evidence ownership stay with [#40](https://github.com/ciahciach/skills/issues/40).
