#!/usr/bin/env node
"use strict";

/**
 * mano-init — installs Mano into the current project.
 *
 * Usage:
 *   npx mano-init install            interactive install into the current directory
 *   npx mano-init install --force    overwrite existing Mano files without asking
 *   npx mano-init install --yes      accept defaults, no prompts (installs CLAUDE.md, skips .cursorrules)
 *   npx mano-init --help
 *
 * Version is selected at the npm layer, e.g. `npx mano-init@next install`.
 *
 * Source layout (inside this package) -> runtime layout (user's project):
 *   src/skills/ src/templates/ src/hooks/ src/workflow.md  ->  ./_mano/
 *   src/bootstrap/AGENTS.md                                  ->  ./AGENTS.md     (always)
 *   src/bootstrap/CLAUDE.md                                  ->  ./CLAUDE.md     (optional)
 *   src/bootstrap/cursorrules                                ->  ./.cursorrules  (optional)
 *
 * Everything the installer ships lives under src/. Within it:
 *   src/bootstrap/ -> project-root files; src/templates/ -> artifact scaffolds
 *   that land in _mano/templates/ — different destinations, different folders.
 */

const fs = require("node:fs");
const path = require("node:path");
const readline = require("node:readline");

const PKG_ROOT = path.resolve(__dirname, "..");
// Everything the installer ships lives under src/ in the package.
const SRC = path.join(PKG_ROOT, "src");
const CWD = process.cwd();

// What lands inside ./_mano/ (read from src/)
const MANO_DIRS = ["skills", "templates", "hooks"];
const MANO_FILES = ["workflow.md"];

function log(msg) {
  process.stdout.write(msg + "\n");
}

function parseArgs(argv) {
  const args = { command: null, force: false, yes: false, help: false };
  for (const a of argv) {
    if (a === "--force") args.force = true;
    else if (a === "--yes" || a === "-y") args.yes = true;
    else if (a === "--help" || a === "-h") args.help = true;
    else if (!args.command) args.command = a;
  }
  return args;
}

function printHelp() {
  log(`mano-init — install Mano into the current project

Usage:
  npx mano-init install           Install Mano into the current directory
  npx mano-init install --yes     Non-interactive (installs CLAUDE.md, skips .cursorrules)
  npx mano-init install --force   Overwrite existing Mano files

Pin a version with npm's own syntax, e.g.:
  npx mano-init@next install
  npx mano-init@0.1.0 install

Always installed:
  ./_mano/        skills, templates, hooks, workflow
  ./AGENTS.md     universal agent contract

Optional (you'll be asked):
  ./CLAUDE.md     Claude Code dispatch guard
  ./.cursorrules  Cursor entry point`);
}

function ask(rl, question, defaultYes) {
  const suffix = defaultYes ? " [Y/n] " : " [y/N] ";
  return new Promise((resolve) => {
    rl.question(question + suffix, (answer) => {
      const a = answer.trim().toLowerCase();
      if (a === "") return resolve(defaultYes);
      resolve(a === "y" || a === "yes");
    });
  });
}

// Copy a file; returns "written" | "skipped" (skipped = target exists and not forcing)
function copyFile(src, dest, force) {
  if (fs.existsSync(dest) && !force) return "skipped";
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  return "written";
}

// Recursively copy a directory. Returns { written, skipped } counts.
function copyDir(srcDir, destDir, force) {
  let written = 0;
  let skipped = 0;
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const src = path.join(srcDir, entry.name);
    const dest = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      const r = copyDir(src, dest, force);
      written += r.written;
      skipped += r.skipped;
    } else if (entry.isFile()) {
      const r = copyFile(src, dest, force);
      if (r === "written") written++;
      else skipped++;
    }
  }
  return { written, skipped };
}

async function install(args) {
  // Sanity: confirm we're running from a real Mano package.
  if (!fs.existsSync(path.join(SRC, "skills")) || !fs.existsSync(path.join(SRC, "workflow.md"))) {
    log("Error: this package is missing Mano source files (src/skills/, src/workflow.md). Aborting.");
    process.exit(1);
  }

  const manoDir = path.join(CWD, "_mano");
  if (fs.existsSync(manoDir) && !args.force) {
    log("A `_mano/` directory already exists here.");
    log("Re-run with --force to overwrite it, or remove it first.\n");
  }

  log("Installing Mano into: " + CWD + "\n");

  // 1. _mano/ payload
  let totalWritten = 0;
  let totalSkipped = 0;
  for (const dir of MANO_DIRS) {
    const r = copyDir(path.join(SRC, dir), path.join(manoDir, dir), args.force);
    totalWritten += r.written;
    totalSkipped += r.skipped;
  }
  for (const file of MANO_FILES) {
    const r = copyFile(path.join(SRC, file), path.join(manoDir, file), args.force);
    if (r === "written") totalWritten++;
    else totalSkipped++;
  }
  log(`  _mano/        ${totalWritten} file(s) written` + (totalSkipped ? `, ${totalSkipped} skipped (already present)` : ""));

  // 2. AGENTS.md at root (always). Source lives in bootstrap/.
  const agentsSrc = path.join(SRC, "bootstrap", "AGENTS.md");
  const agentsResult = copyFile(agentsSrc, path.join(CWD, "AGENTS.md"), args.force);
  log(`  AGENTS.md     ${agentsResult === "written" ? "written" : "skipped (already present — left untouched)"}`);

  // 3. Optional root files. Source name (in bootstrap/) -> destination name (in project root).
  // Note `cursorrules` -> `.cursorrules`: the dot is added at the destination.
  const optional = [
    { src: "CLAUDE.md", dest: "CLAUDE.md", prompt: "Install CLAUDE.md (Claude Code dispatch guard)?", defaultYes: true },
    { src: "cursorrules", dest: ".cursorrules", prompt: "Install .cursorrules (Cursor entry point)?", defaultYes: false },
  ];

  // Only prompt when we have a real interactive terminal. With --yes, or when
  // stdin is not a TTY (piped, CI, scripted), fall back to defaults — interactive
  // prompts on a non-TTY can't be answered reliably.
  const interactive = !args.yes && process.stdin.isTTY;
  let rl = null;
  if (interactive) rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  for (const opt of optional) {
    const src = path.join(SRC, "bootstrap", opt.src);
    if (!fs.existsSync(src)) continue; // not bundled — skip silently
    let wanted = opt.defaultYes;
    if (rl) {
      log("");
      wanted = await ask(rl, opt.prompt, opt.defaultYes);
    }
    if (!wanted) {
      log(`  ${opt.dest}  skipped`);
      continue;
    }
    const r = copyFile(src, path.join(CWD, opt.dest), args.force);
    log(`  ${opt.dest}  ${r === "written" ? "written" : "skipped (already present — left untouched)"}`);
  }
  if (rl) rl.close();

  log("\nDone. Type `mano` in your AI IDE to see available commands, or `mano start` to begin.");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.command) {
    printHelp();
    process.exit(args.help ? 0 : 1);
  }
  if (args.command !== "install") {
    log(`Unknown command: ${args.command}\n`);
    printHelp();
    process.exit(1);
  }
  await install(args);
}

main().catch((err) => {
  log("Error: " + (err && err.message ? err.message : String(err)));
  process.exit(1);
});
