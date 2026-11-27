# Shared Glossary Setup

Read [shared-glossary.md](./shared-glossary.md) bundled beside this procedure. Use its version and definitions, not a copy in the target repo or a download. If it is missing or unreadable, report the missing source and skip glossary changes. Installing or updating a skill is not a setup run.

## Compare

Locate the existing project glossary and any mapped context glossaries from the active domain instructions. Use the existing project glossary in place, even outside the root. Default to root `GLOSSARY.md` only when there is no established project glossary or unresolved legacy location. Reflect any separately approved layout change. Match terms by name, regardless of heading, bold or code formatting. A project glossary definition is managed only if it is in the shared section and recorded in that section's provenance comment for the source below. Compare definitions, not just names. If ownership or layout is ambiguous, show what you found and leave the affected content untouched until resolved.

- **Missing:** propose adding the bundled definition to the shared section if there is no project-wide definition.
- **Managed update:** if the definition differs, show the current and proposed text and each version. Approval replaces only that definition and its provenance row. If the definition is unchanged, keep its existing provenance even when the bundle version changed.
- **Identical local project definition:** leave it where it is, without adding a duplicate or claiming it in provenance.
- **Local conflict:** show the local and bundled definitions and their scope. Keep the local definition by default. In the project glossary, do not add a second definition. If the user explicitly chooses adoption, propose one diff that removes only that local entry, adds the bundled entry under `## Shared vocabulary`, and adds its provenance row. Obtain approval for that exact diff before writing.
- **Absent from this bundle:** keep the existing term and provenance; do not propose automatic removal.

Do not edit mapped context glossaries. A context definition takes precedence there, whether identical or conflicting, and does not prevent proposing an entry missing from the project glossary.

## Propose

Use the existing `## Shared vocabulary` section or append it without reorganizing existing domain sections. If creating the root file, start with `# Glossary`. Use the bundle's groups and definitions for approved entries. Put one HTML comment immediately below `## Shared vocabulary`, in this format:

```markdown
<!-- shared-glossary
source: ciahciach/skills
path: skills/engineering/setup-matt-pocock-skills/shared-glossary.md
Issue tracker: v1
Worktree: v1
-->
```

The term rows are examples: record one row with the bundled version for each approved entry actually written. If `GLOSSARY-MAP.md` exists and the project glossary already exists or is proposed, propose a relative link to it in the map. Link to the file even if all its definitions remain local. Preserve existing context mappings and reuse an existing valid link to the project glossary or its shared section instead of adding another.

List missing terms, managed updates, and local conflicts separately. Show the exact proposed diff and wait for explicit approval. If approval is partial, include only the approved edits and their provenance; omit the map link if its target file will not exist.

## Apply

Recheck the target files against the proposal before applying; if they changed, refresh the proposal and ask for approval again. If nothing is approved or the resulting diff is empty, do not write either file, even to normalize formatting or bump versions. Otherwise write only files with an approved non-empty diff. Read back any changes and report which glossary files were written, or that neither was written.
