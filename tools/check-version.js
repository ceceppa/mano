#!/usr/bin/env node
"use strict";

/**
 * check-version — keep `src/VERSION` and `package.json` in lockstep.
 *
 * `src/VERSION` ships inside the install as `_mano/VERSION`, so it is the only
 * thing an installed project can read to know which Mano it is running. npm
 * never writes it: `npm version` bumps package.json and nothing else, which is
 * exactly how the two drift. A stale `_mano/VERSION` is worse than none — it
 * reports a version whose behaviour the install does not have.
 *
 * Usage:
 *   node tools/check-version.js         verify they match; exit 1 if not
 *   node tools/check-version.js --fix   rewrite src/VERSION from package.json
 *
 * Wired in three places, so drift has to survive all of them:
 *   npm test          — the guard runs with the suite
 *   npm version       — `--fix` + `git add`, so a bump can't leave VERSION behind
 *   prepublishOnly    — the last gate before a broken version reaches npm
 */

const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..");
const PKG_FILE = path.join(REPO_ROOT, "package.json");
const VERSION_FILE = path.join(REPO_ROOT, "src", "VERSION");
const RELATIVE = "src/VERSION";

// npm's own range, loosely: three dot-separated numbers plus an optional
// prerelease/build tail. Deliberately not a full semver parser — this only has
// to reject a file holding prose, a heading, or an empty line.
const SEMVER = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

function fail(message) {
  process.stderr.write(`check-version: ${message}\n`);
  process.exit(1);
}

function packageVersion() {
  let raw;
  try {
    raw = fs.readFileSync(PKG_FILE, "utf8");
  } catch (err) {
    fail(`cannot read package.json (${err.message})`);
  }
  let version;
  try {
    version = JSON.parse(raw).version;
  } catch (err) {
    fail(`package.json is not valid JSON (${err.message})`);
  }
  if (typeof version !== "string" || !SEMVER.test(version)) {
    fail(`package.json version is not a version string: ${JSON.stringify(version)}`);
  }
  return version;
}

function write(version) {
  fs.writeFileSync(VERSION_FILE, `${version}\n`);
}

function main(argv) {
  const fix = argv.includes("--fix");
  const expected = packageVersion();

  if (fix) {
    write(expected);
    process.stdout.write(`check-version: ${RELATIVE} set to ${expected}\n`);
    return;
  }

  if (!fs.existsSync(VERSION_FILE)) {
    fail(
      `${RELATIVE} is missing — the install would ship no _mano/VERSION.\n` +
        `  Run: node tools/check-version.js --fix`,
    );
  }

  const raw = fs.readFileSync(VERSION_FILE, "utf8");
  const found = raw.trim();

  if (!SEMVER.test(found)) {
    fail(
      `${RELATIVE} does not hold a bare version string (found ${JSON.stringify(raw)}).\n` +
        `  It must be the version and nothing else — no heading, no label, no comment.\n` +
        `  Run: node tools/check-version.js --fix`,
    );
  }

  if (found !== expected) {
    fail(
      `${RELATIVE} says ${found}, package.json says ${expected}.\n` +
        `  An install would ship _mano/VERSION reporting ${found}.\n` +
        `  Run: node tools/check-version.js --fix`,
    );
  }

  // A trailing newline and nothing else: anything a reader has to trim is a
  // file some other tool will read wrong.
  if (raw !== `${expected}\n`) {
    fail(
      `${RELATIVE} holds ${expected} but with stray whitespace — it must be exactly "${expected}\\n".\n` +
        `  Run: node tools/check-version.js --fix`,
    );
  }

  process.stdout.write(`check-version: ${RELATIVE} and package.json both at ${expected}\n`);
}

main(process.argv.slice(2));
