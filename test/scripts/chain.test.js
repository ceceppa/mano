"use strict";

const assert = require("node:assert/strict");
const childProcess = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const chain = require("../../src/scripts/chain.js");

const SCRIPT = path.join(__dirname, "..", "..", "src", "scripts", "chain.js");

function gitProject(prefix) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  childProcess.spawnSync("git", ["init", "-q"], { cwd: root });
  return root;
}

function run(root, args) {
  return childProcess.spawnSync("node", [SCRIPT, ...args, root], {
    cwd: root,
    encoding: "utf8",
  });
}

test("chain parser separates commands, flags, and project roots", () => {
  assert.equal(chain.parseArgs([]).command, "show");
  const parsed = chain.parseArgs(["skip", "--phase", "phase-3", "--actions", "ux,ui", "/tmp/project"]);
  assert.equal(parsed.command, "skip");
  assert.equal(parsed.phase, "phase-3");
  assert.equal(parsed.actions, "ux,ui");
  assert.equal(parsed.root, path.resolve("/tmp/project"));
  assert.equal(chain.parseArgs(["--help"]).help, true);
});

test("skippable actions are the planning ones, normalised to chain order", () => {
  assert.deepEqual(chain.validateActions("ui,ux"), ["ux", "ui"]);
  assert.deepEqual(chain.validateActions(" UX , ux "), ["ux"]);
  assert.deepEqual(chain.SKIPPABLE, ["spec", "ux", "rules", "ui", "stories"]);
});

test("a recorded skip round-trips, and clearing forgets it", () => {
  const root = gitProject("mano-chain-roundtrip-");
  assert.deepEqual(chain.readSkipped(root, "phase-3"), []);

  const written = run(root, ["skip", "--phase", "phase-3", "--actions", "ui,ux"]);
  assert.equal(written.status, 0, written.stderr);
  assert.match(written.stdout, /phase-3 — skipped: ux, ui/);
  assert.deepEqual(chain.readSkipped(root, "phase-3"), ["ux", "ui"]);

  // Owner-namespaced ids are phase ids too, and stay independent.
  run(root, ["skip", "--phase", "alice-phase-3", "--actions", "spec"]);
  assert.deepEqual(chain.readSkipped(root, "alice-phase-3"), ["spec"]);
  assert.deepEqual(chain.readSkipped(root, "phase-3"), ["ux", "ui"]);
  assert.equal(chain.readAll(root).length, 2);

  const cleared = run(root, ["clear", "--phase", "phase-3"]);
  assert.equal(cleared.status, 0, cleared.stderr);
  assert.deepEqual(chain.readSkipped(root, "phase-3"), []);
  assert.deepEqual(chain.readSkipped(root, "alice-phase-3"), ["spec"]);
});

test("implementation is a chain's terminal action and can never be skipped", () => {
  const root = gitProject("mano-chain-refusal-");
  for (const action of ["build", "dev", "review", "start"]) {
    const result = run(root, ["skip", "--phase", "phase-1", "--actions", action]);
    assert.equal(result.status, 1, `${action} should be refused`);
    assert.match(result.stderr, /cannot be skipped/);
  }
  // A refused write leaves no partial record behind.
  assert.deepEqual(chain.readSkipped(root, "phase-1"), []);
});

test("a phase id that is not one is refused rather than stored", () => {
  const root = gitProject("mano-chain-phase-id-");
  const result = run(root, ["skip", "--phase", "22", "--actions", "ux"]);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /is not a phase id/);
  assert.deepEqual(chain.readAll(root), []);
});

test("missing records do not invent approval", () => {
  const root = gitProject("mano-chain-empty-");
  const shown = run(root, ["show", "--phase", "phase-1"]);
  assert.equal(shown.status, 0, shown.stderr);
  assert.match(shown.stdout, /no skip record; recover approved actions/);

  const all = run(root, ["show"]);
  assert.equal(all.status, 0, all.stderr);
  assert.match(all.stdout, /no skip records/);
});


test("approved order survives sessions and completion differs from missing approval", () => {
  const root = gitProject("mano-chain-plan-");
  assert.equal(chain.readRemaining(root, "phase-1"), null);
  assert.equal(run(root, ["save", "--phase", "phase-1", "--actions", "rules,spec,ui,build"]).status, 0);
  assert.deepEqual(chain.readRemaining(root, "phase-1"), ["rules", "spec", "ui", "build"]);
  assert.equal(chain.readRemaining(root, "alice-phase-1"), null);
  assert.equal(run(root, ["save", "--phase", "phase-1", "--actions", "ui,build"]).status, 0);
  assert.deepEqual(chain.readRemaining(root, "phase-1"), ["ui", "build"]);
  for (const actions of ["review", "build,ui", "spec,spec,build", "start,build"]) {
    assert.equal(run(root, ["save", "--phase", "phase-1", "--actions", actions]).status, 1);
    assert.deepEqual(chain.readRemaining(root, "phase-1"), ["ui", "build"]);
  }
  assert.equal(run(root, ["save", "--phase", "phase-1", "--actions", ""]).status, 0);
  assert.deepEqual(chain.readRemaining(root, "phase-1"), []);
});

function repairProject() {
  const root = gitProject("mano-chain-repair-");
  childProcess.spawnSync("git", ["config", "mano.mode", "auto"], { cwd: root });
  const dir = path.join(root, "_mano_output", "phase-1");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "phase-brief.md"), "# Approved phase\n");
  run(root, ["save", "--phase", "phase-1", "--actions", "build"]);
  return { root, dir };
}

function repair(root, action) {
  return run(root, ["repair", "--phase", "phase-1", "--actions", action]);
}

test("each artifact owner can be inserted once, with durable attempts across saves", () => {
  const { root } = repairProject();
  for (const owner of ["spec", "ux", "ui", "rules"]) {
    const result = repair(root, owner);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(chain.readRemaining(root, "phase-1"), [owner, "build"]);
    assert.ok(chain.readRun(root, "phase-1").repairs.includes(owner));
    run(root, ["save", "--phase", "phase-1", "--actions", "build"]);
    const before = chain.readRun(root, "phase-1");
    assert.match(repair(root, owner).stderr, /already attempted/);
    assert.deepEqual(chain.readRun(root, "phase-1"), before);
  }
  assert.match(run(root, ["show", "--phase", "phase-1"]).stdout,
    /CHAIN_REPAIRS: spec, ux, ui, rules/);
  run(root, ["save", "--phase", "phase-1", "--actions", ""]);
  assert.equal(repair(root, "spec").status, 1);
  assert.equal(chain.readRun(root, "phase-1").repairs.length, 4);
});

test("repair refusals preserve both the plan and retry budget", () => {
  const scenarios = [
    ["explicit skip", ({ root }) => run(root, ["skip", "--phase", "phase-1", "--actions", "spec"])],
    ["manual mode", ({ root }) => require("../../src/scripts/settings.js").writeSetting(root, "mode", "manual")],
    ["missing brief", ({ dir }) => fs.unlinkSync(path.join(dir, "phase-brief.md"))],
    ["build ledger", ({ dir }) => fs.writeFileSync(path.join(dir, "progress.md"), "invalid also blocks")],
    ["stories ledger", ({ dir }) => {
      fs.mkdirSync(path.join(dir, "stories"));
      fs.writeFileSync(path.join(dir, "stories", "README.md"), "ledger");
    }],
    ["remaining planning", ({ root }) => run(root, ["save", "--phase", "phase-1", "--actions", "ui,build"])],
    ["missing approval", ({ root }) => require("../../src/scripts/settings.js").writePhase(root, "phase-1", { run: null })],
    ["completed run", ({ root }) => run(root, ["save", "--phase", "phase-1", "--actions", ""])],
  ];
  for (const [name, setup] of scenarios) {
    const project = repairProject();
    setup(project);
    const before = chain.readRun(project.root, "phase-1");
    assert.equal(repair(project.root, "spec").status, 1, name);
    assert.deepEqual(chain.readRun(project.root, "phase-1"), before, name);
  }
  const { root } = repairProject();
  for (const owner of ["stories", "build", "dev", "review", "start", "spec,ux"]) {
    assert.equal(repair(root, owner).status, 1, owner);
    assert.deepEqual(chain.readRun(root, "phase-1"), { actions: ["build"], repairs: [] });
  }
});

test("legacy plans support repair and fresh approval clears attempts without losing actions", () => {
  const { root } = repairProject();
  childProcess.spawnSync("git", ["config", "mano.run.phase-1", '["build"]'], { cwd: root });
  assert.equal(repair(root, "spec").status, 0);
  assert.equal(chain.readRun(root, "alice-phase-1"), null);
  run(root, ["clear", "--phase", "phase-1"]);
  assert.deepEqual(chain.readRun(root, "phase-1"), { actions: ["spec", "build"], repairs: [] });
});
