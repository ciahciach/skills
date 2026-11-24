# Desktop Excel route qualification (#40)

**2026-11-24: `PASS` for the repo-path shared route and the one synthetic formula save in [#40](https://github.com/ciahciach/skills/issues/40).** Automatic skill discovery and profile rollout are deferred. This does not qualify a production writer, a different backend or an arbitrary workbook for [#27](https://github.com/ciahciach/skills/issues/27).

## Shared Entry and Backend

- Shared entry: directly read and apply [`skills/in-progress/excel-router/SKILL.md`](../../skills/in-progress/excel-router/SKILL.md) and its runtime reference, as documented in [#59](https://github.com/ciahciach/skills/issues/59). The router tree matches merged PR [#61](https://github.com/ciahciach/skills/pull/61), merge commit `2225a7918a8f35286f87e97b3975f6bad32ab770`. The user explicitly requested the repo-path mode without installing skills and authorized all #40 synthetic tests, including opening the isolated fixture and saving a separate copy. No production edits, label changes, final acceptance, or synchronization were authorized.
- Route decision before execution: `Excel route | router=excel-router@1.0.0 | class=save | profile=simple | mode=qualification | decision=selected | backend=pywin32 312 DispatchEx | recipe=excel-com-safe | authorization=#40 isolated synthetic open and save on a separate copy | qualification=NOT_VERIFIED | reason=explicitly selected direct COM candidate, no fallback`. Execution passed separately below; neither this receipt nor #59's instruction-only test is runtime evidence by itself.
- Backend command selected by that decision: `py -3.14 -B -X utf8 scripts/qualify-excel-com.py`, from this repository. Implementation: [synthetic-only runner](../../scripts/qualify-excel-com.py), Python 3.14.4. `openpyxl` 3.1.5 only generates the fixture and reads saved state, never performs the target edit.
- Live runtime: Excel `Version=16.0`, `Build=20527`; installed executable `16.0.20527.20194` x64. Fixture: one sheet `Calc`, `A1=10`, existing ordinary `B1 = A1*2`, neighboring `C1 = A1+1`, and a styled text sentinel. Intended mutation `B1 = A1*3` (numeric result `30`). The initial package inventory and input formulas contain no VBA, XLM, query, connection, model, or external-link parts.
- Preparation: Excel saved a disposable copy of the generated seed as the baseline before taking any qualification hashes. That save applied the host's existing policy and introduced `docProps/custom.xml`. The prepared profile permits that part but requires its byte-for-byte preservation in later saves. No label was manually set, removed, or reported. The seed and prepared baseline were not the targets of any subsequent saves.
- Live open evidence: newly owned PIDs `67136` (missing-file probe), `48272` (prepare), `37088` (no-op), `106980` (save), and `97684` (readback). All were hidden and logged `UpdateLinks=0` and `AutomationSecurity` `1 -> 3 -> 1`. Event guard `PASS` (`EnableEvents=False`); a live handler test was `NOT_RUN`. All successful opens checked `AutoSaveOn=false`, zero queries/connections, no Excel link sources and no legacy shared-workbook mode. XLM and query-refresh behavior on files containing those features was `NOT_RUN`; the exact fixture profile gate excluded those parts before opening. No network isolation is claimed.

| Stage | Direct COM result |
| --- | --- |
| Controlled open of an isolated XLSX copy | `PASS` within the synthetic profile; successful open and error-path restoration observed. |
| No-op save | `PASS` against the prepared baseline. The cell export and package parts matched after excluding the document modification timestamp. |
| No-write dry-run | `PASS`: identified `Calc!B1` and `=A1*2` to `=A1*3`; hashes of all existing scratch files stayed the same. |
| Targeted save and numeric result | `PASS` for the save itself: distinct copy, `=A1*3` and numeric `30`. |
| Independent read-only reopen and re-export | `PASS`: distinct PID, opened read-only, no save, candidate hash unchanged across reopen, and only `Calc!B1` differed in the cell export. Seed and baseline hashes also matched at end of run. |
| Candidate package preservation | `PASS` for this local synthetic profile: parsed sheet and core XML matched after excluding `B1` formula/cache and the modification timestamp, respectively. Chain order `C1,B1` to `B1,C1` and the revision pointer's document ID value were the only masked byte differences in those parts. Label bytes and all other package parts matched. |
| Acceptance and synchronization | `NOT_RUN`: outside scope. Only temporary synthetic files were used. |

The first run on an unprepared copy stopped at the no-op profile gate: Excel added `docProps/custom.xml` with an `MSIP_Label` property. The prepared fixture resolved that blocker without label removal, Office policy changes, or fallback. Sbroenne follow-up [#45](https://github.com/ciahciach/skills/issues/45) does not block COM work.

## XML Diagnosis

The diagnostic run reproduced both differences after a successful read-only reopen and re-export. Its final hash checks confirmed that the seed, baseline and saved candidate had not changed during verification. The structural diff found only these changed attributes in the two parts:

- `xl/calcChain.xml`, `r` on the first and second calculation cells. [Microsoft's SpreadsheetML documentation](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-the-calculation-chain) describes the chain as calculation order, not the dependency graph. [`l` marks the start of a calculation level](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.calculationcell?view=openxml-3.0.1#remarks). Both formulas depend only on `A1`; the run observed `C1(i=1,l=1), B1(i=1)` becoming `B1(i=1,l=1), C1(i=1)`. The single level boundary stayed in the first position. The comparator allows only the two exact addresses on the same sheet, with no flags except the optional first-position `l="1"`, and masks only the addresses. It still rejects a moved, added or removed level boundary, other changed flags, sheet or membership.
- `xl/workbook.xml`, `xr:revisionPtr/@documentId`. The [Open XML SDK schema](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.office2016.excel.revisionptr?view=openxml-3.0.1) identifies this as the Office revision pointer's document identifier, distinct from its revision number. The runner permits only a value change on the existing pointer, only for the edited local disposable copy. It still compares every other byte of `workbook.xml`, including all other pointer attributes. This is not evidence that rotating document identity is safe for a shared, published, or version-tracked workbook. The diagnostic does not print the identifiers.

Neither exception applies to the no-op check. Nothing in either file, the Office label, or the calculation settings is rewritten by the comparator. The changed-member, changed-flag, missing-identifier, changed-revision, and changed-label controls are covered by the offline tests in `scripts/test_excel_com_qualification.py`.

The successful routed run exited after `package_preservation: PASS`. SHA-256 evidence:

- Prepared base, unchanged: `70207a689e96532f32201bc3b07fb96c9ed859579410ae4cb68cce6db5ab582c`
- No-op copy: `4ed1b9546cbb3aa17ee1e17948833da5df56369064a4f41096bc540df468dbcf`
- Candidate before and after reopen: `191253f17d15583989fe8596e9665facb537c25a42e059e5f32b19e9e6a2daf9`
- Seed, unchanged: `33949ec4e467abe266e1ea9110a2cf58cb014ed3593cf61afdb2f43af9bb49e1`

The previous strict comparator rejected the real first-position level marker. The targeted regression failed before the position-aware change. A separate red/green regression verifies that masking cannot hide a changed XML comment instead of the validated chain nodes. All five comparator tests and both repository npm checks passed. Full Python discovery did not finish within its budget, stopping at the pre-existing onboarding test `test_acceptance_rejects_changed_artifacts_and_is_write_once`. One diagnostic desktop rerun timed out after readback and was not counted; the successful reruns used new scratch files, not a replay against that candidate.

## Historical Sbroenne preflight

The earlier Sbroenne result was based on host metadata and source inspection only. The recorded CLI was not launched.

| Item | Observed or proposed scope |
| --- | --- |
| Shared entry point | No deployed shared Excel router identified in the available skills, active rules, or repository. The [shared contract](https://github.com/ciahciach/versuni-search-ecosystem/issues/63#issuecomment-7108392518) is a reference, not an entry point. The `excel-cli` skill is a backend recipe, not the shared router. |
| Candidate | Installed `excelcli.exe`, product `Sbroenne.ExcelMcp`, file version `2.1.0.0`, product version `2.1.0+d463dfd97b730bcafe820dc7b21727c36276a6d3`. Observed via `Get-Command excelcli` and its `FileVersionInfo`; the CLI was not launched. |
| Excel build | Installed `EXCEL.EXE` file version `16.0.20527.20194`; Office Click-to-Run reports the same version and `x64`. Runtime build and session behavior were not observed. |
| Profile and operation | Proposed: replace one existing ordinary scalar cell formula in a disposable local synthetic XLSX, without VBA, XLM, external links, queries, connections, or a Data Model. No fixture was created or opened; this is not a verified profile or qualification. |
| Authorization | The current request to implement #40 covers preflight and the ticket's synthetic-only qualification scope. Authorization for a specific runtime open and save was not evaluated because no compliant route was identified; record the applicable authorization before running either. The [contract approval](https://github.com/ciahciach/versuni-search-ecosystem/issues/63#issuecomment-7108670667) is not itself runtime authorization. No substitute route, macros, refresh, global changes, production access, acceptance, or synchronization is in scope. |

### Sbroenne findings

The matching upstream revision's [`ExcelBatch` open path](https://github.com/sbroenne/mcp-server-excel/blob/d463dfd97b730bcafe820dc7b21727c36276a6d3/src/ExcelMcp.ComInterop/Session/ExcelBatch.cs) passes `UpdateLinks: 0`, selects `ForceDisable` for the proposed XLSX, and can pass `ReadOnly` at the COM layer. Those are source observations, not evidence that the installed CLI performed a compliant open or an independent readback without saving.

That path sets `AutomationSecurity` before the open loop without capturing and restoring the previous value around `Open` on success or failure. It starts Excel visible before open even when the caller requests a hidden session; the suppression switch is test-only in that source, and no visibility exception was established for this fixture. The open path does not establish scoped event or query-refresh controls. Excluding XLM and refresh-capable parts would require passive verification of the actual fixture; `ForceDisable` and `UpdateLinks: 0` alone do not cover them.

### Sbroenne stage results

| Stage | Result |
| --- | --- |
| Controlled open of isolated copies | `NOT_RUN`: no shared entry point identified and candidate open controls do not meet the contract. |
| No-op preservation before editing | `NOT_RUN`: no open/save cycle or preservation comparison. |
| No-write dry-run | `NOT_RUN`: no pinned synthetic base, formula plan, or before/after hash comparison. |
| Targeted save on a distinct copy | `NOT_RUN`: no formula write, calculation, or save. |
| Independent read-only reopen and re-export | `NOT_RUN`: no saved copy; no formula, numeric result, or unrelated-content comparison. |
| Final acceptance | `NOT_RUN`: outside #40's scope. |

No workbook was opened or changed during the Sbroenne preflight. It does not qualify the CLI or affect the scoped direct COM result above.
