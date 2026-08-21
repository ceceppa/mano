"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { spawnSync } = require("node:child_process");

const { writeAtomic } = require("../../src/scripts/atomic.js");

function tmp(prefix = "mano-atomic-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

test("writeAtomic replaces a file and leaves no temp behind", () => {
  const dir = tmp();
  const file = path.join(dir, "progress.md");
  writeAtomic(file, "first\n");
  writeAtomic(file, "second\n");
  assert.equal(fs.readFileSync(file, "utf8"), "second\n");
  assert.deepEqual(fs.readdirSync(dir), ["progress.md"]);
});

test("the temp file is a sibling, so the rename is atomic", () => {
  // A cross-filesystem rename is a copy, and a copy is not atomic. Staging in
  // the destination's own directory is the property the helper exists for.
  const dir = tmp();
  const file = path.join(dir, "progress.md");
  const opened = [];
  const realOpen = fs.openSync;
  fs.openSync = (p, ...rest) => { opened.push(p); return realOpen(p, ...rest); };
  try {
    writeAtomic(file, "x\n");
  } finally {
    fs.openSync = realOpen;
  }
  assert.equal(path.dirname(opened[0]), dir);
  assert.notEqual(opened[0], file, "the destination is never opened for writing");
});

test("an interrupt between the temp write and the rename leaves the previous file intact", () => {
  // B10, and the one real data-loss path in the product: a bare writeFileSync
  // truncates its target first, so a kill in that window leaves a half-written
  // ledger. Here the process dies with the temp file already written.
  const dir = tmp();
  const file = path.join(dir, "progress.md");
  fs.writeFileSync(file, "the previous, complete ledger\n");

  const script = `
    const fs = require("node:fs");
    const path = require("node:path");
    const file = ${JSON.stringify(file)};
    const realRename = fs.renameSync;
    fs.renameSync = () => { process.kill(process.pid, "SIGKILL"); };
    try {
      require(${JSON.stringify(path.resolve(__dirname, "..", "..", "src", "scripts", "atomic.js"))})
        .writeAtomic(file, "a replacement that must not land\\n");
    } finally {
      fs.renameSync = realRename;
    }
  `;
  const killed = spawnSync(process.execPath, ["-e", script], { encoding: "utf8" });
  assert.equal(killed.signal, "SIGKILL", "the child really died mid-write");
  assert.equal(fs.readFileSync(file, "utf8"), "the previous, complete ledger\n");
});

test("a failed rename cleans up its temp file and reports the failure", () => {
  const dir = tmp();
  const file = path.join(dir, "progress.md");
  fs.writeFileSync(file, "previous\n");
  const realRename = fs.renameSync;
  fs.renameSync = () => { throw new Error("EXDEV: simulated"); };
  try {
    assert.throws(() => writeAtomic(file, "next\n"), /EXDEV/);
  } finally {
    fs.renameSync = realRename;
  }
  assert.equal(fs.readFileSync(file, "utf8"), "previous\n");
  assert.deepEqual(fs.readdirSync(dir), ["progress.md"], "no temp file survives");
});

test("every ledger writer routes through it", () => {
  // The helper only closes B10 if nothing bypasses it. A bare writeFileSync
  // reappearing in one of these is the regression this catches.
  const scripts = path.resolve(__dirname, "..", "..", "src", "scripts");
  for (const name of ["progress.js", "stories.js", "backlog.js"]) {
    const source = fs.readFileSync(path.join(scripts, name), "utf8");
    const bare = source.split("\n").filter((line) => /\bfs\.writeFileSync\(/.test(line));
    assert.deepEqual(bare, [], `${name} still writes ${bare.length} file(s) non-atomically`);
    assert.match(source, /require\("\.\/atomic\.js"\)/, `${name} does not import writeAtomic`);
  }
});
