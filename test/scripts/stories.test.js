"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const stories = require("../../src/scripts/stories.js");
const { phaseRef } = require("../../src/scripts/phase.js");

test("stories parser collects repeatable story flags", () => {
  const parsed = stories.parseArgs([
    "set-status", "--phase", "2", "--story", "3", "--num", "3a", "--status", "done", "/tmp/project",
  ]);
  assert.equal(parsed.command, "set-status");
  assert.deepEqual(parsed.stories, ["3", "3a"]);
  assert.equal(parsed.phase, "2");
  assert.equal(parsed.status, "done");
});

test("stories row helpers parse and normalize Markdown table cells", () => {
  assert.deepEqual(stories.rowCells("| 3a | Title | story.md | pending |"), ["3a", "Title", "story.md", "pending"]);
  assert.equal(stories.rowStoryNum("| 3a | Title | story.md | pending |"), "3a");
  assert.equal(stories.rowStoryNum("| # | Story | File | Status |"), null);
  assert.equal(stories.formatRow("3", "A | title\n", "story.md", "pending"), "| 3 | A  /  title | story.md | pending |");
});

test("stories ordering places lettered insertions immediately after their base number", () => {
  assert.deepEqual(stories.numKey("12b"), [12, "b"]);
  assert.equal(stories.keyLess("3", "3a"), true);
  assert.equal(stories.keyLess("3a", "3b"), true);
  assert.equal(stories.keyLess("3z", "4"), true);
  assert.equal(stories.keyLess("10", "4"), false);
});

test("stories creates the canonical index heading for legacy and owner phases", () => {
  const row = stories.formatRow("1", "First", "story-1-first.md", "pending");
  assert.match(stories.freshIndex("Demo", phaseRef(null, 2), row), /^# Stories — Demo — Phase 2/);
  assert.match(stories.freshIndex("Demo", phaseRef("art", 2), row), /Phase 2 — Owner: art/);
});
