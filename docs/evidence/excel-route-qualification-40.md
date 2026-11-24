# Desktop Excel route qualification (#40)

**2026-11-24: direct COM NOT_QUALIFIED.** The Excel-prepared fixture passed no-op, dry-run, targeted save and independent read-only reopen. The final package comparison detected unclassified changes in `xl/calcChain.xml` and `xl/workbook.xml`. No deployed shared Excel entry point was identified. [Issue #40](https://github.com/ciahciach/skills/issues/40) remains a prerequisite for [#27](https://github.com/ciahciach/skills/issues/27).

## Direct COM qualification entry

- Route selection: the user explicitly chose direct COM with `excel-com-safe` for #40 and authorized the synthetic open/save qualification, not production edits, label changes, or final acceptance. This is an explicit ticket-level route selection, not an automatic fallback or a global router deployment. A shared router can point this qualification case to the command below; do not use it as a qualified writer for #27.
- Entry: `py -3.14 -B -X utf8 scripts/qualify-excel-com.py`, from this repository. Implementation: [synthetic-only runner](../../scripts/qualify-excel-com.py) and `pywin32` 312 `DispatchEx`, Python 3.14.4. `openpyxl` 3.1.5 only generates the fixture and reads saved state, never performs the target edit.
- Live runtime: Excel `Version=16.0`, `Build=20527`; installed executable `16.0.20527.20194` x64. Fixture: one sheet `Calc`, `A1=10`, existing ordinary `B1 = A1*2`, neighboring `C1 = A1+1`, and a styled text sentinel. Intended mutation `B1 = A1*3` (numeric result `30`). The initial package inventory and input formulas contain no VBA, XLM, query, connection, model, or external-link parts.
- Preparation: Excel saved a disposable copy of the generated seed as the baseline before taking any qualification hashes. That save applied the host's existing policy and introduced `docProps/custom.xml`. The prepared profile permits that part but requires its byte-for-byte preservation in later saves. No label was manually set, removed, or reported. The seed and prepared baseline were not the targets of any subsequent saves.
- Live open evidence: newly owned PIDs `97544` (missing-file probe), `109808` (prepare), `104116` (no-op), `90884` (save), and `106728` (readback). All were hidden with events disabled and logged `UpdateLinks=0` and `AutomationSecurity` `1 -> 3 -> 1`. All successful opens checked `AutoSaveOn=false`, zero queries/connections and no Excel link sources. This is scoped evidence, not proof for files containing XLM/queries or external links.

| Stage | Direct COM result |
| --- | --- |
| Controlled open of an isolated XLSX copy | `PASS` within the synthetic profile; successful open and error-path restoration observed. |
| No-op save | `PASS` against the prepared baseline. The cell export and package parts matched after excluding the document modification timestamp. |
| No-write dry-run | `PASS`: identified `Calc!B1` and `=A1*2` to `=A1*3`; hashes of all existing scratch files stayed the same. |
| Targeted save and numeric result | `PASS` for the save itself: distinct copy, `=A1*3` and numeric `30`. |
| Independent read-only reopen and re-export | `PASS` for the reopen and cell export: distinct PID, opened read-only, no save, candidate hash unchanged across reopen, and only `Calc!B1` differed in the cell export. `NOT_VERIFIED` for package preservation: after masking only `B1` formula/result and the document modification timestamp, `xl/calcChain.xml` and `xl/workbook.xml` differed. The label metadata matched. The final end-of-run seed and base hash assertion was not reached. |
| Acceptance and synchronization | `NOT_RUN`: outside scope. Only temporary synthetic files were used. |

The first run on an unprepared copy stopped at the no-op profile gate: Excel added `docProps/custom.xml` with an `MSIP_Label` property. The later prepared-fixture run resolved that blocker without process termination, label removal, Office policy changes, or fallback. For the next run, record a structural diff of the two changed XML parts before scratch cleanup. Do not exclude either part wholesale: classify the exact changes and show that they cannot affect unrelated workbook behavior. Identify and verify the shared entry point separately. Sbroenne follow-up [#45](https://github.com/ciahciach/skills/issues/45) does not block COM work.

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

No workbook was opened or changed during the Sbroenne preflight. Do not advance #27 on the basis of either result.
