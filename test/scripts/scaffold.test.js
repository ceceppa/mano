"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const scaffold = require("../../src/scripts/scaffold.js");

function fixtureRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "mano-scaffold-unit-"));
}

test("scaffold parser requires a command separator and captures options", () => {
  assert.throws(() => scaffold.parseArgs(["run"]), /missing -- before/);
  assert.deepEqual(scaffold.parseArgs(["run", "--project-root", "/tmp/project", "--name", "demo", "--keep-stage", "--", "tool", "{target}"]), {
    help: false,
    action: "run",
    projectRoot: "/tmp/project",
    name: "demo",
    keepStage: true,
    command: ["tool", "{target}"],
  });
});

test("scaffold validates a single safe staging directory name", () => {
  assert.equal(scaffold.validateName("demo-app"), "demo-app");
  for (const value of ("", ".", "..", "nested/app", "nested\\app", "\0")) {
    assert.throws(() => scaffold.validateName(value), /invalid staging name/);
  }
});

test("scaffold tree collection rejects Mano-owned paths before a merge", () => {
  const root = fixtureRoot();
  try {
    fs.mkdirSync(path.join(root, "_mano"));
    assert.throws(() => scaffold.collectTree(root), /reserved path/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("scaffold preflight, merge, and verify preserve identical files and add only missing ones", () => {
  const root = fixtureRoot();
  const source = path.join(root, "source");
  const project = path.join(root, "project");
  fs.mkdirSync(path.join(source, "src"), { recursive: true });
  fs.mkdirSync(project);
  fs.writeFileSync(path.join(source, "README.md"), "same\n");
  fs.writeFileSync(path.join(source, "src", "index.js"), "export {};\n");
  fs.writeFileSync(path.join(project, "README.md"), "same\n");
  try {
    const entries = scaffold.collectTree(source);
    const checked = scaffold.preflight(entries, project);
    assert.deepEqual(checked, { conflicts: [], identicalFiles: 1 });
    assert.equal(scaffold.merge(entries), 1);
    assert.doesNotThrow(() => scaffold.verify(entries));
    assert.equal(fs.readFileSync(path.join(project, "src", "index.js"), "utf8"), "export {};\n");
    assert.equal(scaffold.filesEqual(path.join(source, "README.md"), path.join(project, "README.md")), true);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("scaffold preflight detects conflicting file contents without merging", () => {
  const root = fixtureRoot();
  const source = path.join(root, "source");
  const project = path.join(root, "project");
  fs.mkdirSync(source);
  fs.mkdirSync(project);
  fs.writeFileSync(path.join(source, "README.md"), "generated\n");
  fs.writeFileSync(path.join(project, "README.md"), "existing\n");
  try {
    const checked = scaffold.preflight(scaffold.collectTree(source), project);
    assert.deepEqual(checked, { conflicts: ["README.md"], identicalFiles: 0 });
    assert.equal(fs.readFileSync(path.join(project, "README.md"), "utf8"), "existing\n");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
