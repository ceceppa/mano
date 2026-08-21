"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { spawnSync } = require("node:child_process");

const progress = require("../../src/scripts/progress.js");
const L = require("../../src/scripts/ledger.js");

const SCRIPT = path.resolve(__dirname, "..", "..", "src", "scripts", "progress.js");
const STATE = path.resolve(__dirname, "..", "..", "src", "scripts", "state.js");

const BRIEF = `# Phase Brief — TaskCLI — Phase 1

## Phase Goal

A person can add, list, and complete tasks from the command line.

## Phase Scope

1. **TaskManager class** — a class backed by a JSON file: create the file if missing, add a task, list tasks, mark one complete.
2. **Persistence** — the data survives a restart
   a. **Write on change** — every mutation is flushed to disk immediately
   b. **Read on start** — the file is loaded once at startup
3. **Unit tests** — creation, completion, and filtering are covered.

## Not This Phase

- Networking, auth, and any UI.

## Exit Criteria

1. **Fresh start**
   a. Run \`add "Buy milk"\` with no data file: the file is created and a confirmation is shown
2. **Core interaction**
   a. \`add\`: the task gets a unique id, the given title, and is not completed
   b. \`done <bad-id>\`: it reports the task was not found and nothing changes
`;

function project(brief = BRIEF, phase = 1) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "mano-progress-"));
  const dir = path.join(root, "_mano_output", `phase-${phase}`);
  fs.mkdirSync(dir, { recursive: true });
  if (brief !== null) fs.writeFileSync(path.join(dir, "phase-brief.md"), brief);
  return {
    root,
    dir,
    ledger: path.join(dir, "progress.md"),
    read: () => fs.readFileSync(path.join(dir, "progress.md"), "utf8"),
    parse: () => L.parseLedger(fs.readFileSync(path.join(dir, "progress.md"), "utf8")),
    file: (name, text) => {
      const p = path.join(root, name);
      fs.writeFileSync(p, text);
      return p;
    },
  };
}

function run(root, args, env = {}) {
  return spawnSync("node", [SCRIPT, ...args, root], {
    encoding: "utf8",
    env: { ...process.env, ...env },
  });
}

// Every mutation carries the identity the caller saw; these helpers keep that
// out of the way of what each test is actually about.
function init(p, phase = 1, extra = []) {
  return run(p.root, ["init", "--phase", String(phase), "--expect-phase-id", `phase-${phase}`, ...extra]);
}
function setStatus(p, args, phase = 1) {
  return run(p.root, ["set-status", "--phase", String(phase), "--expect-phase-id", `phase-${phase}`, ...args]);
}
function statuses(p) {
  return Object.fromEntries(
    [...p.parse().ledger.scope, ...p.parse().ledger.exit].map((r) => [r.id, r.status]),
  );
}

// ---- args -----------------------------------------------------------------

test("each --status binds to the rows before it that lack one", () => {
  const shared = progress.parseArgs(["set-status", "--row", "S1", "--row", "S2", "--status", "done"]);
  assert.deepEqual(shared.entries.map((e) => [e.row, e.status]), [["S1", "done"], ["S2", "done"]]);

  const paired = progress.parseArgs([
    "set-status", "--row", "S2", "--status", "doing", "--reopen", "--row", "E2c", "--status", "pending", "--reopen",
  ]);
  assert.deepEqual(paired.entries.map((e) => [e.row, e.status, e.reopen]), [
    ["S2", "doing", true], ["E2c", "pending", true],
  ]);
});

// ---- init -----------------------------------------------------------------

test("init writes a v2 ledger whose rows are the brief's own items", () => {
  const p = project();
  const result = init(p);
  assert.equal(result.status, 0, result.stderr);

  const text = p.read();
  assert.match(text, /<!-- mano-progress: v2 -->/);
  assert.match(text, /<!-- contract: [0-9a-f]{16} -->/);
  const parsed = p.parse();
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.deepEqual(parsed.ledger.scope.map((r) => r.id), ["S1", "S2a", "S2b", "S3"]);
  assert.deepEqual(parsed.ledger.exit.map((r) => r.id), ["E1a", "E2a", "E2b"]);
  // The brief's own numbering, not a renumbering: item 3 stays S3 even though
  // item 2 contributed two leaves.
  assert.match(text, /\| S3 \| Unit tests \| pending \|/);
  // A nested leaf's cell carries its category, so the table can be scanned.
  assert.match(text, /\| S2a \| Persistence — Write on change \| pending \|/);
});

test("the contract digest pins the addressed brief", () => {
  const p = project();
  init(p);
  const before = p.parse().ledger.contract;
  assert.equal(before, L.contractDigest(BRIEF));

  // D12: an edit to Phase Goal / Phase Scope / Not This Phase / Exit Criteria
  // fails every later mutation closed, because every row address points into it.
  fs.writeFileSync(path.join(p.dir, "phase-brief.md"), BRIEF.replace("- Networking, auth, and any UI.", "- Networking only."));
  const blocked = setStatus(p, ["--row", "S1", "--status", "doing"]);
  assert.equal(blocked.status, 1);
  assert.match(blocked.stderr, /brief changed after this ledger was created/);
  assert.match(blocked.stderr, /nothing was written/);
  assert.equal(statuses(p).S1, "pending");
});

test("init refuses a second run, a prose-only section, and a phase that already has stories", () => {
  const p = project();
  init(p);
  const second = init(p);
  assert.equal(second.status, 1);
  assert.match(second.stderr, /already exists/);

  const prose = project(BRIEF.replace(/## Phase Scope\n\n[\s\S]*?\n## Not This Phase/, "## Phase Scope\n\nWe will build the thing.\n\n## Not This Phase"));
  const refused = init(prose);
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /no list to parse/);
  assert.equal(fs.existsSync(prose.ledger), false, "a refusal writes nothing");

  const dual = project();
  fs.mkdirSync(path.join(dual.dir, "stories"), { recursive: true });
  fs.writeFileSync(path.join(dual.dir, "stories", "README.md"), "| # | Story | File | Status |\n");
  const twoLedgers = init(dual);
  assert.equal(twoLedgers.status, 1);
  assert.match(twoLedgers.stderr, /A phase has one ledger/);
  assert.equal(fs.existsSync(dual.ledger), false);
});

test("init writes the owner into the heading and the path", () => {
  const p = project();
  const result = run(p.root, ["init", "--phase", "1", "--expect-phase-id", "alice-phase-1"], { MANO_OWNER: "alice" });
  assert.equal(result.status, 1, "the phase directory does not exist yet for that owner");

  const owned = project();
  const dir = path.join(owned.root, "_mano_output", "alice-phase-1");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "phase-brief.md"), BRIEF);
  const ok = run(owned.root, ["init", "--phase", "1", "--expect-phase-id", "alice-phase-1"], { MANO_OWNER: "alice" });
  assert.equal(ok.status, 0, ok.stderr);
  assert.match(fs.readFileSync(path.join(dir, "progress.md"), "utf8"), /# Progress — TaskCLI — Phase 1 — Owner: alice/);
});

// ---- identity guard -------------------------------------------------------

test("an owner change between projection and mutation writes nothing", () => {
  // B3: build wrote done/met and only afterwards checked owner and phase, while
  // the ledger path was resolved from whatever owner was configured *now*. An
  // owner change mid-implementation mutated another owner's same-numbered phase.
  const p = project();
  init(p);
  assert.equal(setStatus(p, ["--row", "S1", "--status", "doing"]).status, 0);

  const drifted = run(
    p.root,
    ["set-status", "--phase", "1", "--expect-phase-id", "phase-1", "--row", "S1", "--status", "done"],
    { MANO_OWNER: "alice" },
  );
  assert.equal(drifted.status, 1);
  assert.match(drifted.stderr, /identity changed/);
  assert.match(drifted.stderr, /Nothing was written/);
  assert.equal(statuses(p).S1, "doing");
});

test("every mutating command requires --expect-phase-id and rejects a disagreeing one", () => {
  const p = project();
  init(p);
  for (const command of ["set-status", "split", "add-row", "request-rework", "resolve-rework", "sign-off"]) {
    const bare = run(p.root, [command, "--phase", "1"]);
    assert.equal(bare.status, 1, command);
    assert.match(bare.stderr, /needs --expect-phase-id/, command);
  }
  const mismatch = run(p.root, ["set-status", "--phase", "1", "--expect-phase-id", "phase-2", "--row", "S1", "--status", "doing"]);
  assert.equal(mismatch.status, 1);
  assert.match(mismatch.stderr, /disagree/);
});

// ---- set-status -----------------------------------------------------------

test("the two status vocabularies stay separate in both directions", () => {
  const p = project();
  init(p);
  const scopeMet = setStatus(p, ["--row", "S1", "--status", "met"]);
  assert.equal(scopeMet.status, 1);
  assert.match(scopeMet.stderr, /built is not proven/);

  const exitDone = setStatus(p, ["--row", "E1a", "--status", "done"]);
  assert.equal(exitDone.status, 1);
  assert.match(exitDone.stderr, /built is not proven/);
});

test("a backwards move needs --reopen and is reported when it happens", () => {
  const p = project();
  init(p);
  setStatus(p, ["--row", "S1", "--status", "doing"]);
  setStatus(p, ["--row", "S1", "--status", "done"]);

  const silent = setStatus(p, ["--row", "S1", "--status", "doing"]);
  assert.equal(silent.status, 1);
  assert.match(silent.stderr, /without --reopen/);
  assert.equal(statuses(p).S1, "done");

  const loud = setStatus(p, ["--row", "S1", "--status", "doing", "--reopen"]);
  assert.equal(loud.status, 0, loud.stderr);
  assert.match(loud.stdout, /reopened — report this/);
});

test("one bad target in a batch writes nothing at all", () => {
  const p = project();
  init(p);
  const before = p.read();

  const unknown = setStatus(p, ["--row", "S1", "--status", "done", "--row", "S9", "--status", "done"]);
  assert.equal(unknown.status, 1);
  assert.equal(p.read(), before, "the good row in the batch is not written either");

  const duplicated = setStatus(p, ["--row", "S1", "--status", "doing", "--row", "S1", "--status", "done"]);
  assert.equal(duplicated.status, 1);
  assert.match(duplicated.stderr, /appears twice/);
  assert.equal(p.read(), before);

  // A stale expectation — the row already moved past where this call assumes
  // it is — is refused for the whole batch, not applied to the other row.
  setStatus(p, ["--row", "S1", "--status", "doing"]);
  setStatus(p, ["--row", "S1", "--status", "done"]);
  const stale = setStatus(p, ["--row", "S3", "--status", "doing", "--row", "S1", "--status", "pending"]);
  assert.equal(stale.status, 1);
  assert.equal(statuses(p).S3, "pending", "the other row in the batch was left alone");
});

// ---- split and roll-ups ---------------------------------------------------

test("split records its first part done and derives the parent from its children", () => {
  const p = project();
  init(p);
  setStatus(p, ["--row", "S1", "--status", "doing"]);

  const early = run(p.root, ["split", "--phase", "1", "--expect-phase-id", "phase-1", "--row", "S3", "--part-file", p.file("x.txt", "too early")]);
  assert.equal(early.status, 1, "only the row being built may be split");
  assert.match(early.stderr, /only the row currently being built/);

  const split = run(p.root, [
    "split", "--phase", "1", "--expect-phase-id", "phase-1", "--row", "S1",
    "--part-file", p.file("a.txt", "add + wiring"),
    "--part-file", p.file("b.txt", "list + done"),
  ]);
  assert.equal(split.status, 0, split.stderr);
  const after = statuses(p);
  assert.equal(after["S1.1"], "done", "a split is legitimate only once a part is complete");
  assert.equal(after["S1.2"], "pending");
  assert.equal(after.S1, "doing", "derived from its children");
});

test("a roll-up parent cannot be written directly and closes with its last child", () => {
  const p = project();
  init(p);
  setStatus(p, ["--row", "S1", "--status", "doing"]);
  run(p.root, ["split", "--phase", "1", "--expect-phase-id", "phase-1", "--row", "S1",
    "--part-file", p.file("a.txt", "first"), "--part-file", p.file("b.txt", "second")]);

  const direct = setStatus(p, ["--row", "S1", "--status", "done"]);
  assert.equal(direct.status, 1);
  assert.match(direct.stderr, /roll-up over S1\.1, S1\.2/);
  assert.equal(statuses(p).S1, "doing");

  const closing = setStatus(p, ["--row", "S1.2", "--status", "done"]);
  assert.equal(closing.status, 0, closing.stderr);
  assert.equal(statuses(p).S1, "done");
  // Promotion is committed in the same write as the child that closed it.
  assert.match(closing.stdout, /S1 \(doing → done, derived from its children\)/);
});

test("an Exit row is never split", () => {
  const p = project();
  init(p);
  const refused = run(p.root, ["split", "--phase", "1", "--expect-phase-id", "phase-1", "--row", "E1a", "--part-file", p.file("x.txt", "no")]);
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /Exit Criteria are the human's leaves/);
});

// ---- add-row --------------------------------------------------------------

test("add-row allocates the correction number and links it to an Exit Criterion", () => {
  const p = project();
  init(p);
  const words = p.file("c.txt", 'the empty state should say\n"nothing here yet | add one"');

  const unlinked = run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a", "--text-file", words]);
  assert.equal(unlinked.status, 1, "a correction must say which promise it changes");
  assert.match(unlinked.stderr, /needs --exit/);

  const added = run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a", "--text-file", words, "--exit", "E2a"]);
  assert.equal(added.status, 0, added.stderr);

  const parsed = p.parse();
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.ok(parsed.ledger.byId.has("S2a+1"), "the caller never chooses the number");
  assert.equal(parsed.ledger.contracts.get("S2a+1").attributes.affects, "E2a");
  assert.equal(
    parsed.ledger.contracts.get("S2a+1").text,
    'the empty state should say\n"nothing here yet | add one"',
    "the user's own words, byte for byte, pipes and quotes included",
  );

  const second = run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a", "--text-file", p.file("d.txt", "and again"), "--exit", "E2a"]);
  assert.equal(second.status, 0, second.stderr);
  assert.ok(p.parse().ledger.byId.has("S2a+2"));
});

test("a correction of a correction is refused, and so is one under nothing", () => {
  const p = project();
  init(p);
  const words = p.file("c.txt", "words");
  run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a", "--text-file", words, "--exit", "E2a"]);

  const chained = run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a+1", "--text-file", words, "--exit", "E2a"]);
  assert.equal(chained.status, 1);
  assert.match(chained.stderr, /never off another correction/);

  const newScope = run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S9", "--text-file", words, "--exit", "E2a"]);
  assert.equal(newScope.status, 1);
  assert.match(newScope.stderr, /new scope, not a correction/);
});

test("new Exit wording lands as a correction leaf under the criterion it supersedes", () => {
  const p = project();
  init(p);
  const added = run(p.root, [
    "add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a",
    "--text-file", p.file("c.txt", "flush on every write"),
    "--exit", "E2a",
    "--exit-text-file", p.file("e.txt", "add: the task is on disk before the command returns"),
  ]);
  assert.equal(added.status, 0, added.stderr);
  const parsed = p.parse();
  assert.ok(parsed.ledger.byId.has("E2a+1"));
  assert.equal(parsed.ledger.contracts.get("S2a+1").attributes.affects, "E2a+1");
  assert.equal(parsed.ledger.byId.get("E2a").label, "Core interaction — `add`: the task gets a unique id, the given title, and is not completed",
    "the superseded criterion stays readable");
});

test("text arguments are refused on the command line", () => {
  // Quotes, backticks, $(), and newlines do not survive a shell round-trip, and
  // fish expands sequences other shells do not.
  const p = project();
  init(p);
  for (const args of [
    ["add-row", "--parent", "S2a", "--text", "inline", "--exit", "E2a"],
    ["split", "--row", "S1", "--part", "inline"],
  ]) {
    const refused = run(p.root, [args[0], "--phase", "1", "--expect-phase-id", "phase-1", ...args.slice(1)]);
    assert.equal(refused.status, 1, args[0]);
    assert.match(refused.stderr, /travel as files/, args[0]);
  }
});

// ---- rework ---------------------------------------------------------------

test("rework events are ordered, keep their exact text, and close explicitly", () => {
  const p = project();
  init(p);
  const first = run(p.root, ["request-rework", "--phase", "1", "--expect-phase-id", "phase-1",
    "--text-file", p.file("r1.txt", "deleting a task removes it with no confirmation step")]);
  assert.equal(first.status, 0, first.stderr);
  const second = run(p.root, ["request-rework", "--phase", "1", "--expect-phase-id", "phase-1",
    "--text-file", p.file("r2.txt", "the list is not sorted")]);
  assert.equal(second.status, 0, second.stderr);

  let parsed = p.parse();
  assert.deepEqual(parsed.ledger.rework.map((r) => [r.id, r.status]), [["R1", "pending"], ["R2", "pending"]]);
  assert.equal(parsed.ledger.contracts.get("R1").text, "deleting a task removes it with no confirmation step");

  const resolved = run(p.root, ["resolve-rework", "--phase", "1", "--expect-phase-id", "phase-1", "--id", "R1", "--status", "resolved"]);
  assert.equal(resolved.status, 0, resolved.stderr);

  const bareDismissal = run(p.root, ["resolve-rework", "--phase", "1", "--expect-phase-id", "phase-1", "--id", "R2", "--status", "dismissed"]);
  assert.equal(bareDismissal.status, 1, "dismissal discards a finding a human confirmed");
  assert.match(bareDismissal.stderr, /--reason-file is required/);

  const dismissed = run(p.root, ["resolve-rework", "--phase", "1", "--expect-phase-id", "phase-1", "--id", "R2", "--status", "dismissed",
    "--reason-file", p.file("why.txt", "the user said unsorted is intended for now")]);
  assert.equal(dismissed.status, 0, dismissed.stderr);

  parsed = p.parse();
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.deepEqual(parsed.ledger.rework.map((r) => r.status), ["resolved", "dismissed"]);
  assert.equal(
    parsed.ledger.contracts.get("R2").attributes["dismissed-reason"],
    "the user said unsorted is intended for now",
  );

  const again = run(p.root, ["resolve-rework", "--phase", "1", "--expect-phase-id", "phase-1", "--id", "R1", "--status", "resolved"]);
  assert.equal(again.status, 1, "an event closes once");
});

// ---- needs-human and sign-off ---------------------------------------------

function closeAllScope(p) {
  for (const id of ["S1", "S2a", "S2b", "S3"]) {
    setStatus(p, ["--row", id, "--status", "doing"]);
    setStatus(p, ["--row", id, "--status", "done"]);
  }
}

test("needs-human is a terminal handoff, not a mid-build escape hatch", () => {
  const p = project();
  init(p);
  const reason = p.file("why.txt", "cannot be honestly judged by the implementing agent");

  const early = setStatus(p, ["--row", "E1a", "--status", "needs-human", "--reason-file", reason]);
  assert.equal(early.status, 1);
  assert.match(early.stderr, /still open/);

  closeAllScope(p);
  const bare = setStatus(p, ["--row", "E1a", "--status", "needs-human"]);
  assert.equal(bare.status, 1, "it carries a reason or it is not written");
  assert.match(bare.stderr, /--reason-file is required/);

  const ok = setStatus(p, ["--row", "E1a", "--status", "needs-human", "--reason-file", reason]);
  assert.equal(ok.status, 0, ok.stderr);
  const parsed = p.parse();
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.equal(parsed.ledger.contracts.get("E1a").attributes.reason, "cannot be honestly judged by the implementing agent");
});

test("needs-human is refused while a rework event is pending", () => {
  const p = project();
  init(p);
  closeAllScope(p);
  run(p.root, ["request-rework", "--phase", "1", "--expect-phase-id", "phase-1", "--text-file", p.file("r.txt", "delete does not confirm")]);
  const refused = setStatus(p, ["--row", "E1a", "--status", "needs-human", "--reason-file", p.file("why.txt", "visual")]);
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /still pending/);
});

test("sign-off flips pending and needs-human leaves to met with recorded provenance", () => {
  const p = project();
  init(p);
  closeAllScope(p);
  setStatus(p, ["--row", "E2a", "--status", "met"]);
  setStatus(p, ["--row", "E1a", "--status", "needs-human", "--reason-file", p.file("why.txt", "inherently visual")]);

  const signed = run(p.root, ["sign-off", "--phase", "1", "--expect-phase-id", "phase-1"]);
  assert.equal(signed.status, 0, signed.stderr);

  const parsed = p.parse();
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.deepEqual(parsed.ledger.exit.map((r) => r.status), ["met", "met", "met"]);
  // The ledger records *who* proved it: "built is not proven" survives more
  // honestly as attributed evidence than as a status nobody owns.
  const stamp = new Date().toISOString().slice(0, 10);
  assert.equal(parsed.ledger.contracts.get("E1a").attributes.provenance, `human sign-off at review, ${stamp}`);
  assert.equal(parsed.ledger.contracts.get("E2b").attributes.provenance, `human sign-off at review, ${stamp}`);
  assert.equal(parsed.ledger.contracts.has("E2a"), false, "a criterion already met is not re-attested");
});

test("sign-off refuses while a review finding is open", () => {
  const p = project();
  init(p);
  closeAllScope(p);
  run(p.root, ["request-rework", "--phase", "1", "--expect-phase-id", "phase-1", "--text-file", p.file("r.txt", "delete does not confirm")]);
  const refused = run(p.root, ["sign-off", "--phase", "1", "--expect-phase-id", "phase-1"]);
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /still pending/);
});

// ---- writer and reader agree ----------------------------------------------

test("the ledger progress.js writes is the ledger state.js reads back", () => {
  const p = project();
  init(p);
  setStatus(p, ["--row", "S1", "--status", "doing"]);
  run(p.root, ["split", "--phase", "1", "--expect-phase-id", "phase-1", "--row", "S1",
    "--part-file", p.file("a.txt", "add + wiring"), "--part-file", p.file("b.txt", "list + done")]);
  run(p.root, ["add-row", "--phase", "1", "--expect-phase-id", "phase-1", "--parent", "S2a",
    "--text-file", p.file("c.txt", "flush | on every write"), "--exit", "E2a"]);

  const projection = spawnSync("node", [STATE, "--next", p.root], { encoding: "utf8" });
  assert.equal(projection.status, 0, projection.stderr);
  const out = projection.stdout;

  assert.match(out, /PROGRESS_STATUS: present/);
  // B2: the deepest open leaf, not the roll-up parent that file order returns.
  assert.match(out, /^ROW: S1\.2$/m);
  // B1: the row's full contract text, inline — no second read of the brief.
  assert.match(out, /^ROW_CONTRACT:$/m);
  assert.match(out, /list \+ done/);
  // B7: build now has the artifact inventory the stories path always had.
  assert.match(out, /^ARTIFACTS: /m);
  assert.match(out, /^= S1 /m, "the roll-up is marked as derived");
});

test("a normal nested leaf projects its whole brief line, not its bolded lead", () => {
  const p = project();
  init(p);
  setStatus(p, ["--row", "S1", "--status", "doing"]);
  setStatus(p, ["--row", "S1", "--status", "done"]);

  const projection = spawnSync("node", [STATE, "--next", p.root], { encoding: "utf8" });
  assert.match(projection.stdout, /^ROW: S2a$/m);
  assert.match(
    projection.stdout,
    /Persistence — Write on change — every mutation is flushed to disk immediately/,
  );
});

test("an invalid ledger is a hard stop, never an unstarted phase", () => {
  const p = project();
  init(p);
  fs.writeFileSync(p.ledger, p.read().replace("<!-- mano-progress: v2 -->\n", ""));
  const broken = p.read();

  const projection = spawnSync("node", [STATE, "--next", p.root], { encoding: "utf8" });
  assert.match(projection.stdout, /PROGRESS_STATUS: invalid/);
  assert.match(projection.stdout, /Delete .*progress\.md and re-run mano build/);
  assert.doesNotMatch(projection.stdout, /PROGRESS_STATUS: missing/);

  const blocked = setStatus(p, ["--row", "S1", "--status", "doing"]);
  assert.equal(blocked.status, 1);
  assert.match(blocked.stderr, /is invalid and nothing was written/);
  assert.equal(p.read(), broken, "a refusal does not change a byte, not even to repair");
});

test("the dual-ledger refusal fires even when the ledger is malformed", () => {
  // B4: the check used to be `if (stories && progress)`, and a malformed
  // progress.md made `progress` null — so the one state that most needs the
  // refusal was the one state that skipped it.
  const p = project();
  fs.writeFileSync(p.ledger, "this is not a ledger\n");
  fs.mkdirSync(path.join(p.dir, "stories"), { recursive: true });
  fs.writeFileSync(path.join(p.dir, "stories", "README.md"),
    "| # | Story | File | Status |\n|---|---|---|---|\n| 1 | Setup | story-1.md | done |\n");
  fs.writeFileSync(path.join(p.root, "_mano_output", "backlog.md"), "# Backlog\n\n## Items\n");

  const projection = spawnSync("node", [STATE, p.root], { encoding: "utf8" });
  assert.notEqual(projection.status, 0);
  assert.match(projection.stderr, /holds both stories\/README\.md and progress\.md/);
});

test("a planning artifact newer than the ledger raises an advisory flag only", () => {
  const p = project();
  init(p);
  const spec = path.join(p.root, "_mano_output", "tech-spec.md");
  fs.writeFileSync(spec, "# Tech Spec\n");
  const later = new Date(Date.now() + 60_000);
  fs.utimesSync(spec, later, later);

  const projection = spawnSync("node", [STATE, "--next", p.root], { encoding: "utf8" });
  assert.equal(projection.status, 0);
  assert.match(projection.stdout, /⚠ tech-spec\.md changed after the ledger was last written/);
  // Advisory means advisory: the row to work on is unchanged and nothing routes.
  assert.match(projection.stdout, /^ROW: S1$/m);
});
