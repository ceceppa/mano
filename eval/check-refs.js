#!/usr/bin/env node
"use strict";

/**
 * check-refs — verify cross-file section pointers in the shipped Markdown.
 *
 * The skills reference shared rules by file + section, e.g.:
 *
 *   `_mano/rules/hooks.md` → **Post-Hook Findings Triage**
 *   "Scripts are mandatory" in `_mano/rules/core.md`
 *   defined in `_mano/rules/core.md` ("Canonical execution-log format")
 *
 * A pointer to a section that does not exist in the named file is exactly the
 * drift the workflow split can introduce, so this fails on any such pointer.
 * A section matches when a heading in the target file equals the pointer text
 * or starts with it (case-insensitive) — "Writing artifacts" may point at
 * "Writing artifacts: create once, edit thereafter".
 *
 * Exit 0 when every pointer resolves; exit 1 with a listing otherwise.
 */

const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..");
const SRC = path.join(REPO_ROOT, "src");

// Runtime path -> repo source path.
function sourcePathFor(target) {
  if (target === "_mano/workflow.md") return path.join(SRC, "workflow.md");
  let m = /^_mano\/(rules|skills|templates)\/([a-z0-9-]+\.md)$/.exec(target);
  if (m) return path.join(SRC, m[1], m[2]);
  if (target === "AGENTS.md") return path.join(SRC, "bootstrap", "AGENTS.md");
  if (target === "CLAUDE.md") return path.join(SRC, "bootstrap", "CLAUDE.md");
  return null;
}

function headings(text) {
  const out = [];
  for (const line of text.split("\n")) {
    const m = /^#{1,6}\s+(.*?)\s*$/.exec(line);
    if (m) out.push(m[1].replace(/\*\*/g, "").trim());
  }
  return out;
}

function filesToScan() {
  const files = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(p);
      else if (entry.isFile() && (p.endsWith(".md") || entry.name === "cursorrules")) files.push(p);
    }
  };
  walk(SRC);
  return files;
}

// The three pointer shapes used across the source files.
const POINTER_PATTERNS = [
  // `FILE` → **SECTION**
  /`((?:_mano\/[a-z0-9/.-]+\.md)|AGENTS\.md|CLAUDE\.md)`\s*(?:→|->)\s*\*\*([^*]+)\*\*/g,
  // "SECTION" in `FILE`
  /"([^"\n]+)" in `((?:_mano\/[a-z0-9/.-]+\.md)|AGENTS\.md|CLAUDE\.md)`/g,
  // `FILE` ("SECTION")
  /`((?:_mano\/[a-z0-9/.-]+\.md)|AGENTS\.md|CLAUDE\.md)`\s*\("([^"\n]+)"\)/g,
];

function collectPointers(text) {
  const pointers = [];
  for (const [index, pattern] of POINTER_PATTERNS.entries()) {
    pattern.lastIndex = 0;
    let m;
    while ((m = pattern.exec(text)) !== null) {
      const [target, section] = index === 1 ? [m[2], m[1]] : [m[1], m[2]];
      const line = text.slice(0, m.index).split("\n").length;
      pointers.push({ target, section: section.trim(), line });
    }
  }
  return pointers;
}

function main() {
  const failures = [];
  const headingCache = new Map();

  for (const file of filesToScan()) {
    const text = fs.readFileSync(file, "utf8");
    for (const pointer of collectPointers(text)) {
      const source = sourcePathFor(pointer.target);
      const rel = path.relative(REPO_ROOT, file);
      if (source === null) continue; // not a Mano-shipped file — out of scope
      if (!fs.existsSync(source)) {
        failures.push(`${rel}:${pointer.line}: points at missing file ${pointer.target}`);
        continue;
      }
      if (!headingCache.has(source)) {
        headingCache.set(source, headings(fs.readFileSync(source, "utf8")));
      }
      const wanted = pointer.section.toLowerCase();
      const found = headingCache
        .get(source)
        .some((h) => h.toLowerCase() === wanted || h.toLowerCase().startsWith(wanted));
      if (!found) {
        failures.push(
          `${rel}:${pointer.line}: section "${pointer.section}" not found in ${pointer.target}`,
        );
      }
    }
  }

  if (failures.length) {
    process.stderr.write("check-refs: unresolved section pointers:\n");
    for (const f of failures) process.stderr.write(`  ${f}\n`);
    process.exit(1);
  }
  process.stdout.write("check-refs: all section pointers resolve\n");
}

if (require.main === module) main();

module.exports = { sourcePathFor, headings, collectPointers };
