"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { spawnSync } = require("node:child_process");

const progress = require("../../src/scripts/progress.js");
const { phaseRef } = require("../../src/scripts/phase.js");

const SCRIPT = path.resolve(__dirname, "..", "..", "src", "scripts", "progress.js");
const STATE = path.resolve(__dirname, "..", "..", "src", "scripts", "state.js");

const BRIEF = `# Phase Brief — TaskCLI — Phase 1

## Phase Goal

A person can add, list, and complete tasks from the command line.

## Phase Scope

1. **TaskManager class** — a class backed by a JSON file: create the file if missing, add a task, list tasks, mark one complete.
2. **CLI runner** — a command-line runner exposing \`add\`, \`list\`, and \`done\`.
3. **Unit tests** — creation, completion, and filtering are covered.

## Exit Criteria

1. **Fresh start**
   a. Run \`add "Buy milk"\` with no data file: the file is created and a confirmation is shown
2. **Core interaction**
   a. \`add\`: the task gets a unique id, the given title, and is not completed
   b. \`done <bad-id>\`: it reports the task was not found and nothing changes
`;

function project(brief = BRIEF, phase = 1) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-progress-"));
  const dir = path.join(root, "_mano_output", `phase-${phase}`);
  fs.mkdirSync(dir, { recursive: true });
  if (brief !== null) fs.writeFileSync(path.join(dir, "phase-brief.md"), brief);
  return { root, dir, ledger: path.join(dir, "progress.md") };
}

function run(root, args) {
  return spawnSync("node", [SCRIPT, ...args, root], { encoding: "utf8" });
}

// ---- args -----------------------------------------------------------------

test("progress parser binds each --status to the rows before it that lack one", () => {
  const shared = progress.parseArgs(["set-status", "--row", "S1", "--row", "S2", "--status", "done"]);
  assert.deepEqual(shared.entries.map((e) => [e.row, e.status]), [["S1", "done"], ["S2", "done"]]);

  const paired = progress.parseArgs([
    "set-status", "--row", "S2", "--status", "doing", "--reopen", "--row", "E2c", "--status", "pending", "--reopen",
  ]);
  assert.deepEqual(paired.entries.map((e) => [e.row, e.status, e.reopen]), [
    ["S2", "doing", true], ["E2c", "pending", true],
  ]);
});

test("progress row addresses sort decomposition before lettered corrections", () => {
  const id = (s) => progress.parseRowId(s);
  assert.deepEqual(progress.rowKey(id("S2")), [2, "", 0]);
  assert.equal(progress.keyLess(id("S2"), id("S2.1")), true);
  assert.equal(progress.keyLess(id("S2.1"), id("S2.2")), true);
  assert.equal(progress.keyLess(id("S2.2"), id("S2a")), true);
  assert.equal(progress.keyLess(id("S2a"), id("S3")), true);
  assert.equal(progress.keyLess(id("S10"), id("S3")), false);
  assert.equal(progress.parseRowId("E2.1"), null, "dots are build's decomposition; exit criteria never take one");
  assert.equal(progress.parseRowId("X1"), null);
});

// ---- init parses the brief; nothing composes row text ---------------------

test("init preserves the brief's own numbers and short titles byte for byte", () => {
  const p = project();
  const result = run(p.root, ["init", "--phase", "1"]);
  assert.equal(result.status, 0, result.stderr);
  const text = fs.readFileSync(p.ledger, "utf8");

  assert.match(text, /^# Progress — TaskCLI — Phase 1$/m);
  assert.match(text, /^\| S1 \| TaskManager class \| pending \|$/m);
  assert.match(text, /^\| S2 \| CLI runner \| pending \|$/m);
  assert.match(text, /^\| S3 \| Unit tests \| pending \|$/m);
  // Exit criteria are addressed per leaf, so a category can never hide one.
  assert.match(text, /^\| E1a \| Fresh start — Run `add "Buy milk"` with no data file: the file is created and a confirmation is shown \| pending \|$/m);
  assert.match(text, /^\| E2a \| Core interaction — `add`: the task gets a unique id, the given title, and is not completed \| pending \|$/m);
  assert.match(text, /^\| E2b \| Core interaction — `done <bad-id>`: it reports the task was not found and nothing changes \| pending \|$/m);
  assert.equal(/\| E2c \|/.test(text), false);
});

test("init numbers an unnumbered bullet list in document order and keeps the whole line", () => {
  const p = project(`# Phase Brief — Demo — Phase 1

## Phase Scope

- the store keeps tasks between runs
- the runner exposes add and list

## Exit Criteria

- adding a task shows a confirmation
`);
  assert.equal(run(p.root, ["init", "--phase", "1"]).status, 0);
  const text = fs.readFileSync(p.ledger, "utf8");
  assert.match(text, /^\| S1 \| the store keeps tasks between runs \| pending \|$/m);
  assert.match(text, /^\| S2 \| the runner exposes add and list \| pending \|$/m);
  assert.match(text, /^\| E1 \| adding a task shows a confirmation \| pending \|$/m);
});

test("init letters an older brief's nested exit bullets and folds a third level into the leaf", () => {
  const p = project(`# Phase Brief — Demo — Phase 1

## Phase Scope

1. **Store** — tasks persist

## Exit Criteria

1. Core interaction
   - User submits form:
     - Confirmation message appears
     - Item added to list
   - Invalid input: error shown, no state change
`);
  assert.equal(run(p.root, ["init", "--phase", "1"]).status, 0);
  const text = fs.readFileSync(p.ledger, "utf8");
  // No bolded category lead to borrow, so each leaf stands as its own whole text.
  assert.match(text, /^\| E1a \| User submits form:; Confirmation message appears; Item added to list \| pending \|$/m);
  assert.match(text, /^\| E1b \| Invalid input: error shown, no state change \| pending \|$/m);
});

test("init refuses a prose-only scope rather than inventing the split", () => {
  const p = project(`# Phase Brief — Demo — Phase 1

## Phase Scope

We will build the task store and a small runner around it, then test it.

## Exit Criteria

1. **Fresh start**
   a. it works: a confirmation is shown
`);
  const result = run(p.root, ["init", "--phase", "1"]);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /no list to parse/);
  assert.match(result.stderr, /mano start/);
  assert.equal(fs.existsSync(p.ledger), false, "a refusal writes no ledger");
});

test("init runs once — a second call refuses instead of renumbering a live ledger", () => {
  const p = project();
  assert.equal(run(p.root, ["init", "--phase", "1"]).status, 0);
  run(p.root, ["set-status", "--phase", "1", "--row", "S1", "--status", "done"]);
  const second = run(p.root, ["init", "--phase", "1"]);
  assert.equal(second.status, 1);
  assert.match(second.stderr, /already exists/);
  assert.match(fs.readFileSync(p.ledger, "utf8"), /\| S1 \| TaskManager class \| done \|/);
});

test("init writes the owner into the ledger heading", () => {
  const p = project(BRIEF, 1);
  fs.renameSync(p.dir, path.join(p.root, "_mano_output", "art-phase-1"));
  const result = spawnSync("node", [SCRIPT, "init", "--phase", "1", p.root], {
    encoding: "utf8",
    env: { ...process.env, MANO_OWNER: "art" },
  });
  assert.equal(result.status, 0, result.stderr);
  const ref = phaseRef("art", 1);
  assert.match(fs.readFileSync(path.join(p.root, ref.relativeDir, "progress.md"), "utf8"),
    /^# Progress — TaskCLI — Phase 1 — Owner: art$/m);
});

// ---- status vocabularies --------------------------------------------------

test("set-status enforces the two status vocabularies in both directions", () => {
  const p = project();
  run(p.root, ["init", "--phase", "1"]);

  const met = run(p.root, ["set-status", "--phase", "1", "--row", "S1", "--status", "met"]);
  assert.equal(met.status, 1);
  assert.match(met.stderr, /built is not proven/i);

  const done = run(p.root, ["set-status", "--phase", "1", "--row", "E1a", "--status", "done"]);
  assert.equal(done.status, 1);
  assert.match(done.stderr, /built is not proven/i);

  assert.equal(run(p.root, ["set-status", "--phase", "1", "--row", "E1a", "--status", "met"]).status, 0);
  assert.match(fs.readFileSync(p.ledger, "utf8"), /\| E1a \|.*\| met \|/);
});

test("set-status refuses a backwards move without --reopen and reports one with it", () => {
  const p = project();
  run(p.root, ["init", "--phase", "1"]);
  run(p.root, ["set-status", "--phase", "1", "--row", "S1", "--status", "done"]);

  const silent = run(p.root, ["set-status", "--phase", "1", "--row", "S1", "--status", "doing"]);
  assert.equal(silent.status, 1);
  assert.match(silent.stderr, /--reopen/);
  assert.match(fs.readFileSync(p.ledger, "utf8"), /\| S1 \|.*\| done \|/, "a refusal changes nothing");

  const reopened = run(p.root, ["set-status", "--phase", "1", "--row", "S1", "--status", "doing", "--reopen"]);
  assert.equal(reopened.status, 0);
  assert.match(reopened.stdout, /reopened/);
});

test("set-status validates every row before writing any of them", () => {
  const p = project();
  run(p.root, ["init", "--phase", "1"]);
  const result = run(p.root, [
    "set-status", "--phase", "1", "--row", "S1", "--status", "done", "--row", "S9", "--status", "done",
  ]);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /no row S9/);
  assert.match(fs.readFileSync(p.ledger, "utf8"), /\| S1 \| TaskManager class \| pending \|/);
});

// ---- split ----------------------------------------------------------------

test("split only decomposes the row being built, records its first part done, and closes the parent", () => {
  const p = project();
  run(p.root, ["init", "--phase", "1"]);

  const early = run(p.root, ["split", "--phase", "1", "--row", "S2", "--part", "a", "--part", "b"]);
  assert.equal(early.status, 1, "a pending row cannot be pre-decomposed");
  assert.match(early.stderr, /only the row currently being built/);

  run(p.root, ["set-status", "--phase", "1", "--row", "S2", "--status", "doing"]);
  assert.equal(run(p.root, [
    "split", "--phase", "1", "--row", "S2", "--part", "add + wiring", "--part", "list + done",
  ]).status, 0);
  let text = fs.readFileSync(p.ledger, "utf8");
  assert.match(text, /^\| S2\.1 \| add \+ wiring \| done \|$/m);
  assert.match(text, /^\| S2\.2 \| list \+ done \| pending \|$/m);

  const early2 = run(p.root, ["set-status", "--phase", "1", "--row", "S2", "--status", "done"]);
  assert.equal(early2.status, 1);
  assert.match(early2.stderr, /sub-rows that are not done/);

  const finish = run(p.root, ["set-status", "--phase", "1", "--row", "S2.2", "--status", "done"]);
  assert.equal(finish.status, 0, finish.stderr);
  text = fs.readFileSync(p.ledger, "utf8");
  assert.match(text, /^\| S2 \| CLI runner \| done \|$/m, "a completed split completes its parent");

  assert.equal(run(p.root, ["split", "--phase", "1", "--row", "E1a", "--part", "x"]).status, 1);
});

// ---- add-row --------------------------------------------------------------

test("add-row appends a lettered correction verbatim and refuses new top-level scope", () => {
  const p = project();
  run(p.root, ["init", "--phase", "1"]);
  const words = "the done command should say which id it could not find";
  assert.equal(run(p.root, ["add-row", "--phase", "1", "--row", "S2a", "--text", words]).status, 0);

  const text = fs.readFileSync(p.ledger, "utf8");
  assert.ok(text.includes(`| S2a | ${words} | pending |`), "the row carries the user's own words");
  const lines = text.split("\n").filter((l) => /^\| S[0-9]/.test(l)).map((l) => l.split("|")[1].trim());
  assert.deepEqual(lines, ["S1", "S2", "S2a", "S3"], "a correction sorts under the item it corrects");

  assert.equal(run(p.root, ["add-row", "--phase", "1", "--row", "S2a", "--text", "again"]).status, 1);
  const invented = run(p.root, ["add-row", "--phase", "1", "--row", "S9a", "--text", "dark mode"]);
  assert.equal(invented.status, 1);
  assert.match(invented.stderr, /mano start/);
  const unlettered = run(p.root, ["add-row", "--phase", "1", "--row", "S4", "--text", "dark mode"]);
  assert.equal(unlettered.status, 1);
  assert.match(unlettered.stderr, /new top-level item is new scope/);

  assert.equal(run(p.root, ["add-row", "--phase", "1", "--row", "E2c", "--text", "the id is named in the error"]).status, 0);
  assert.match(fs.readFileSync(p.ledger, "utf8"), /^\| E2c \| the id is named in the error \| pending \|$/m);
});

// ---- round-trip with state.js ---------------------------------------------

test("the ledger progress.js writes is the ledger state.js reads back", () => {
  const p = project();
  run(p.root, ["init", "--phase", "1"]);
  run(p.root, ["set-status", "--phase", "1", "--row", "S1", "--status", "done"]);
  run(p.root, ["set-status", "--phase", "1", "--row", "E1a", "--status", "met"]);

  const projected = spawnSync("node", [STATE, "--next", p.root], { encoding: "utf8" });
  assert.equal(projected.status, 0, projected.stderr);
  assert.match(projected.stdout, /PROGRESS: _mano_output\/phase-1\/progress\.md/);
  assert.match(projected.stdout, /SCOPE: 1\/3 done/);
  assert.match(projected.stdout, /EXIT_CRITERIA: 1\/3 met/);
  assert.match(projected.stdout, /ROW: S2/);
});
