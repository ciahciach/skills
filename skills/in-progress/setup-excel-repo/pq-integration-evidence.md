# Power Query integration evidence

| Field | Value |
| --- | --- |
| Mode | $mode |
| Evidence class | $evidence_class |
| Repository | `$repository` |
| Integration PR / execution Issue | #$pr / #$issue |
| Authorized merge | `$merge_sha` |
| Job / attempt | `$job` / `$attempt` |
| Desktop and interface | $environment |
| Matching qualification | $qualification |
| Source commit | `$source_sha` |
| Proposal SHA-256 | `$proposal_sha256` |
| Input version / SHA-256 | `$input_version` / `$input_sha256` |
| Approved synchronization record SHA-256 | `$sync_sha256` |
| Output version / SHA-256 | `$output_version` / `$output_sha256` |
| Verification | $verification |
| Owner acceptance | $acceptance |
| Pre-write eligibility | $eligibility |
| Save evidence | $save_evidence |
| Passive package evidence | $package_evidence |
| Reopen evidence | $reopen_evidence |
| Read-back tables, ranges and connections | $load_destinations |
| Package-confirmed connection to query mappings | $connection_queries |
| Data Model present | $data_model_present |

| Check | Result |
| --- | --- |
| Saved only a separate copy | $copy_only |
| Independent read-only reopen at the exact output hash | $independent_readback |
| All intended M and adjacent M matched | $m_matches |
| Worksheet load destinations and connection mappings preserved | $load_wiring_preserved |
| Input preserved by SHA-256 | $base_unchanged |
| Refresh requested by adapter | $refresh |
| Macros permitted by adapter | $macros |
| Link updates permitted by adapter | $links_updated |

Scope: $claim_limit Opening controls are procedure attestations, not monitoring of all Excel activity. Preserved worksheet caches and package markers corroborate them for this synthetic profile. No network isolation is claimed.

Verification does not advance the synchronization point, accept an output as a base, or grant structural write access. This report identifies the private copy by version and SHA-256, not by its local path. Do not add binaries, cell data, M text, secrets, or private paths to published evidence.
