#!/usr/bin/env node
"use strict";

/** Store approved remaining actions and explicit skips in local Git config.
 * Artifact existence cannot reconstruct approval order or human additions.
 */

const path = require("node:path");
const fs = require("node:fs");
const childProcess = require("node:child_process");
const { parsePhaseDirName, resolveConfiguredMode } = require("./phase.js");

// The planning actions a chain can contain, and therefore the only ones a human
// can remove from one. Implementation is the chain's terminal action and is
// never skippable — a chain that stops before implementation is a chain that
// did nothing. `review` is never in a chain at all.
const SKIPPABLE = ["spec", "ux", "rules", "ui", "stories"];
const REPAIRABLE = ["spec", "ux", "rules", "ui"];

const HELP = `mano chain — persist approved remaining actions and explicit skips

Usage:
  node chain.js show [--phase <phase-id>] [projectRoot]
  node chain.js save --phase <phase-id> --actions <ordered-actions> [projectRoot]
  node chain.js repair --phase <phase-id> --actions <spec|ux|rules|ui> [projectRoot]
  node chain.js skip --phase <phase-id> --actions <a,b,...> [projectRoot]
  node chain.js clear --phase <phase-id> [projectRoot]

save     persist approved remaining actions in order; an empty string marks completion.
repair   insert one artifact owner before pending build in auto, before either
         ledger exists. Each owner gets one automatic attempt per approved run.
skip     record that the human removed these actions when they approved the
         scope. Only ${SKIPPABLE.join(", ")} may be skipped; implementation is a
         chain's terminal action and is never optional.
show     print the saved run and skips for one phase, or skips for every phase.
clear    forget skips and repair attempts on fresh scope approval; retain actions.

Approved remaining actions are stored separately as mano.run.<phase-id>.
Missing run records require recovering approval from chat or asking the human.
It is stored in local Git config as mano.chain.<phase-id> and is not committed.`;

function fail(message) {
  process.stderr.write(`[mano chain] ${message}\n`);
  process.exit(1);
}

function parseArgs(argv) {
  const args = {
    help: argv.includes("--help") || argv.includes("-h"),
    command: null,
    phase: null,
    actions: null,
    root: null,
  };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") continue;
    else if (a === "--phase") args.phase = argv[++i];
    else if (a === "--actions") args.actions = argv[++i];
    else positional.push(a);
  }
  args.command = positional[0] || "show";
  args.root = path.resolve(positional[1] || process.cwd());
  return args;
}

function runGit(root, gitArgs, allowMissing = false) {
  const result = childProcess.spawnSync("git", gitArgs, { cwd: root, encoding: "utf8" });
  if (result.status === 0) return result;
  // 1 is "key not found" on --get, 5 is "no such section" on --unset.
  if (allowMissing && (result.status === 1 || result.status === 5)) return result;
  const detail = String(result.stderr || result.stdout || "git command failed").trim();
  fail(`${detail}. Chain records require a Git checkout.`);
}

function validatePhaseId(value) {
  const id = String(value == null ? "" : value).trim();
  if (!id) fail("--phase needs a phase id, e.g. phase-3 or alice-phase-3");
  if (!parsePhaseDirName(id)) {
    fail(`${JSON.stringify(id)} is not a phase id; use the exact PHASE_ID from the state projection`);
  }
  return id;
}

function validateActions(value) {
  const raw = String(value == null ? "" : value)
    .split(",")
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
  if (!raw.length) fail(`--actions needs at least one of: ${SKIPPABLE.join(", ")}`);
  const seen = [];
  for (const action of raw) {
    if (!SKIPPABLE.includes(action)) {
      fail(
        `${JSON.stringify(action)} cannot be skipped; a chain's terminal action is implementation. ` +
          `Skippable: ${SKIPPABLE.join(", ")}`,
      );
    }
    if (!seen.includes(action)) seen.push(action);
  }
  // Stored in the chain's own order, not the order they were typed, so `show`
  // reads the same for the same set.
  return SKIPPABLE.filter((action) => seen.includes(action));
}

/** Read one phase's recorded skips. Returns [] when nothing is recorded. */
function readSkipped(root, phaseId) {
  const result = childProcess.spawnSync(
    "git",
    ["config", "--local", "--get", `mano.chain.${phaseId}`],
    { cwd: root, encoding: "utf8" },
  );
  if (result.status !== 0) return [];
  return String(result.stdout || "")
    .trim()
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

/** null means no saved approval; actions: [] means the run completed. */
function readRun(root, phaseId) {
  const result = childProcess.spawnSync("git",
    ["config", "--local", "--get", `mano.run.${phaseId}`],
    { cwd: root, encoding: "utf8" });
  if (result.status === 1) return null;
  if (result.status !== 0) throw new Error("Unable to read approved chain record");
  const value = JSON.parse(result.stdout);
  // Existing array records remain readable; new records keep the retry budget
  // in the same atomic Git config write as the inserted action.
  const run = Array.isArray(value) ? { actions: value, repairs: [] } : value;
  if (!run || !Array.isArray(run.repairs) ||
      run.repairs.some(a => !REPAIRABLE.includes(a)) ||
      new Set(run.repairs).size !== run.repairs.length) {
    throw new Error("Invalid chain repair record");
  }
  validateRemaining(run.actions);
  return run;
}

function readRemaining(root, phaseId) {
  return readRun(root, phaseId)?.actions ?? null;
}

function writeRun(root, phaseId, run) {
  runGit(root, ["config", "--local", `mano.run.${phaseId}`, JSON.stringify(run)]);
}

function validateRemaining(actions) {
  if (!Array.isArray(actions) || actions.some(a => ![...SKIPPABLE, "build", "dev"].includes(a)) ||
      new Set(actions).size !== actions.length ||
      (actions.length && !["build", "dev"].includes(actions.at(-1))) ||
      actions.slice(0, -1).some(a => ["build", "dev"].includes(a))) {
    throw new Error("Remaining actions must be unique planning actions followed by build or dev, or empty after completion");
  }
}

/** Every phase with a record, as { phaseId, skipped } rows. */
function readAll(root) {
  const result = childProcess.spawnSync(
    "git",
    ["config", "--local", "--get-regexp", "^mano\\.chain\\."],
    { cwd: root, encoding: "utf8" },
  );
  if (result.status !== 0) return [];
  const rows = [];
  for (const line of String(result.stdout || "").split("\n")) {
    const match = /^mano\.chain\.(\S+)\s+(.*)$/.exec(line.trim());
    if (!match) continue;
    const skipped = match[2].split(",").map((p) => p.trim()).filter(Boolean);
    if (skipped.length) rows.push({ phaseId: match[1], skipped });
  }
  return rows;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(HELP + "\n");
    return;
  }
  if (!["show", "skip", "save", "repair", "clear"].includes(args.command)) {
    fail(`unknown command ${JSON.stringify(args.command)}; use show, save, repair, skip, or clear`);
  }

  if (args.command === "repair") {
    const phaseId = validatePhaseId(args.phase);
    const action = args.actions;
    if (!REPAIRABLE.includes(action)) fail("repair requires exactly one of spec, ux, rules, ui");
    if (resolveConfiguredMode(args.root).mode !== "auto") fail("repair requires auto mode");
    const phaseDir = path.join(args.root, "_mano_output", phaseId);
    if (!fs.existsSync(path.join(phaseDir, "phase-brief.md")) ||
        fs.existsSync(path.join(phaseDir, "progress.md")) ||
        fs.existsSync(path.join(phaseDir, "stories", "README.md"))) {
      fail("repair requires a phase brief and neither implementation ledger");
    }
    const run = readRun(args.root, phaseId);
    if (!run || run.actions.length !== 1 || run.actions[0] !== "build") {
      fail("repair requires an approved run with only build remaining");
    }
    if (readSkipped(args.root, phaseId).includes(action)) fail(`${action} was explicitly skipped`);
    if (run.repairs.includes(action)) fail(`${action} automatic repair already attempted; ask the human`);
    writeRun(args.root, phaseId, { actions: [action, "build"], repairs: [...run.repairs, action] });
    process.stdout.write(`[mano chain] ${phaseId} — repair: ${action}; remaining: ${action}, build\n`);
    return;
  }

  if (args.command === "save") {
    const phaseId = validatePhaseId(args.phase);
    if (args.actions == null) fail("save requires --actions (empty after completion)");
    const actions = args.actions === "" ? [] : args.actions.split(",").map(a => a.trim());
    validateRemaining(actions);
    const previous = readRun(args.root, phaseId);
    writeRun(args.root, phaseId, { actions, repairs: previous?.repairs ?? [] });
    process.stdout.write(`[mano chain] ${phaseId} — remaining: ${actions.join(", ") || "none (completed)"}\n`);
    return;
  }

  if (args.command === "skip") {
    const phaseId = validatePhaseId(args.phase);
    const actions = validateActions(args.actions);
    runGit(args.root, ["rev-parse", "--git-dir"]);
    runGit(args.root, ["config", "--local", `mano.chain.${phaseId}`, actions.join(",")]);
    process.stdout.write(`[mano chain] ${phaseId} — skipped: ${actions.join(", ")}\n`);
    process.stdout.write("  Recorded so a later session does not re-propose them. Not committed.\n");
    return;
  }

  if (args.command === "clear") {
    const phaseId = validatePhaseId(args.phase);
    runGit(args.root, ["rev-parse", "--git-dir"]);
    const run = readRun(args.root, phaseId);
    if (run) writeRun(args.root, phaseId, { actions: run.actions, repairs: [] });
    runGit(args.root, ["config", "--local", "--unset-all", `mano.chain.${phaseId}`], true);
    process.stdout.write(`[mano chain] ${phaseId} — record cleared\n`);
    return;
  }

  runGit(args.root, ["rev-parse", "--git-dir"]);
  if (args.phase) {
    const phaseId = validatePhaseId(args.phase);
    const run = readRun(args.root, phaseId);
    const remaining = run?.actions ?? null;
    if (remaining !== null) process.stdout.write(`CHAIN_REMAINING: ${remaining.join(", ") || "none (completed)"}\n`);
    const repairs = run?.repairs ?? [];
    process.stdout.write(`CHAIN_REPAIRS: ${repairs.join(", ") || "none"}\n`);
    const skipped = readSkipped(args.root, phaseId);
    process.stdout.write(
      skipped.length
        ? `[mano chain] ${phaseId} — skipped: ${skipped.join(", ")}\n`
        : `[mano chain] ${phaseId} — no skip record; recover approved actions from the saved run or chat\n`,
    );
    return;
  }
  const rows = readAll(args.root);
  if (!rows.length) {
    process.stdout.write("[mano chain] no skip records; use show --phase to read an approved run\n");
    return;
  }
  for (const row of rows) {
    process.stdout.write(`[mano chain] ${row.phaseId} — skipped: ${row.skipped.join(", ")}\n`);
  }
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    fail(error && error.message ? error.message : String(error));
  }
}

module.exports = { SKIPPABLE, parseArgs, readSkipped, readAll, readRun, readRemaining, validateRemaining, validateActions, main };
