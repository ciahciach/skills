// Parses every SKILL.md's frontmatter with `yaml`, the parser the `skills`
// installer uses, so a skill that would be skipped on install fails here first.
import { readFileSync, readdirSync, realpathSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { parseDocument } from "yaml";

const root = fileURLToPath(new URL("..", import.meta.url));

function* skillFiles(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* skillFiles(path);
    else if (entry.name === "SKILL.md") yield path;
  }
}

const failures = [];
const packaged = process.argv.includes("--package");
const skills = new Map();

for (const file of skillFiles(join(root, "skills"))) {
  const where = relative(root, file);
  const match = readFileSync(file, "utf8").match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) {
    failures.push(`${where}: no frontmatter block`);
    continue;
  }
  const doc = parseDocument(match[1], { strict: true, uniqueKeys: true });
  if (doc.errors.length > 0) {
    failures.push(`${where}: ${doc.errors[0].message.split("\n")[0]}`);
    continue;
  }
  const data = doc.toJS();
  for (const key of ["name", "description"]) {
    if (typeof data?.[key] !== "string" || data[key].trim() === "") {
      failures.push(`${where}: missing \`${key}\``);
    }
  }
  skills.set(where.replaceAll("\\", "/"), data?.name);
}

if (packaged) {
  const pluginPath = ".claude-plugin/plugin.json";
  const marketplacePath = ".claude-plugin/marketplace.json";
  const plugin = JSON.parse(readFileSync(join(root, pluginPath), "utf8"));
  const marketplace = JSON.parse(readFileSync(join(root, marketplacePath), "utf8"));
  const seen = new Set();
  // Existing fork skills kept out of the package until their promotion is decided.
  const unpublished = new Set(["co-dalej", "granica", "implement-wave", "retrofit-repo"].map(
    (name) => `./skills/engineering/${name}`,
  ));
  const promoted = /^\.\/skills\/(engineering|productivity)\/[a-z0-9]+(?:-[a-z0-9]+)*$/;

  if (!Array.isArray(plugin?.skills) || plugin.skills.length === 0) {
    failures.push(`${pluginPath}: expected a nonempty skills array`);
  } else {
    for (const dir of plugin.skills) {
      if (typeof dir !== "string" || !promoted.test(dir)) {
        failures.push(`${pluginPath}: invalid promoted skill directory ${JSON.stringify(dir)}`);
        continue;
      }
      if (seen.has(dir)) failures.push(`${pluginPath}: duplicate skill directory ${dir}`);
      seen.add(dir);
      const file = `${dir.slice(2)}/SKILL.md`;
      if (!skills.has(file)) {
        failures.push(`${pluginPath}: missing or invalid ${file}`);
      } else if (skills.get(file) !== dir.split("/").at(-1)) {
        failures.push(`${file}: skill name must match its packaged directory`);
      } else {
        const resolved = relative(realpathSync(root), realpathSync(join(root, file))).replaceAll("\\", "/");
        if (resolved !== file) {
          failures.push(`${pluginPath}: ${file} must resolve to its declared repository path`);
        }
      }
    }
  }

  for (const file of skills.keys()) {
    const dir = `./${file.slice(0, -"/SKILL.md".length)}`;
    if (promoted.test(dir) && !unpublished.has(dir) && !seen.has(dir)) {
      failures.push(`${pluginPath}: missing promoted skill ${dir}`);
    }
  }

  const entries = marketplace?.plugins;
  if (typeof marketplace?.name !== "string" || !marketplace.name.trim()) {
    failures.push(`${marketplacePath}: missing marketplace name`);
  }
  if (
    typeof plugin?.name !== "string" || !plugin.name.trim() || !Array.isArray(entries) ||
    entries.length !== 1 || entries[0]?.name !== plugin.name || entries[0]?.source !== "./"
  ) {
    failures.push(`${marketplacePath}: expected one root entry (source "./") matching ${pluginPath}'s name`);
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  console.error(
    `\n${failures.length} validation error(s).`,
  );
  process.exit(1);
}
console.log("All SKILL.md frontmatter parses.");
if (packaged) console.log("Plugin skill paths and repository marketplace entry are consistent.");
