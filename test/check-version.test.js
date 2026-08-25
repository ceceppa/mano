"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const REPO_ROOT = path.resolve(__dirname, "..");
const SCRIPT = path.join(REPO_ROOT, "tools", "check-version.js");

function run(args = []) {
  return spawnSync(process.execPath, [SCRIPT, ...args], { encoding: "utf8" });
}

test("src/VERSION matches package.json", () => {
  const result = run();
  assert.strictEqual(
    result.status,
    0,
    `check-version failed:\n${result.stderr || result.stdout}`,
  );
});

test("the installer ships VERSION into _mano/", () => {
  const installer = fs.readFileSync(path.join(REPO_ROOT, "bin", "mano-plan.js"), "utf8");
  const match = /const MANO_FILES = \[(.*?)\];/s.exec(installer);
  assert.ok(match, "MANO_FILES not found in bin/mano-plan.js");
  assert.match(
    match[1],
    /"VERSION"/,
    "VERSION is not in MANO_FILES, so an install would ship no _mano/VERSION",
  );
});

test("the guard fails on drift rather than passing quietly", (t) => {
  const versionFile = path.join(REPO_ROOT, "src", "VERSION");
  const original = fs.readFileSync(versionFile, "utf8");
  t.after(() => fs.writeFileSync(versionFile, original));

  fs.writeFileSync(versionFile, "0.0.1\n");
  const drift = run();
  assert.strictEqual(drift.status, 1, "a mismatched VERSION passed the guard");
  assert.match(drift.stderr, /says 0\.0\.1/);

  // Prose, a heading, or a label is drift the naive `trim() === version` check
  // would let through on the day someone "documents" the file.
  fs.writeFileSync(versionFile, `# Mano\n${original}`);
  const prose = run();
  assert.strictEqual(prose.status, 1, "a VERSION file holding prose passed the guard");

  // Trailing whitespace reads fine to a human and breaks a naive reader.
  fs.writeFileSync(versionFile, `${original.trim()}  \n`);
  const padded = run();
  assert.strictEqual(padded.status, 1, "a padded VERSION passed the guard");
});

test("--fix restores sync", (t) => {
  const versionFile = path.join(REPO_ROOT, "src", "VERSION");
  const original = fs.readFileSync(versionFile, "utf8");
  t.after(() => fs.writeFileSync(versionFile, original));

  fs.writeFileSync(versionFile, "0.0.1\n");
  assert.strictEqual(run(["--fix"]).status, 0);

  const expected = JSON.parse(
    fs.readFileSync(path.join(REPO_ROOT, "package.json"), "utf8"),
  ).version;
  assert.strictEqual(fs.readFileSync(versionFile, "utf8"), `${expected}\n`);
  assert.strictEqual(run().status, 0);
});
