"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const phase = require("../../src/scripts/phase.js");

function withEnvironment(values, run) {
  const prior = new Map();
  for (const [key, value] of Object.entries(values)) {
    prior.set(key, process.env[key]);
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  try {
    return run();
  } finally {
    for (const [key, value] of prior) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

test("phase validates explicit owner and run-mode inputs", () => {
  assert.equal(phase.validateOwner(" gameplay-team "), "gameplay-team");
  assert.equal(phase.validateMode(" AUTO "), "auto");
  for (const owner of ["", "Alice", "alice@example.com", "-alice", "alice-"]) {
    assert.throws(() => phase.validateOwner(owner), /invalid Mano owner/);
  }
  assert.throws(() => phase.validateMode("yolo"), /invalid Mano mode/);
  assert.equal(phase.validateTrack(" Option B "), "Option B");
  assert.throws(() => phase.validateTrack(""), /invalid Mano track/);
  assert.throws(() => phase.validateTrack("two\nlines"), /invalid Mano track/);
  assert.throws(() => phase.validateTrack("tab\ttrack"), /invalid Mano track/);
});

test("phase parses legacy and owner-scoped directories", () => {
  assert.deepEqual(phase.parsePhaseDirName("phase-12"), {
    owner: null, number: 12, id: "phase-12", dirName: "phase-12",
  });
  assert.deepEqual(phase.parsePhaseDirName("combat-phase-3"), {
    owner: "combat", number: 3, id: "combat-phase-3", dirName: "combat-phase-3",
  });
  assert.equal(phase.parsePhaseDirName("phase-zero"), null);
  assert.equal(phase.parsePhaseDirName("Alice-phase-1"), null);
});

test("phase references keep owner identity in paths, statuses, and reviews", () => {
  assert.deepEqual(phase.phaseRef(null, 4), {
    owner: null,
    number: 4,
    id: "phase-4",
    dirName: "phase-4",
    relativeDir: "_mano_output/phase-4",
    inPhaseStatus: "in-phase-4",
    reviewHeading: "Phase 4 Review",
  });
  const owned = phase.phaseRef("gameplay", 4);
  assert.equal(owned.relativeDir, "_mano_output/gameplay-phase-4");
  assert.equal(owned.inPhaseStatus, "in-gameplay-phase-4");
  assert.match(owned.reviewHeading, /Owner: gameplay/);
  assert.throws(() => phase.phaseRef("gameplay", 0), /positive integer/);
});

test("phase routing filters the filesystem by the explicit owner and mode", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-phase-unit-"));
  const output = path.join(root, "_mano_output");
  fs.mkdirSync(path.join(output, "phase-9"), { recursive: true });
  fs.mkdirSync(path.join(output, "gameplay-phase-2"));
  fs.mkdirSync(path.join(output, "gameplay-phase-5"));
  fs.mkdirSync(path.join(output, "art-phase-7"));
  try {
    withEnvironment({ MANO_OWNER: "gameplay", MANO_MODE: "auto", MANO_TRACK: "Option B" }, () => {
      const routing = phase.phaseRouting(root, output);
      assert.equal(routing.mode, "owned");
      assert.equal(routing.runMode, "auto");
      assert.equal(routing.track, "Option B");
      assert.equal(routing.latest.id, "gameplay-phase-5");
      assert.deepEqual(routing.otherOwners, ["art"]);
    });
    withEnvironment({ MANO_OWNER: undefined, MANO_MODE: undefined, MANO_TRACK: undefined }, () => {
      const routing = phase.phaseRouting(root, output);
      assert.equal(routing.mode, "legacy");
      assert.equal(routing.latest.id, "phase-9");
      assert.equal(routing.runMode, "manual");
      assert.equal(routing.track, null);
    });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("review heading patterns keep legacy and owner namespaces separate", () => {
  const legacy = phase.reviewHeadingPattern(phase.phaseRef(null, 3));
  const owned = phase.reviewHeadingPattern(phase.phaseRef("art", 3));
  assert.match("## Phase 3 Review — 2026-08-12", legacy);
  assert.doesNotMatch("## Phase 3 Review — Owner: art — 2026-08-12", legacy);
  assert.match("## Phase 3 Review — Owner: art — 2026-08-12", owned);
  assert.doesNotMatch("## Phase 3 Review — Owner: gameplay — 2026-08-12", owned);
});
