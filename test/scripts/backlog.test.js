"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const backlog = require("../../src/scripts/backlog.js");

const SAMPLE = `# Backlog

## Core Product Principles

### Not an item
- **Type:** spec-gap
- **Status:** backlog

## Items

### First item
- **Type:** feature
- **Context:**
  A human-readable context.
- **Status:** backlog

### Second item
- **Type:** spec-gap
- **Context:**
  Define the public contract.
- **Status:** resolved

## Notes

### Not an item either
- **Type:** feature
- **Status:** backlog
`;

test("backlog parser retains repeated title flags and an explicit root", () => {
  const parsed = backlog.parseArgs([
    "assign", "--phase", "7", "--title", "First item", "--title", "Second item", "/tmp/project",
  ]);
  assert.equal(parsed.command, "assign");
  assert.equal(parsed.phase, "7");
  assert.deepEqual(parsed.titles, ["First item", "Second item"]);
  assert.equal(parsed.root, path.resolve("/tmp/project"));
});

test("backlog formatting normalizes context while retaining the canonical shape", () => {
  const item = backlog.formatItem({
    title: "  Add onboarding  ",
    type: "feature",
    source: "Phase 1 review",
    track: "Option B",
    context: "\nFirst line  \r\nSecond line\n",
  });
  assert.equal(item, `### Add onboarding
- **Type:** feature
- **Source:** Phase 1 review
- **Track:** Option B
- **Context:**
  First line
  Second line
- **Status:** backlog`);
});

test("backlog validates the item envelope and line limit", () => {
  assert.equal(backlog.validateItem({ title: "One", type: "bug", context: "Fix it" }, 0), null);
  assert.match(backlog.validateItem({ type: "bug", context: "Fix it" }, 0), /missing "title"/);
  assert.match(backlog.validateItem({ title: "One", type: "unknown", context: "Fix it" }, 0), /not one of/);
  assert.match(
    backlog.validateItem({ title: "One", type: "bug", context: "1\n2\n3\n4\n5\n6" }, 0),
    /max 5/,
  );
  assert.match(
    backlog.validateItem({ title: "One", type: "bug", context: "Fix it", track: "bad\ntrack" }, 0),
    /invalid Mano track/,
  );
});

test("backlog displays explicit and missing tracks", () => {
  assert.equal(backlog.displayTrack({ track: " Option B " }), "Option B");
  assert.equal(backlog.displayTrack({ track: "" }), "undefined");
  assert.equal(backlog.displayTrack({}), "undefined");
});

test("backlog title detection and records ignore non-Items sections", () => {
  assert.deepEqual([...backlog.existingTitles(SAMPLE)].sort(), ["first item", "not an item", "not an item either", "second item"]);
  const records = backlog.parseItemRecords(SAMPLE);
  assert.equal(records.records.length, 2);
  assert.deepEqual(records.records.map((record) => record.title), ["First item", "Second item"]);
  assert.equal(backlog.itemField(records.lines, records.records[0], "Status").value, "backlog");
  assert.equal(backlog.itemField(records.lines, records.records[1], "Type").value, "spec-gap");
});

test("backlog inserts blocks inside the canonical Items section", () => {
  const block = backlog.formatItem({ title: "Third item", type: "test", context: "Cover it" });
  const next = backlog.buildWithItems(SAMPLE, [block]);
  assert.match(next, /### Second item[\s\S]*?### Third item[\s\S]*?## Notes/);
  assert.equal(next.indexOf("### Third item") < next.indexOf("## Notes"), true);
  assert.match(backlog.buildWithItems(null, [block]), /^# Backlog\n\n## Items/);
});
