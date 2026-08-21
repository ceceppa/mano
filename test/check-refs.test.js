"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("node:child_process");
const path = require("node:path");

const SCRIPT = path.resolve(__dirname, "..", "eval", "check-refs.js");

test("every cross-file section pointer in src/ resolves", () => {
  const result = spawnSync(process.execPath, [SCRIPT], { encoding: "utf8" });
  assert.strictEqual(
    result.status,
    0,
    `check-refs failed:\n${result.stderr || result.stdout}`,
  );
});
