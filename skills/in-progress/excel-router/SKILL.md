---
name: excel-router
description: "Use when a Windows Excel task involves a workbook, an Excel export, VBA, Power Query, or the Excel Data Model. Selects an interface by scoped evidence or bounded qualification before loading a recipe."
metadata:
  version: "1.1.0"
---

# Excel router

Entry point for Windows Kilo VS Code. After rollout start with `skill(name: "excel-router")`, even if an interface was named. For an explicitly requested pre-rollout review, read this `SKILL.md` by its supplied absolute path and apply it without relying on skill discovery. This is a decision procedure, not permission or a test result. [Selection and trial contract](https://github.com/ciahciach/skills/issues/107#issuecomment-7196611688); [earlier compatibility reference](https://github.com/ciahciach/versuni-search-ecosystem/issues/63#issuecomment-7108392518).

## Route before touching the workbook

1. Identify the intended artifact, exact operation, authorized read/change effects and applicable project safeguards. An existing export with adequate freshness qualifies for `text` without Excel or a recipe. If freshness is unknown, say so; do not silently refresh or regenerate it.
2. Record the workbook profile: `simple`, `application` or `unknown`. Extensions alone are not evidence. VBA, XLM, Power Query, model, controls, connections, add-ins or exchange contracts are application signals; a known new plain XLSX can be simple. Unknown permits bounded passive profiling, not guessed runtime or parser write.
3. Choose the highest applicable class: `text` (exports/source), `passive` (bytes or saved state, no Excel), `runtime` (opening Excel, calculation, macro or refresh), `save` (any persistent workbook change, including file libraries, AutoSave or shutdown). Track ancillary effects separately. Permission to read or run is not permission to save.
4. For `text` or sufficient `passive` work, select that route directly once access and controls are confirmed. For `runtime` or `save`, establish the actual implementation/version, actions/schema, relevant host/build and required controls before loading any recipe. Identity or capability checks are not qualification. Include only methods available and permitted for the named target and effects, with a demonstrable way to meet and verify the required controls. A named skill, configured tool or CLI help alone does not establish eligibility. Do not install anything or escalate the operation to obtain a route.
5. For `runtime` or `save`, establish the permitted mode before calling the [decision step](#decision-step). Routine work requires positive evidence for the exact scope. For differential reuse, establish and cite that the relevant contract is unchanged before treating old evidence as applicable. A writer of a new simple document needs its own scoped evidence; state what engine can verify the result without inheriting desktop qualification or claiming unsupported calculation. Qualification requires separate authorization for a named isolated synthetic input, operation and effects. Decision-only authorization may identify a candidate; execution and any save to a separate copy must be explicitly in scope. The synthetic scope is not the user workbook's scope.
6. For `runtime` or `save`, rank eligible interfaces and their distinct methods by fit to this operation and its controls, not a fixed MCP/CLI/COM preference. Call the decision step with that order and the authorized scope; include `trial` only when separately authorized. If routine evidence is missing and qualification is not authorized, report `blocked` and name the missing evidence or the exact synthetic scope for the human to approve. For every class, report the decision before loading a recipe or using the selected route.

## Decide and try

- Matching positive evidence selects a method without probing the target. A matching exclusion removes that method; an unverified result or temporary unavailability is not an exclusion.
- For a `candidate` or the first `trial`, report `selected` in qualification mode with `qualification=NOT_VERIFIED` and `execution=NOT_RUN` separately. For an evidence-backed `selected`, report the actual evidence instead. In any decision-only task, stop after reporting the decision and `execution=NOT_RUN`, before loading a recipe or running a method. Later interface changes and results get short progress entries, not another full report.
- Execute an evidence-backed `selected` only if the authorized target, effects and controls still match. For a `trial`, execute only the next authorized method, on an isolated synthetic input. Before every trial that may write, verify the synthetic base is unchanged and prepare a fresh separate copy from that base. Never reuse a previous trial's copy; if the base or a fresh copy cannot be verified, stop. Recheck authorization and controls immediately before use, including on an interface change. Do not retry a trial method or allow internal retries (including recipe-level `Open` retries); omit methods that cannot run with retries disabled. Apply any stricter recipe, project or host limits. After a trial, report its redacted outcome and submit that observation to obtain the next decision. Success requires all operation-specific checks, not a tool return code. End at `verified`; never continue on the user workbook based on this synthetic result.
- If an effect is unresolved, including a possibly completed save or a process still running after a timeout, stop across all methods and interfaces. Have the human account for the owned process and inspect the isolated copy before any further operation. Never retry a write with an unknown effect. At exhaustion report `blocked`, name the failed/missing control or unavailable capability and give a concrete human action to resolve it, such as obtaining an authorized interface that offers independent readback. A block before any trial gets the full report; a block after trials is an execution result, not a second full report.

## Decision step

Use [`route.py`](route.py) from the same router directory with Python 3.9 or newer. Pass one JSON object on stdin to `python -B -X utf8 <absolute path to route.py>` and read its JSON result. It reads no workbook, loads no recipe and runs no method. If it is missing or fails, stop and report the blocker; do not improvise a runtime route. Supply only redacted facts:

- `scope`: `operation`, `profile`, `class`, `effects`, `controls`, `environment` (relevant host and Excel build, or the applicable non-desktop environment), `boundary` (evidence applicability label) and `target_kind` (`synthetic` or `target`). Use stable labels and sorted lists for effects and controls. `controls` must include the check that verifies the operation's expected result. Only include evidence within its demonstrated applicability; a synthetic run does not imply routine qualification.
- `candidates`: ordered entries with `interface` (actual implementation), `version` (observed), and ordered `methods` (canonical action IDs, not aliases or code). Supply one entry per interface. Include only admissible methods, using fewer than five where a stricter limit applies.
- `evidence`: entries with the same `scope` shape, `interface`, `version`, `method`, `reference` and `outcome` (`verified` or `excluded`). An exclusion requires a scoped, observed gap. Do not fabricate missing facts from a similar profile or another implementation.
- For separately authorized qualification only, add `trial` with `authorization` (`decision-only` or `execute`), `attempts` (initially `[]`) and `limit` (the strictest applicable total operation-attempt cap, or `null` if none). For a sequence that may use desktop Excel, set `limit` to at most three per [runtime controls](runtime.md), shared across methods and interfaces. A stricter project or host cap wins. The per-interface cap is separate.
- Append each tried method as `{interface, version, method, outcome}`. Use `verified` only when all controls pass; `gap` for a confirmed limitation; `unavailable` if it could not run; `not-verified` for inconclusive checks. For `gap` or `not-verified`, effects must be accounted for; include `control` with the failed or unconfirmed label from `scope.controls`. If the process or any effect is not accounted for, use `unresolved-effects` instead and stop. Keep the scope, order, evidence, limit and authorization fixed. A change that invalidates the plan stops the sequence; do not reset the budget or bypass an unresolved write.

The decision step skips duplicate action IDs and matching exclusions. For qualification trials it considers at most five admissible methods per interface, then advances to the next eligible interface. `selected` is an evidence-backed choice; `candidate` is selection only; `trial` identifies one next method; `verified` and `blocked` are terminal. After the full decision entry, note each returned `excluded` method and its evidence reference once in session progress. Keep trial observations in the session, redacting paths, values, credentials and raw output.

## Select the current recipe

| Selected route | Load only after selection |
|---|---|
| Current export/source | None |
| Passive package or saved-state inspection | `passive-excel-audit` |
| File-library write to a verified simple document | `xlsx` |
| Sbroenne MCP with matching tools and controls | `excel-mcp` |
| Sbroenne CLI with matching executable and controls | `excel-cli` |
| Explicitly selected direct COM for a justified gap or synthetic qualification | `excel-com-safe` |
| Approved GUI method with matching controls | Applicable scoped recipe if one exists; otherwise none |

Use `skill(name: "<selected-recipe>")` for the current method only, plus its narrow domain reference if needed. MCP and CLI do not share sessions. Negokaz is not Sbroenne and does not inherit its recipe or evidence. Direct COM needs explicit scope; it is not an automatic substitution. An application or unknown workbook does not go to a file writer because it is XLSX.

Visibility is an execution setting, not a different interface or a grant to automate GUI. A GUI method needs explicit consent for the specific interaction, the same target/effects checks, and an owned session without forced takeover. A step the human must perform (such as signing in to SharePoint) is `human-in-the-loop`, not an agent method and not a verified trial.

## Execution controls

Before Excel opens, apply [runtime and persistence controls](runtime.md) and the chosen recipe. The shared controls take precedence over recipe examples. In particular, in-session readback cannot replace independent reopen/readback of the saved copy. Exclude a method that cannot demonstrate the required controls. A selection or an instruction-only evaluation is not an execution result.

## Report the decision once

Emit the full line as the first progress entry after deciding, exactly once in the session, before any recipe load or operation execution. Identity, scope and authorization checks can come first. Never put the full line in the final response or repeat it on a later result.

`Excel route | router=excel-router@<metadata.version> | class=<text/passive/runtime/save> | profile=<simple/application/unknown> | mode=<routine/qualification> | decision=<selected/blocked> | interface=<implementation and observed version, or none/unknown> | recipe=<skill or none> | authorization=<scope or missing> | qualification=<matching evidence reference, NOT_VERIFIED or N/A> | reason=<why, including blockers>`

Report execution separately (`NOT_RUN` until performed). Do not turn a blocked or selection-only result into a PASS. Use redacted scope labels and evidence references, not workbook paths, cell data, credentials or raw tool output.
