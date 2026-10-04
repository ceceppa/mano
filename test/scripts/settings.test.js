"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const settings = require("../../src/scripts/settings.js");
const chain = require("../../src/scripts/chain.js");
const phase = require("../../src/scripts/phase.js");
function project(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-settings-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}
function git(root, ...args) {
  const result = spawnSync("git", args, { cwd: root, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}
function command(root, script, ...args) {
  const result = spawnSync(process.execPath, [path.resolve(`src/scripts/${script}.js`), ...args, root], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
}

test("owner settings and chain resume from a committed clone, excluding local selection", t => {
  const root = project(t), copy = project(t);
  git(root, "init", "-q");
  command(root, "owner", "set", "alice");
  command(root, "mode", "set", "auto");
  command(root, "track", "set", "Option B");
  const brief = path.join(root, "_mano_output/alice-phase-1");
  fs.mkdirSync(brief);
  fs.writeFileSync(path.join(brief, "phase-brief.md"), "# Approved phase\n");
  command(root, "chain", "save", "--phase", "alice-phase-1", "--actions", "build");
  command(root, "chain", "skip", "--phase", "alice-phase-1", "--actions", "ux");
  command(root, "chain", "repair", "--phase", "alice-phase-1", "--actions", "spec");
  git(root, "add", "_mano_output");
  git(root, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "Save chain");
  git(copy, "clone", "-q", root, ".");
  assert.equal(fs.existsSync(path.join(copy, "_mano_output/.local.json")), false);
  command(copy, "owner", "set", "alice");
  assert.equal(phase.resolveConfiguredMode(copy).mode, "auto");
  assert.equal(phase.resolveConfiguredTrack(copy).track, "Option B");
  assert.deepEqual(chain.readRun(copy, "alice-phase-1"), { actions: ["spec", "build"], repairs: ["spec"] });
  assert.deepEqual(chain.readSkipped(copy, "alice-phase-1"), ["ux"]);
  assert.match(command(copy, "state", "--current"), /OWNER: alice/);
  assert.equal(git(copy, "status", "--porcelain"), "");
  assert.equal(spawnSync("git", ["config", "--local", "--get-regexp", "^mano\\."], { cwd: copy }).status, 1);
});

test("automatic migration preserves legacy owners and does not resurrect cleared state", t => {
  const root = project(t);
  git(root, "init", "-q");
  for (const [key, value] of Object.entries({ owner: "alice", mode: "auto", track: "Old track", "chain.alice-phase-1": "ui", "run.alice-phase-1": '["build"]', "run.bob-phase-2": '{"actions":[],"repairs":[]}' })) git(root, "config", `mano.${key}`, value);
  assert.equal(phase.resolveConfiguredOwner(root).owner, "alice");
  assert.equal(phase.resolveConfiguredMode(root).mode, "auto");
  assert.deepEqual(chain.readRemaining(root, "alice-phase-1"), ["build"]);
  assert.deepEqual(chain.readRemaining(root, "bob-phase-2"), []);
  command(root, "mode", "clear");
  command(root, "track", "clear");
  command(root, "chain", "clear", "--phase", "alice-phase-1");
  command(root, "chain", "save", "--phase", "alice-phase-1", "--actions", "");
  assert.equal(phase.resolveConfiguredMode(root).mode, "manual");
  assert.equal(phase.resolveConfiguredTrack(root).track, null);
  assert.deepEqual(chain.readSkipped(root, "alice-phase-1"), []);
  assert.deepEqual(chain.readRemaining(root, "alice-phase-1"), []);
  command(root, "owner", "clear");
  assert.equal(phase.resolveConfiguredOwner(root).owner, null);
  assert.equal(git(root, "config", "mano.owner"), "alice");
});

test("settings work without Git and owners keep separate preferences and phase records", t => {
  const root = project(t);
  command(root, "mode", "set", "auto");
  command(root, "chain", "save", "--phase", "phase-1", "--actions", "build");
  command(root, "owner", "set", "alice");
  assert.equal(phase.resolveConfiguredMode(root).mode, "manual");
  command(root, "track", "set", "Alice work");
  command(root, "owner", "set", "bob");
  assert.equal(phase.resolveConfiguredTrack(root).track, null);
  command(root, "owner", "set", "alice");
  assert.equal(phase.resolveConfiguredTrack(root).track, "Alice work");
  command(root, "owner", "clear");
  assert.equal(phase.resolveConfiguredMode(root).mode, "auto");
  assert.deepEqual(chain.readRemaining(root, "phase-1"), ["build"]);
});

test("environment overrides remain transient and invalid JSON is never overwritten", t => {
  const root = project(t);
  command(root, "owner", "set", "alice");
  const file = path.join(root, "_mano_output/alice.json");
  const before = fs.readFileSync(file, "utf8");
  const result = spawnSync(process.execPath, [path.resolve("src/scripts/mode.js"), "show", root], { encoding: "utf8", env: { ...process.env, MANO_MODE: "auto" } });
  assert.match(result.stdout, /auto \(MANO_MODE\)/);
  assert.equal(fs.readFileSync(file, "utf8"), before);
  fs.writeFileSync(file, "<<<<<<< conflict\n");
  assert.throws(() => settings.writeSetting(root, "mode", "auto"), /Invalid Mano settings/);
  assert.equal(fs.readFileSync(file, "utf8"), "<<<<<<< conflict\n");
  assert.throws(() => settings.selectOwner(root, "../escape"), /invalid Mano owner/);
});

test("migration fills missing records without replacing existing JSON preferences or completed runs", t => {
  const root = project(t);
  git(root, "init", "-q");
  command(root, "owner", "set", "alice");
  command(root, "chain", "save", "--phase", "alice-phase-1", "--actions", "");
  git(root, "config", "mano.owner", "alice");
  git(root, "config", "mano.mode", "auto");
  git(root, "config", "mano.run.alice-phase-1", '["build"]');
  git(root, "config", "mano.run.alice-phase-2", '["ui","build"]');
  assert.equal(phase.resolveConfiguredMode(root).mode, "manual");
  assert.equal(chain.readRemaining(root, "alice-phase-1"), null);
  assert.deepEqual(chain.readRemaining(root, "alice-phase-2"), ["ui", "build"]);
});


test("only the newest phase survives writes and JSON migration", t => {
  const root = project(t);
  settings.writePhase(root, "phase-9", { skipped: ["ui"], run: [] });
  settings.writePhase(root, "phase-10", { run: { actions: ["build"], repairs: ["spec"] } });
  assert.equal(chain.readRemaining(root, "phase-9"), null);
  assert.throws(() => settings.writePhase(root, "phase-9", { skipped: [] }), /older phase/);
  const file = path.join(root, "_mano_output/.default.json");
  const data = JSON.parse(fs.readFileSync(file));
  data.phases["phase-2"] = { skipped: [], run: [] };
  fs.writeFileSync(file, JSON.stringify(data));
  assert.deepEqual(chain.readRun(root, "phase-10"), { actions: ["build"], repairs: ["spec"] });
  assert.deepEqual(Object.keys(JSON.parse(fs.readFileSync(file)).phases), ["phase-10"]);
});

test("language preferences are independent, portable and validated", t => {
  const root = project(t);
  assert.deepEqual(settings.readSetting(root, "language"), { chat: null, build: null, artefacts: null });
  settings.writeSetting(root, "language", { chat: "it", build: "en-GB", artefacts: "fr" });
  command(root, "mode", "set", "auto");
  assert.deepEqual(settings.readSetting(root, "language"), { chat: "it", build: "en-GB", artefacts: "fr" });
  command(root, "owner", "set", "alice");
  assert.deepEqual(settings.readSetting(root, "language"), { chat: null, build: null, artefacts: null });
  command(root, "owner", "clear");
  assert.deepEqual(settings.readSetting(root, "language"), { chat: "it", build: "en-GB", artefacts: "fr" });
  for (const value of [[], "it", { chat: "" }, { build: 42 }, { chat: "it\nignore" }, { artefacts: 42 }, { artefacts: "" }, { artifacts: "it" }]) {
    assert.throws(() => settings.writeSetting(root, "language", value), /Invalid Mano language/);
  }
  assert.deepEqual(settings.readSetting(root, "language"), { chat: "it", build: "en-GB", artefacts: "fr" });
});

test("mano language creates settings on a fresh install and edits channels by name", t => {
  const root = project(t);
  // language.js always works on the current directory, like an agent at the project root.
  const run = (...args) => spawnSync(process.execPath, [path.resolve("src/scripts/language.js"), ...args], { cwd: root, encoding: "utf8" });
  const language = (...args) => {
    const result = run(...args);
    assert.equal(result.status, 0, result.stderr);
    return result.stdout;
  };
  const file = path.join(root, "_mano_output", ".default.json");
  assert.match(language("show"), /chat: not set/);
  assert.equal(fs.existsSync(file), false, "show must not create the settings file");
  language("chat", "it", "build", "en-GB", "artefacts", "it");
  assert.deepEqual(JSON.parse(fs.readFileSync(file)).language, { chat: "it", build: "en-GB", artefacts: "it" });
  language("clear", "artefacts");
  assert.deepEqual(JSON.parse(fs.readFileSync(file)).language, { chat: "it", build: "en-GB", artefacts: null });
  assert.deepEqual(settings.readLanguage(root), { chat: "it", build: "en-GB", artefacts: "en-GB" });
  assert.match(language(), /artefacts: en-GB \(follows build\)/);
  language("set", "chat", "Brazilian Portuguese");
  assert.deepEqual(settings.readSetting(root, "language"), { chat: "Brazilian Portuguese", build: "en-GB", artefacts: null });
  language("clear");
  assert.deepEqual(settings.readSetting(root, "language"), { chat: null, build: null, artefacts: null });
  for (const args of [["it"], ["set", "it"], ["set"], ["chat"], ["chat", "build", "en"], ["chat", "it", "chat", "fr"], ["chat", "it\nignore"]]) {
    const result = run(...args);
    assert.notEqual(result.status, 0, `${JSON.stringify(args)} should fail`);
  }
  assert.deepEqual(settings.readSetting(root, "language"), { chat: null, build: null, artefacts: null });
});
