# Desktop Excel route preflight (#40)

**2026-11-24: NOT_QUALIFIED.** This is a host metadata and source inspection record, not a desktop Excel run. [Issue #40](https://github.com/ciahciach/skills/issues/40) remains a prerequisite for [#27](https://github.com/ciahciach/skills/issues/27).

| Item | Observed or proposed scope |
| --- | --- |
| Shared entry point | No deployed shared Excel router identified in the available skills, active rules, or repository. The [shared contract](https://github.com/ciahciach/versuni-search-ecosystem/issues/63#issuecomment-7108392518) is a reference, not an entry point. The `excel-cli` skill is a backend recipe, not the shared router. |
| Candidate | Installed `excelcli.exe`, product `Sbroenne.ExcelMcp`, file version `2.1.0.0`, product version `2.1.0+d463dfd97b730bcafe820dc7b21727c36276a6d3`. Observed via `Get-Command excelcli` and its `FileVersionInfo`; the CLI was not launched. |
| Excel build | Installed `EXCEL.EXE` file version `16.0.20527.20194`; Office Click-to-Run reports the same version and `x64`. Runtime build and session behavior were not observed. |
| Profile and operation | Proposed: replace one existing ordinary scalar cell formula in a disposable local synthetic XLSX, without VBA, XLM, external links, queries, connections, or a Data Model. No fixture was created or opened; this is not a verified profile or qualification. |
| Authorization | The current request to implement #40 covers preflight and the ticket's synthetic-only qualification scope. Authorization for a specific runtime open and save was not evaluated because no compliant route was identified; record the applicable authorization before running either. The [contract approval](https://github.com/ciahciach/versuni-search-ecosystem/issues/63#issuecomment-7108670667) is not itself runtime authorization. No substitute route, macros, refresh, global changes, production access, acceptance, or synchronization is in scope. |

## Preflight findings

The matching upstream revision's [`ExcelBatch` open path](https://github.com/sbroenne/mcp-server-excel/blob/d463dfd97b730bcafe820dc7b21727c36276a6d3/src/ExcelMcp.ComInterop/Session/ExcelBatch.cs) passes `UpdateLinks: 0`, selects `ForceDisable` for the proposed XLSX, and can pass `ReadOnly` at the COM layer. Those are source observations, not evidence that the installed CLI performed a compliant open or an independent readback without saving.

That path sets `AutomationSecurity` before the open loop without capturing and restoring the previous value around `Open` on success or failure. It starts Excel visible before open even when the caller requests a hidden session; the suppression switch is test-only in that source, and no visibility exception was established for this fixture. The open path does not establish scoped event or query-refresh controls. Excluding XLM and refresh-capable parts would require passive verification of the actual fixture; `ForceDisable` and `UpdateLinks: 0` alone do not cover them.

## Stage results

| Stage | Result |
| --- | --- |
| Controlled open of isolated copies | `NOT_RUN`: no shared entry point identified and candidate open controls do not meet the contract. |
| No-op preservation before editing | `NOT_RUN`: no open/save cycle or preservation comparison. |
| No-write dry-run | `NOT_RUN`: no pinned synthetic base, formula plan, or before/after hash comparison. |
| Targeted save on a distinct copy | `NOT_RUN`: no formula write, calculation, or save. |
| Independent read-only reopen and re-export | `NOT_RUN`: no saved copy; no formula, numeric result, or unrelated-content comparison. |
| Final acceptance | `NOT_RUN`: outside #40's scope. |

No workbook was opened or changed; neither the original nor an approved synchronization point was touched. No simulated pass, alternate backend, installation, or global settings change was used. To resume #40, identify the actual shared entry point and a candidate version with compliant open controls, then run the listed stages on preflighted disposable copies. Do not advance #27 on the basis of this record.
