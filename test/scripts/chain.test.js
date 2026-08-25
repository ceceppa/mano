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

test("no record is the normal case and reads as derived, not as an error", () => {
  const root = gitProject("mano-chain-empty-");
  const shown = run(root, ["show", "--phase", "phase-1"]);
  assert.equal(shown.status, 0, shown.stderr);
  assert.match(shown.stdout, /no record; the chain is derived from what exists on disk/);

  const all = run(root, ["show"]);
  assert.equal(all.status, 0, all.stderr);
  assert.match(all.stdout, /no records/);
});
