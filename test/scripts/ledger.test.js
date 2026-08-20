"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const L = require("../../src/scripts/ledger.js");

const FENCE = "`".repeat(3);

function ledgerText({ scope, exit, rework = "", contracts = "", version = true, contract = "0123456789abcdef" }) {
  return [
    "# Progress — Demo — Phase 1",
    "",
    version ? "<!-- mano-progress: v2 -->" : "",
    contract ? `<!-- contract: ${contract} -->` : "",
    "",
    "## Scope",
    "",
    L.SCOPE_HEADER,
    L.SCOPE_SEPARATOR,
    scope,
    "",
    "## Exit Criteria",
    "",
    L.EXIT_HEADER,
    L.EXIT_SEPARATOR,
    exit,
    rework ? `\n## Rework\n\n${L.REWORK_HEADER}\n${L.REWORK_SEPARATOR}\n${rework}` : "",
    contracts ? `\n## Row Contracts\n${contracts}` : "",
    "",
  ].filter((l) => l !== "").join("\n");
}

const MINIMAL = ledgerText({
  scope: "| S1 | Store | pending |",
  exit: "| E1a | It works | pending |",
});

// ---- grammar --------------------------------------------------------------

test("the row grammar separates corrections, splits, and normal nested leaves", () => {
  assert.deepEqual(
    ["S2", "S2a", "S2+1", "S2a+1", "S2.1", "S2a+1.1", "E2a", "E2a+1"].map((id) => {
      const p = L.parseRowId(id);
      return [p.id, p.kind];
    }),
    [
      ["S2", "normal"],
      ["S2a", "normal"],
      ["S2+1", "correction"],
      ["S2a+1", "correction"],
      ["S2.1", "split"],
      ["S2a+1.1", "correction-split"],
      ["E2a", "normal"],
      ["E2a+1", "correction"],
    ],
  );
});

test("a correction of a correction cannot even be spelled", () => {
  // The `+N` is allocated by add-row, never chosen by a caller, and the grammar
  // has no second `+` — so `+1+1` is unrepresentable rather than merely refused.
  assert.equal(L.parseRowId("S2+1+1"), null);
  assert.equal(L.parseRowId("S2+0"), null);
  assert.equal(L.parseRowId("S2.0"), null);
});

test("an Exit leaf is never split", () => {
  // Exit Criteria are the human's promises; build decomposes its own work, not
  // the promises it is being measured against.
  assert.equal(L.parseRowId("E2a.1"), null);
  assert.equal(L.parseRowId("E2.1"), null);
  assert.ok(L.parseRowId("E2a+1"), "but a correction Exit leaf is legal");
});

test("the comparator puts a correction after its parent's whole split subtree", () => {
  const ids = ["S3", "S2a+1.1", "S2a", "S2a.2", "S2a.1", "S2a+1", "S2", "S10"];
  assert.deepEqual(
    ids.map(L.parseRowId).sort(L.compareRows).map((r) => r.id),
    ["S2", "S2a", "S2a.1", "S2a.2", "S2a+1", "S2a+1.1", "S3", "S10"],
  );
});

test("only a split makes its parent a roll-up", () => {
  const rows = ["S1", "S1.1", "S2", "S2+1"].map((id) => ({ id, parsed: L.parseRowId(id) }));
  // A split partitions its parent, so the parent's status is derived. A
  // correction is extra work beside the item, so the item stays actionable and
  // keeps owning its own contract.
  assert.deepEqual([...L.rollUpIds(rows)], ["S1"]);
});

test("resume selects the first open deepest leaf, never the roll-up parent", () => {
  const rows = [
    { id: "S1", parsed: L.parseRowId("S1"), status: "done" },
    { id: "S2", parsed: L.parseRowId("S2"), status: "doing" },
    { id: "S2.1", parsed: L.parseRowId("S2.1"), status: "done" },
    { id: "S2.2", parsed: L.parseRowId("S2.2"), status: "pending" },
    { id: "S3", parsed: L.parseRowId("S3"), status: "pending" },
  ];
  assert.equal(L.nextActionableRow(rows).id, "S2.2");
});

test("several rows left doing resume at the first unresolved actionable one", () => {
  const rows = [
    { id: "S1", parsed: L.parseRowId("S1"), status: "doing" },
    { id: "S2", parsed: L.parseRowId("S2"), status: "doing" },
  ];
  assert.equal(L.nextActionableRow(rows).id, "S1");
});

test("a parent's derived status follows its split parts", () => {
  const parts = (...statuses) => statuses.map((status) => ({ status }));
  assert.equal(L.derivedParentStatus(parts("done", "done")), "done");
  assert.equal(L.derivedParentStatus(parts("done", "pending")), "doing");
  assert.equal(L.derivedParentStatus(parts("pending", "pending")), "pending");
  assert.equal(L.derivedParentStatus(parts("doing", "pending")), "doing");
});

test("needs-human ranks with met, so reaching it is never a backwards move", () => {
  assert.ok(L.rank("E", "needs-human") > L.rank("E", "pending"));
  assert.equal(L.rank("E", "needs-human"), L.rank("E", "met"));
  assert.equal(L.rank("S", "done") > L.rank("S", "doing"), true);
});

// ---- brief parsing --------------------------------------------------------

const NESTED_BRIEF = `# Phase Brief — Demo — Phase 1

## Phase Goal

Ship it.

## Phase Scope

1. **Flat item** — the whole behaviour on one line.
2. **Persistence** — data survives a restart
   a. **Write on change** — every mutation is flushed to disk immediately
   b. **Read on start** — the file is loaded once at startup

## Not This Phase

- Networking.

## Exit Criteria

1. **Fresh start**
   a. the file is created
   b. a confirmation is shown
`;

test("a nested Scope leaf keeps its full behaviour line, not just its bolded lead", () => {
  // B1: the ledger label is a scannable handle, but the row's *contract* is the
  // brief's whole line. Keeping only the lead lost the behaviour the row exists
  // to deliver, and nothing downstream could recover it.
  const scope = L.parseScope(NESTED_BRIEF);
  assert.deepEqual(scope.rows.map((r) => r.id), ["S1", "S2a", "S2b"]);
  // The label joins the category, so the table row says which item it belongs to.
  assert.equal(scope.rows[1].label, "Persistence — Write on change");
  assert.equal(
    scope.rows[1].text,
    "Persistence — Write on change — every mutation is flushed to disk immediately",
  );
  assert.equal(scope.rows[0].text, "Flat item — the whole behaviour on one line.");
});

test("Exit Criteria join their category lead into each leaf", () => {
  const exit = L.parseExitCriteria(NESTED_BRIEF);
  assert.deepEqual(exit.rows.map((r) => r.id), ["E1a", "E1b"]);
  assert.equal(exit.rows[0].text, "Fresh start — the file is created");
});

test("duplicate Scope numbers and duplicate Exit letters are both rejected", () => {
  const dupScope = `# Phase Brief — Demo — Phase 1

## Phase Scope

1. **Flat item** — one line.
1. **Also one** — another line.
`;
  assert.match(L.parseScope(dupScope).error, /numbers two Phase Scope items/);

  // B4b: parseScope checked for duplicates and parseExitCriteria did not, so a
  // brief with two `b.` leaves under one category silently produced two E1b rows.
  const dupExit = NESTED_BRIEF.replace("   b. a confirmation is shown", "   a. a confirmation is shown");
  assert.match(L.parseExitCriteria(dupExit).error, /numbers two Exit Criteria leaves/);
});

test("a prose-only section is an error, not an invented split", () => {
  const prose = NESTED_BRIEF.replace(/## Phase Scope\n\n[\s\S]*?\n## Not This Phase/, "## Phase Scope\n\nJust some prose.\n\n## Not This Phase");
  assert.match(L.parseScope(prose).error, /no list to parse/);
});

// ---- contract digest ------------------------------------------------------

test("the contract digest covers exactly the addressed sections", () => {
  const base = L.contractDigest(NESTED_BRIEF);
  assert.match(base, /^[0-9a-f]{16}$/);
  assert.equal(L.contractDigest(NESTED_BRIEF), base, "stable across calls");

  // A section outside the addressed set may change freely.
  assert.equal(
    L.contractDigest(`${NESTED_BRIEF}\n## Acknowledged Risks\n\n- None.\n`),
    base,
    "an unaddressed section does not move the digest",
  );
  for (const edit of [
    ["Ship it.", "Ship something else."],
    ["1. **Flat item**", "1. **Flat thing**"],
    ["- Networking.", "- Networking and auth."],
    ["b. a confirmation is shown", "b. a confirmation appears"],
  ]) {
    assert.notEqual(L.contractDigest(NESTED_BRIEF.replace(...edit)), base, `editing ${edit[0]} must move the digest`);
  }
});

test("the digest normalises line endings and nothing else", () => {
  assert.equal(L.contractDigest(NESTED_BRIEF.replace(/\n/g, "\r\n")), L.contractDigest(NESTED_BRIEF));
  // A whitespace edit inside an addressed section is a brief edit. Smoothing it
  // away would let scope drift under a ledger that still claims to address it.
  assert.notEqual(L.contractDigest(NESTED_BRIEF.replace("Ship it.", "Ship it. ")), L.contractDigest(NESTED_BRIEF));
});

// ---- Row Contracts round-trip ---------------------------------------------

test("row contract text survives pipes, quotes, newlines, backticks, and $()", () => {
  const nasty = [
    'the empty state should say "nothing here yet | add one"',
    "  two   leading spaces and   runs   of   them  ",
    "a `backtick` and $(echo pwned) and 'single' quotes",
    "| a | table | row |",
    "",
    "a trailing blank line above",
  ].join("\n");

  const rendered = L.renderLedger({
    project: "Demo", phaseNumber: 1, owner: null, contract: "0123456789abcdef",
    scope: [{ id: "S1", label: "Store", status: "done" }, { id: "S1.1", label: "part", status: "done" }],
    exit: [{ id: "E1a", label: "It works", status: "pending" }],
    contracts: new Map([["S1.1", { text: nasty }]]),
  });
  const parsed = L.parseLedger(rendered);
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.equal(parsed.ledger.contracts.get("S1.1").text, nasty, "byte for byte");
});

test("text containing a triple-backtick run still round-trips", () => {
  const text = ["reproduce with:", "```sh", "npm test -- --grep 'x|y'", "```", "then read the tail"].join("\n");
  const rendered = L.renderLedger({
    project: "Demo", phaseNumber: 1, owner: null, contract: "0123456789abcdef",
    scope: [{ id: "S1", label: "Store", status: "done" }, { id: "S1.1", label: "part", status: "done" }],
    exit: [{ id: "E1a", label: "It works", status: "pending" }],
    contracts: new Map([["S1.1", { text }]]),
  });
  assert.match(rendered, /````text/, "the fence outgrows the longest run inside");
  const parsed = L.parseLedger(rendered);
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.equal(parsed.ledger.contracts.get("S1.1").text, text);
});

test("attributes never share the fence with authored text", () => {
  // A correction's text is the user's exact words and could legitimately begin
  // with something shaped like `reason:`. Metadata therefore lives outside the
  // fence, and the fence holds the text and nothing else.
  const text = "reason: the user actually wrote this line\nand this one";
  const rendered = L.renderLedger({
    project: "Demo", phaseNumber: 1, owner: null, contract: "0123456789abcdef",
    scope: [{ id: "S1", label: "Store", status: "pending" }, { id: "S1+1", label: "fix", status: "pending" }],
    exit: [{ id: "E1a", label: "It works", status: "pending" }],
    contracts: new Map([["S1+1", { attributes: { affects: "E1a" }, text }]]),
  });
  const parsed = L.parseLedger(rendered);
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  const body = parsed.ledger.contracts.get("S1+1");
  assert.equal(body.attributes.affects, "E1a");
  assert.equal(body.text, text);
});

// ---- fail closed ----------------------------------------------------------

test("a valid minimal ledger parses", () => {
  const parsed = L.parseLedger(MINIMAL);
  assert.ok(parsed.ok, JSON.stringify(parsed.errors));
  assert.equal(parsed.ledger.contract, "0123456789abcdef");
});

test("a versionless ledger is invalid — there is no legacy to migrate", () => {
  const parsed = L.parseLedger(MINIMAL.replace("<!-- mano-progress: v2 -->\n", ""));
  assert.equal(parsed.ok, false);
  assert.match(parsed.errors.join(" "), /not a v2 ledger/);
});

test("each malformed shape is invalid and says why", () => {
  const cases = {
    "no contract digest": MINIMAL.replace(/<!-- contract: .* -->\n/, ""),
    "no heading": MINIMAL.replace("# Progress — Demo — Phase 1\n", ""),
    "two scope tables": `${MINIMAL}\n## Scope\n\n${L.SCOPE_HEADER}\n${L.SCOPE_SEPARATOR}\n| S9 | Extra | pending |\n`,
    "empty scope table": ledgerText({ scope: "", exit: "| E1a | It works | pending |" }),
    "row in the wrong table": ledgerText({
      scope: "| E1a | Store | pending |",
      exit: "| E1b | It works | pending |",
    }),
    "duplicate scope id": ledgerText({
      scope: "| S1 | Store | pending |\n| S1 | Again | pending |",
      exit: "| E1a | It works | pending |",
    }),
    "duplicate exit id": ledgerText({
      scope: "| S1 | Store | pending |",
      exit: "| E1a | It works | pending |\n| E1a | Twice | pending |",
    }),
    "met on a scope row": ledgerText({ scope: "| S1 | Store | met |", exit: "| E1a | It works | pending |" }),
    "done on an exit row": ledgerText({ scope: "| S1 | Store | pending |", exit: "| E1a | It works | done |" }),
    "orphan correction": ledgerText({
      scope: "| S1 | Store | pending |\n| S9+1 | Orphan | pending |",
      exit: "| E1a | It works | pending |",
    }),
    "unaddressed row id": ledgerText({ scope: "| SX | Store | pending |", exit: "| E1a | It works | pending |" }),
  };
  for (const [name, text] of Object.entries(cases)) {
    const parsed = L.parseLedger(text);
    assert.equal(parsed.ok, false, `${name} should be invalid`);
    assert.ok(parsed.errors.length, `${name} should say why`);
  }
});

test("a row that carries its own contract must have one", () => {
  const missing = ledgerText({
    scope: "| S1 | Store | doing |\n| S1.1 | part | pending |",
    exit: "| E1a | It works | pending |",
  });
  assert.match(L.parseLedger(missing).errors.join(" "), /S1\.1 carries its own contract/);
});

test("a scope correction must name an affected Exit Criterion that exists", () => {
  const body = (affects) => `\n### S1+1\n${affects}\n\n${FENCE}text\nfix the empty state\n${FENCE}\n`;
  const unlinked = ledgerText({
    scope: "| S1 | Store | pending |\n| S1+1 | fix | pending |",
    exit: "| E1a | It works | pending |",
    contracts: body(""),
  });
  assert.match(L.parseLedger(unlinked).errors.join(" "), /names no affected Exit Criterion/);

  const orphanLink = ledgerText({
    scope: "| S1 | Store | pending |\n| S1+1 | fix | pending |",
    exit: "| E1a | It works | pending |",
    contracts: body("affects: E9z"),
  });
  assert.match(L.parseLedger(orphanLink).errors.join(" "), /affects E9z, which is not a row/);

  const linked = ledgerText({
    scope: "| S1 | Store | pending |\n| S1+1 | fix | pending |",
    exit: "| E1a | It works | pending |",
    contracts: body("affects: E1a"),
  });
  assert.ok(L.parseLedger(linked).ok, JSON.stringify(L.parseLedger(linked).errors));
});

test("needs-human without a recorded reason is invalid", () => {
  const bare = ledgerText({ scope: "| S1 | Store | done |", exit: "| E1a | It works | needs-human |" });
  assert.match(L.parseLedger(bare).errors.join(" "), /needs-human with no `reason:`/);

  const withReason = ledgerText({
    scope: "| S1 | Store | done |",
    exit: "| E1a | It works | needs-human |",
    contracts: "\n### E1a\nreason: cannot be honestly judged by the implementing agent\n",
  });
  assert.ok(L.parseLedger(withReason).ok, JSON.stringify(L.parseLedger(withReason).errors));
});

test("rework events need unique ids, valid statuses, order, and a dismissal reason", () => {
  const text = (rework, contracts) => ledgerText({
    scope: "| S1 | Store | done |",
    exit: "| E1a | It works | met |",
    rework,
    contracts,
  });
  const contract = (id, extra = "") => `\n### ${id}\n${extra}\n${FENCE}text\ndelete does not confirm\n${FENCE}\n`;

  assert.ok(L.parseLedger(text("| R1 | delete does not confirm | pending |", contract("R1"))).ok);

  assert.match(
    L.parseLedger(text("| R1 | a | pending |\n| R1 | b | pending |", contract("R1"))).errors.join(" "),
    /duplicate row id R1/,
  );
  assert.match(
    L.parseLedger(text("| R2 | a | pending |\n| R1 | b | pending |", `${contract("R1")}${contract("R2")}`)).errors.join(" "),
    /out of order/,
  );
  assert.match(
    L.parseLedger(text("| R1 | a | closed |", contract("R1"))).errors.join(" "),
    /rework takes pending \| resolved \| dismissed/,
  );
  assert.match(
    L.parseLedger(text("| R1 | a | dismissed |", contract("R1"))).errors.join(" "),
    /dismissed with no `dismissed-reason:`/,
  );
  assert.ok(
    L.parseLedger(text("| R1 | a | dismissed |", contract("R1", "dismissed-reason: the user said it is intended"))).ok,
  );
});
