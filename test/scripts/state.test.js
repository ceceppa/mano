"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const state = require("../../src/scripts/state.js");
const { phaseRef } = require("../../src/scripts/phase.js");

const BACKLOG = `# Backlog

## Core Product Principles

Keep the game readable.

## Items

### Open feature
- **Type:** feature
- **Context:**
  Build the visible interaction.
- **Status:** backlog

### Open spec gap
- **Type:** spec-gap
- **Context:**
  Define exact method arguments.
- **Status:** backlog

### Shipped feature
- **Type:** feature
- **Status:** resolved

## Notes

### Not a backlog item
- **Type:** spec-gap
- **Status:** backlog
`;

test("state parser keeps projection switches and a project root distinct", () => {
  const parsed = state.parseArgs(["--spec", "--json", "--verbose", "/tmp/project"]);
  assert.equal(parsed.spec, true);
  assert.equal(parsed.json, true);
  assert.equal(parsed.verbose, true);
  assert.equal(parsed.root, path.resolve("/tmp/project"));
  assert.equal(state.parseArgs(["--gaps"]).gaps, "");
  assert.equal(state.parseArgs(["--gaps", "rule-gap"]).gaps, "rule-gap");
});

test("state parses story rows and treats every non-done status as pending work", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-stories-"));
  const index = path.join(root, "README.md");
  fs.writeFileSync(index, `| # | Story | File | Status |
|---|-------|------|--------|
| 1 | Setup | story-1.md | done |
| 2a | Follow-up | story-2a.md | blocked |
| Notes | ignored | ignored | done |
`);
  try {
    assert.deepEqual(state.readStories(index), {
      total: 2,
      done: 1,
      openTitles: ["2a Follow-up (blocked)"],
      rows: [
        { num: "1", title: "Setup", file: "story-1.md", status: "done" },
        { num: "2a", title: "Follow-up", file: "story-2a.md", status: "blocked" },
      ],
    });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("state restricts backlog projections to canonical Items blocks", () => {
  assert.deepEqual(state.countBacklogStatuses(BACKLOG), { backlog: 2, resolved: 1 });
  assert.deepEqual(
    state.extractBacklogItems(BACKLOG, { status: "backlog" }).map((item) => item.match(/^### (.+)$/m)[1]),
    ["Open feature", "Open spec gap"],
  );
  assert.deepEqual(
    state.extractBacklogItems(BACKLOG, { status: "backlog", excludeTypes: ["spec-gap"] })
      .map((item) => item.match(/^### (.+)$/m)[1]),
    ["Open feature"],
  );
  assert.equal(state.extractCoreProductPrinciples(BACKLOG), "## Core Product Principles\n\nKeep the game readable.");
});

test("state filters Track across canonical and human-edited Markdown forms", () => {
  const tracked = `# Backlog

## Items

### Canonical track
- **Type:** feature
- **Track:** Option B
- **Context:**
  Canonical writer output.
- **Status:** backlog

### Human-edited track
- **Type:** feature
- **Track**: option b
- **Context:**
  Colon outside the bold label.
- **Status:** backlog

### Different track
- **Type:** feature
- **Track:** Option A
- **Context:**
  Another experiment.
- **Status:** backlog

### No track
- **Type:** feature
- **Context:**
  General work.
- **Status:** backlog
`;

  const names = state.extractBacklogItems(tracked, { status: "backlog", track: "OPTION B" })
    .map((item) => item.match(/^### (.+)$/m)[1]);

  assert.deepEqual(names, ["Canonical track", "Human-edited track"]);
});

test("state rejects malformed canonical item envelopes", () => {
  assert.throws(
    () => state.assertBacklogItemsWellFormed("## Items\n\n### Missing status\n- **Type:** feature\n"),
    /expected exactly one top-level Type and Status field/,
  );
  assert.throws(
    () => state.assertBacklogItemsWellFormed(
      "## Items\n\n### Conflicting track\n- **Type:** feature\n- **Track:** A\n- **Track**: B\n- **Status:** backlog\n",
    ),
    /at most one Source and Track field/,
  );
  assert.doesNotThrow(() => state.assertBacklogItemsWellFormed(BACKLOG));
});

test("resume draft keeps the Track already assigned to its items", () => {
  const assigned = [
    "### One\n- **Type:** feature\n- **Track:** Option A\n- **Status:** in-phase-2",
    "### Two\n- **Type:** feature\n- **Track**: option a\n- **Status:** in-phase-2",
  ];
  assert.equal(state.resumeDraftTrack(assigned, "Option B", "phase-2"), "Option A");
  assert.equal(state.resumeDraftTrack([], "Option B", "phase-2"), "Option B");
  assert.throws(
    () => state.resumeDraftTrack(
      [...assigned, "### Three\n- **Type:** feature\n- **Status:** in-phase-2"],
      "Option B",
      "phase-2",
    ),
    /conflicting Track values/,
  );
});

test("state scope and gap scans fail closed on malformed backlog items", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-malformed-"));
  const output = path.join(root, "_mano_output");
  fs.mkdirSync(output);
  fs.writeFileSync(
    path.join(output, "backlog.md"),
    "# Backlog\n\n## Items\n\n### Missing status\n- **Type:** rule-gap\n",
  );
  try {
    assert.throws(() => state.scan(root), /malformed backlog item/);
    assert.throws(() => state.scanGaps(root, "rule-gap"), /malformed backlog item/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("state selects reviews only from the requested phase namespace", () => {
  const reviews = `## Phase 2 Review — Owner: art — 2026-01-01

Art review.

## Phase 3 Review — Owner: gameplay — 2026-01-02

Gameplay review.

## Phase 4 Review — Owner: art — 2026-01-03

Latest art review.
`;
  assert.match(state.extractLatestReview(reviews, phaseRef("art", 2)), /Art review/);
  assert.match(state.extractLatestReview(reviews, null, "art"), /Latest art review/);
  assert.equal(state.extractLatestReview(reviews, phaseRef(null, 2)), null);
  assert.equal(state.hasReviewEntry(reviews, phaseRef("art", 2)), true);
  assert.equal(state.hasReviewEntry(reviews, phaseRef("gameplay", 2)), false);
});

test("state projects active hooks with their declared mode and never the examples", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-hooks-"));
  try {
    const hooks = path.join(root, "_mano", "hooks");
    fs.mkdirSync(hooks, { recursive: true });
    fs.writeFileSync(path.join(hooks, "post-start.md"), "# post-start hook\n\n## Mode\ncheck\n\n## Checklist\n- something\n");
    fs.writeFileSync(path.join(hooks, "post-import.md"), "# post-import hook\n\n## Mode\ncommand\n\n## Command\nnode x.js\n");
    fs.writeFileSync(path.join(hooks, "post-spec.md"), "# post-spec hook\n\n## Purpose\nlegacy, no mode section\n");
    fs.writeFileSync(path.join(hooks, "post-ux.example.md"), "# example\n\n## Mode\ncheck\n");
    assert.deepEqual(state.scanHooks(root), [
      "command:post-import",
      "check:post-start",
      "suggest:post-spec",
    ]);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("state projects HOOK and ARTIFACTS lines in the decision projection", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-artifacts-"));
  try {
    const out = path.join(root, "_mano_output");
    fs.mkdirSync(out, { recursive: true });
    fs.writeFileSync(path.join(out, "backlog.md"), BACKLOG);
    fs.writeFileSync(path.join(out, "tech-spec.md"), "# Tech Spec\n");
    const rendered = state.renderDecision(state.scan(root));
    assert.match(rendered, /^HOOK: none$/m);
    assert.match(
      rendered,
      /^ARTIFACTS: tech-spec=present ux-flow=absent design-brief=absent project-rules=absent$/m,
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("unrecognised hook modes fall back to suggest", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-hookmode-"));
  try {
    const hooks = path.join(root, "_mano", "hooks");
    fs.mkdirSync(hooks, { recursive: true });
    fs.writeFileSync(path.join(hooks, "post-review.md"), "# hook\n\n## Mode\nsomething-else\n");
    assert.deepEqual(state.scanHooks(root), ["suggest:post-review"]);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("state reads a build ledger's two tables and the next non-done scope row", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-progress-"));
  const ledger = path.join(root, "progress.md");
  fs.writeFileSync(ledger, `# Progress — Demo — Phase 1

## Scope
| # | What | Status |
|---|------|--------|
| S1 | Store | done |
| S2 | Runner | doing |
| S2.1 | wiring | done |
| S3 | Tests | pending |

## Exit Criteria
| # | Criterion | Status |
|---|-----------|--------|
| E1a | Fresh start: a confirmation is shown | met |
| E2a | Bad id: nothing changes | pending |
| Notes | ignored | met |
`);
  const progress = state.readProgress(ledger);
  assert.equal(progress.scope.total, 4);
  assert.equal(progress.scope.closed, 2);
  assert.equal(progress.exit.total, 2, "a prose row is not a criterion");
  assert.equal(progress.exit.closed, 1);
  assert.equal(progress.next.id, "S2");
  assert.equal(progress.allDone, false);
  assert.equal(progress.allMet, false);
  assert.equal(state.readProgress(path.join(root, "absent.md")), null);
});

test("state refuses a phase that holds both a stories index and a build ledger", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-state-two-ledgers-"));
  const phaseDir = path.join(root, "_mano_output", "phase-1");
  fs.mkdirSync(path.join(phaseDir, "stories"), { recursive: true });
  fs.writeFileSync(path.join(root, "_mano_output", "backlog.md"), "# Backlog\n\n## Items\n");
  fs.writeFileSync(path.join(phaseDir, "phase-brief.md"), "# Phase Brief — Demo — Phase 1\n");
  fs.writeFileSync(path.join(phaseDir, "stories", "README.md"),
    "| # | Story | File | Status |\n|---|---|---|---|\n| 1 | Setup | story-1.md | done |\n");
  fs.writeFileSync(path.join(phaseDir, "progress.md"),
    "## Scope\n| # | What | Status |\n|---|---|---|\n| S1 | Store | pending |\n");
  assert.throws(() => state.scan(root), /one ledger/i);
});
