---
description: Validate repository skills and confirm which spawn copy Kilo VS Code loads.
---

1. From this repository checkout, run `npm run check-skills` (`npm.cmd run check-skills` on Windows if PowerShell blocks `npm.ps1`). If dependencies are missing, report `npm ci` as the prerequisite. Report the static result separately.
2. Call the Skill tool with `spawn` for inspection only. Do not follow its startup procedure or start a session. Compare the returned source directory, resolving links if needed, and the loaded Markdown body with this checkout's `skills/engineering/spawn/SKILL.md`. Ignore the tool wrapper, frontmatter, and line-ending differences when comparing bodies.
3. Report `PASS` for checkout discovery only when the source resolves to this checkout and the loaded text matches its skill. Otherwise report `BLOCKED`, with the actual and expected paths and whether the content differs. Do not change installed skills, config, or Agent Manager state. A discovery pass does not test either startup mode.
