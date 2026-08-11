"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const mode = require("../../src/scripts/mode.js");
const owner = require("../../src/scripts/owner.js");

test("mode parser accepts the documented command shapes", () => {
  assert.deepEqual(mode.parseArgs([]).command, "show");
  assert.equal(mode.parseArgs(["auto"]).command, "auto");
  assert.equal(mode.parseArgs(["set", "manual", "/tmp/project"]).value, "manual");
  assert.equal(mode.parseArgs(["set", "manual", "/tmp/project"]).root, path.resolve("/tmp/project"));
  assert.equal(mode.parseArgs(["--help"]).help, true);
});

test("owner parser separates commands, slugs, and project roots", () => {
  assert.equal(owner.parseArgs([]).command, "show");
  const parsed = owner.parseArgs(["set", "gameplay", "/tmp/project"]);
  assert.equal(parsed.command, "set");
  assert.equal(parsed.slug, "gameplay");
  assert.equal(parsed.root, path.resolve("/tmp/project"));
  assert.equal(owner.parseArgs(["clear", "/tmp/project"]).command, "clear");
  assert.equal(owner.parseArgs(["-h"]).help, true);
});

test("configuration scripts import without executing their command entry points", () => {
  assert.equal(typeof mode.main, "function");
  assert.equal(typeof owner.main, "function");
  assert.equal(typeof mode.runGit, "function");
  assert.equal(typeof owner.runGit, "function");
});
