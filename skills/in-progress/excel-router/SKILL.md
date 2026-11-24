---
name: excel-router
description: "Use when a Windows Excel task involves a workbook, an Excel export, VBA, Power Query, or the Excel Data Model. Classifies the task and gates backend use before loading a recipe."
metadata:
  version: "1.0.0"
---

# Excel router

Entry point for Windows Kilo VS Code. After rollout start with `skill(name: "excel-router")`, even if a backend was named. For an explicitly requested pre-rollout review, read this `SKILL.md` by its supplied absolute path and apply it without relying on skill discovery. This is a decision procedure, not permission or a test result. [Approved contract](https://github.com/ciahciach/versuni-search-ecosystem/issues/63#issuecomment-7108392518).

## Route before touching the workbook

1. Identify the intended artifact, requested result, authorized read/change effects and applicable project safeguards. An existing export with adequate freshness is `text`: use it without starting Excel or loading any backend recipe. If freshness is unknown, say so; do not silently refresh or regenerate it.
2. Record the workbook profile: `simple`, `application` or `unknown`. Extensions alone are not evidence. VBA, XLM, Power Query, model, controls, connections, add-ins or exchange contracts are application signals; a known new plain XLSX can be simple. Unknown permits bounded passive profiling, not guessed runtime or parser write.
3. Choose the highest applicable class: `text` (exports/source), `passive` (bytes or saved state, no Excel), `runtime` (opening Excel, calculation, macro or refresh), `save` (any persistent workbook change, including file libraries, AutoSave or shutdown). Track ancillary effects separately. Permission to read or run is not permission to save.
4. Validate what is actually available for the operation before loading a recipe. Match the implementation, version, actions/schema and required controls. A skill name/version, enabled config, package cache, or CLI help is not that evidence. A side-effect-free identity/capability check is not qualification. Stop with the missing fact or control if unavailable. Do not install, switch backends, escalate to runtime or run a live probe as a fallback.
5. Check authorization for the specific target and effects. Routine `runtime` and `save` require applicable evidence for the backend implementation/version, operation, workbook profile and relevant host/build/controls. Differential reuse requires evidence that the relevant contract is unchanged. For a file-library write to a new simple document, use evidence for that writer's scoped use and state what engine can verify the result; do not inherit a desktop qualification or claim unsupported calculation. If evidence is missing, stop. A separately authorized qualification may select a candidate for a named isolated synthetic fixture and operation, with explicit scope (including execution and writes, if requested). This exception does not authorize running a prompt that only requests a decision, operating on user workbooks, or calling the route qualified.

## Select one backend recipe

| Selected route | Load only after selection |
|---|---|
| Current export/source | None |
| Passive package or saved-state inspection | `passive-excel-audit` |
| File-library write to a verified simple document | `xlsx` |
| Sbroenne MCP with matching tools and controls | `excel-mcp` |
| Sbroenne CLI with matching executable and controls | `excel-cli` |
| Explicitly selected direct COM for a justified gap or synthetic qualification | `excel-com-safe` |

Use `skill(name: "<selected-recipe>")` for the selected interface and, if needed, its narrow domain reference (e.g. `vba-compile-cycle` for a VBA import/test). A pre-rollout decision-only review names the recipe without loading or running it. Sbroenne is the desktop baseline candidate, not a blanket PASS. MCP and CLI do not share sessions. Negokaz-only access is not a match for the Sbroenne recipe and is not the isolated default; stop rather than infer actions or use COM. An application or unknown workbook does not go to a file writer because it is XLSX.

## Execution controls

Before Excel opens, apply [runtime and persistence controls](runtime.md) and the chosen recipe. Stop if the backend cannot demonstrate the required controls. A selection or an instruction-only evaluation is not a runtime result.

## Report the decision

Emit `Excel route | router=excel-router@<metadata.version> | class=<text/passive/runtime/save> | profile=<simple/application/unknown> | mode=<routine/qualification> | decision=<selected/blocked> | backend=<implementation and observed version, or none/unknown> | recipe=<skill or none> | authorization=<scope or missing> | qualification=<matching evidence reference, NOT_VERIFIED or N/A> | reason=<why, including blockers>`. If selection is for qualification, report execution separately (`NOT_RUN` until it is executed). Do not turn a blocked or selection-only result into a PASS.
