"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

test("installed scripts run in an ESM host, including upgrades from an unscoped install", t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-esm-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const manifest = '{"type":"module"}\n';
  fs.writeFileSync(path.join(root, "package.json"), manifest);
  const env = { ...process.env };
  delete env.MANO_OWNER;
  const run = (...args) => {
    const result = spawnSync(process.execPath, args, {
      cwd: root, encoding: "utf8", env,
    });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    return result.stdout;
  };
  const install = () => run(path.resolve(__dirname, "../bin/mano-plan.js"), "install", "--yes");
  const verify = () => {
    assert.deepEqual(JSON.parse(run("_mano/scripts/settings.js", "language")), {
      language: { chat: null, build: null, artefacts: null },
    });
    assert.match(run("_mano/scripts/state.js", "--current"), /STATUS: NO_PHASE/);
    assert.equal(fs.readFileSync(path.join(root, "package.json"), "utf8"), manifest);
  };
  install();
  verify();
  fs.unlinkSync(path.join(root, "_mano/scripts/package.json"));
  install();
  verify();
});
