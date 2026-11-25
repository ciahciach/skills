# Warp Skill Doctor: criteria, FAIL, and improvement routing

Research snapshot: 2026-11-25. Sources are the public Skill Doctor distribution, Warp documentation and product pages, and the official posting of Ben Holmes's talk. The three sources describe related but distinct workflows.

## Local Skill Doctor: four scored dimensions

The [scoring instructions][scoring] require a label, its numeric score, and a 1-3 sentence reason tied to specific transcript evidence for each applicable rubric. The scores are discrete, not a free-form scale.

| Dimension | Labels and raw scores | What it assesses |
| --- | --- | --- |
| [Efficiency][efficiency] | `highly_efficient` 1; `mostly_efficient` 0.8; `mostly_inefficient` 0.4; `highly_inefficient` 0.2 | Avoidable work, rework, user corrections, redundant reads/retries, batching, and verification timing. |
| [Code Quality][quality] | `approve` 1; `block` 0.2; `insufficient_evidence` 0.5 (excluded) | The code artifact against repo conventions and reviewer standards; one merge-blocking defect suffices for `block`. No code change or too little visible diff is insufficient evidence. |
| [Procedure Compliance][procedure] | `fully_compliant` 1; `mostly_compliant` 0.8; `noncompliant` 0.2 | Applicable standing rules, skill invocation and follow-through; task-specific instructions are out of scope. A single protective-rule breach disqualifies. No applicable rules or skills is `fully_compliant`. |
| [Verbosity][verbosity] | `proportionate` 1; `verbose` 0.2; `terse` 0.1 | Proportionality of written agent communication, not diff or tool-output size. Over- and under-communication both fail. |

**FAIL is ANY, not ALL:** one or more applicable **raw** scorer results strictly below `0.5` makes the conversation a member of `failed_conversations`. Exactly `0.5` is not below the threshold. `insufficient_evidence` does not count toward failure or the code-quality mean. A single `mostly_inefficient` (0.4) is enough even if the other applicable scorers pass. Neither `skill_coverage` nor `overall` participates in this gate. [Exact instruction][gate]

**Report scale is separate:** average each rubric across the sampled sessions, excluding insufficient code evidence (if none is usable, default the raw code-quality mean to `0.5` and disclose it). Curve each mean as `0.5 + 0.5 * raw_mean`. `skill_coverage` is the uncurved share of sampled sessions with at least one installed skill detected (zero if no skills were found). `overall` weights curved efficiency 25%, code quality 25%, procedure compliance 20%, verbosity 15%, and literal coverage 15%. [Aggregation instructions][aggregation] The [renderer][renderer] displays `round(score * 100)`; the letter cutoffs are A+ 0.97, A 0.93, A- 0.90, B+ 0.87, B 0.83, B- 0.80, C+ 0.77, C 0.73, C- 0.70, D 0.60, else F. The [product page][product] shows a sample `B / 82` and a selective list of metrics, not the canonical scorecard; the pinned renderer maps an exact 0.82 to B-. A report F is not the conversation FAIL filter.

## Local Skill Doctor: when a failure becomes a change

1. Use **only** `failed_conversations` as evidence for improvement suggestions and draft edits. Cite the failed session, scorer, and moment. [Evidence and draft instructions][gate]
2. Attribute the failure, cluster by root cause across scorers/classifications, rank by frequency times severity, and verify against the current repository and agent configuration. Drop unverified findings. [Improvement guide][improvements]
3. Propose a change only if a missing, incorrect, or underspecified instruction on a named owning surface (agent configuration, skill, or in-repo guidance) would have prevented the failure if followed. Require more than one source run or one severe occurrence that proves the gap. Do not file for a correct instruction that was merely ignored, model variance, restatements, or fixes outside the instruction surfaces. [Improvement guide][improvements]
4. The local skill's specified output is a proposed `SKILL.md` and diff in a scratch report, not an automatic PR or modification to live skill files. No verified actionable gap means no edit. [Draft instructions][drafts]

## Warp Factories: per-scorer failures and a separate trigger

[Configuring Scorers][factory-scorers] documents custom judge instructions, classifications with a score, and a configurable pass threshold per scorer. [Warp engineering][factory-blog] gives a 0-1 classification scale and an example with threshold `0.8`: `clean` (1.0) passes; `contains unnecessary comments` (0.7) and `introduces needless complexity` (0.3) fail. It also describes an internal Efficiency scorer with threshold `1.0` and illustrates Task Compliance, Procedure Compliance, Verbosity, Efficiency, and Code Quality; these are examples/configurations, not a universal bundled scoring gate. The public Factories sources consulted do not specify an ALL/ANY rule for a single verdict across scorers; they describe failures and opt-in at the individual scorer level.

[Configuring and reviewing Self-improvement][factory-improvement] defines failure as strictly below that scorer's threshold. The scheduled check groups failures per agent for scorers with Self-improvement enabled. By default, it starts a follow-up after 25 distinct unreviewed failures **or** when the oldest unreviewed failure is seven days old; GitHub-backed configuration allows `failedRunThreshold` from 1 to 50. `Run now` can include an agent with one unreviewed failure. A follow-up can propose changes to code or definition files (prompts, skills, config); a PR submitted for review links the failing runs and scorer results under `Regressions addressed`. None of these scheduling or review rules changes the local skill's `ANY < 0.5` filter.

## Ben Holmes: what the talk evidence establishes

The organizer's [official YouTube posting][talk] describes collecting conversations with tool calls/outputs, LLM-as-judge scoring, and a daily agent that finds patterns in failures and opens PRs for skills and configuration. The publication's chapter markers identify the following entry points:

| Timestamp | Official chapter |
| --- | --- |
| [05:08](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=308s) | What to capture: transcripts, tool calls, outputs |
| [06:00](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=360s) | Scoring redundant tests |
| [06:55](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=415s) | Scoring verbosity |
| [07:52](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=472s) | Scoring efficiency |
| [08:57](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=537s) / [10:41](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=641s) | Writing a scoring rubric / Grading a real conversation |
| [12:51](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=771s) / [13:47](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=827s) | A daily agent that suggests fixes / Try it: Skill Doctor |
| [16:14](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=974s) / [17:59](https://www.youtube.com/watch?v=pz74r-4dGfQ&t=1079s) | Tracking scores over time / Self-improvement PRs in Warp |

**Unverified from the talk:** the exact spoken labels, numeric cutoffs, the ALL/ANY gate, and whether the demo used the currently published revision. The official English caption track was listed but returned an empty response. Timestamps above come from the uploader's chapter metadata, not a verified transcript or slide transcription. Redundant tests is a named talk example, not a fifth rubric in the pinned local skill. The daily loop in the talk description is not evidence of the current Factories schedule.

**Implication for the map:** `ANY < 0.5` is a source-backed reference if choosing parity with local Skill Doctor. It is not a requirement imposed by the talk or by Warp Factories. Keep the session verdict, aggregate report, admission to improvement analysis, and evidence required for an edit separate.

[talk]: https://www.youtube.com/watch?v=pz74r-4dGfQ
[product]: https://www.warp.dev/skill-doctor
[scoring]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/SKILL.md#L90-L99
[aggregation]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/SKILL.md#L101-L115
[gate]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/SKILL.md#L115-L124
[drafts]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/SKILL.md#L122-L135
[efficiency]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/scorers/efficiency.md#L2-L34
[quality]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/scorers/code-quality.md#L2-L37
[procedure]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/scorers/procedure-compliance.md#L2-L33
[verbosity]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/scorers/verbosity.md#L2-L30
[improvements]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/references/skill-improvements.md#L3-L29
[renderer]: https://github.com/warpdotdev/common-skills/blob/7c4eb852de8d7c3e68c81802e1c59db9a611f914/.agents/skills/skill-doctor/scripts/render_report.py#L23-L46
[factory-scorers]: https://docs.warp.dev/factories/measure-and-improve/scorers/
[factory-improvement]: https://docs.warp.dev/factories/measure-and-improve/self-improvement/
[factory-blog]: https://www.warp.dev/blog/engineering-self-improving-software-factories
