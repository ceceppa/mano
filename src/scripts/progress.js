#!/usr/bin/env node
"use strict";

/**
 * mano progress — the deterministic writer for a phase's build ledger
 * (`_mano_output/phase-<N>/progress.md`).
 *
 * Sibling to stories.js and backlog.js. Same contract, different file — with
 * one addition that is the whole point of this script:
 *
 *   `init` takes no content. It reads the phase brief and emits both tables
 *   itself. The ledger's rows are the human's own `## Phase Scope` items and
 *   `## Exit Criteria` leaves, addressed by their brief numbers. Verbatim
 *   copying stops being a rule a model can violate and becomes a property of a
 *   parser, which deletes a class of drift instead of testing for it.
 *
 * The other commands perform only mechanical edits already decided elsewhere:
 * a status flip `mano build` earned by implementing, a split of the row it is
 * currently building, or a correction row carrying the user's own words. The
 * script never decides what to build or when something is done.
 *
 * Row addressing — one namespace, self-describing:
 *   S<n>      a `## Phase Scope` item                    (pending|doing|done)
 *   S<n><x>   a lettered correction under that item      (pending|doing|done)
 *   S<n>.<k>  a sub-row: build's own split of S<n>       (pending|doing|done)
 *   E<n><x>   an `## Exit Criteria` leaf                  (pending|met)
 *
 * The prefix carries the table, so the split between the two status
 * vocabularies is enforced here rather than trusted: `met` on an S row and
 * `done` on an E row are both errors. Built is not proven.
 *
 * Commands:
 *   init        parse the brief and write both tables (once per phase)
 *   set-status  flip one or more rows; a backwards move needs --reopen
 *   split       append dot-numbered sub-rows under the row being built
 *   add-row     append a lettered correction row carrying the user's words
 *
 * Usage:
 *   node progress.js init --phase 3
 *   node progress.js set-status --phase 3 --row S2 --status done
 *   node progress.js set-status --phase 3 --row S2 --status doing --reopen \
 *        --row E2c --status pending --reopen
 *   node progress.js split --phase 3 --row S2 --part "add + wiring" --part "list + done"
 *   node progress.js add-row --phase 3 --row S2a --text "the user's own words"
 *   node progress.js --help
 *
 * A trailing positional arg is the project root (default: current dir).
 *
 * Exit code 0 only when every requested row was written or already correct. A
 * refusal writes nothing at all, so a caller can trust a successful run.
 */

const fs = require("node:fs");
const path = require("node:path");
const { phaseRef, phaseRouting } = require("./phase.js");

const SCOPE_HEADER = "| # | What | Status |";
const SCOPE_SEPARATOR = "|---|------|--------|";
const EXIT_HEADER = "| # | Criterion | Status |";
const EXIT_SEPARATOR = "|---|-----------|--------|";

const SCOPE_STATUSES = ["pending", "doing", "done"];
const EXIT_STATUSES = ["pending", "met"];

// S2, S2a, S2.1 — the whole address space, in one regex.
const ROW_ID = /^([SE])(\d+)([a-z]*)(?:\.(\d+))?$/;

const HELP = `mano progress — deterministic writer for the configured phase's progress.md

Commands:
  init        parse the phase brief and write both ledger tables (once per phase)
  set-status  flip one or more rows to a new status
  split       append dot-numbered sub-rows under the row being built
  add-row     append a lettered correction row

init:
  --phase N         the configured owner's phase number (required)
  Reads PHASE_DIR/phase-brief.md and emits a Scope row per '## Phase Scope'
  item and an Exit Criteria row per '## Exit Criteria' leaf. Takes no content:
  the rows are the brief's own text. Refuses when a ledger already exists, and
  when either section has no list to parse (route that back to mano start).

set-status:
  --phase N         the configured owner's phase number (required)
  --row <id>        row to flip, repeatable (S2, S2a, S2.1, E2c)
  --status <s>      S rows: pending|doing|done. E rows: pending|met.
  --reopen          required for any backwards move (done -> doing, met -> pending)
  A --status applies to every --row before it that has none yet, so both
  '--row S2 --row S3 --status done' and '--row S2 --status doing --reopen
  --row E2c --status pending --reopen' mean what they look like.

split:
  --phase N         the configured owner's phase number (required)
  --row S<n>        the row being built; must exist and be 'doing'
  --part "..."      one sub-row, repeatable (required)
  The first split of a row records its first part as already done — a split is
  only legitimate once one part is complete. Later splits append as pending.

add-row:
  --phase N         the configured owner's phase number (required)
  --row <id>        a lettered row under an existing item (S2a, E2e)
  --text "..."      the row's text, copied from the user's own words (required)

A trailing positional argument = project root (default: current dir).

This script owns the ledger row format and performs only edits already decided
by the human and the skill — it never decides scope, or when work is done.`;

// ---- args -----------------------------------------------------------------

function parseArgs(argv) {
  const args = {
    command: null, root: process.cwd(), help: false,
    phase: null, entries: [], parts: [], text: null,
  };
  let current = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") args.help = true;
    else if (a === "--phase") args.phase = argv[++i];
    else if (a === "--row") {
      current = { row: argv[++i], status: null, reopen: false };
      args.entries.push(current);
    } else if (a === "--status") {
      const status = argv[++i];
      // Bind to every row that has no status yet, so a shared trailing
      // --status and per-row pairing both read the way they look.
      const open = args.entries.filter((e) => e.status === null);
      for (const e of open) e.status = status;
      if (open.length === 0) args.danglingStatus = status;
    } else if (a === "--reopen") {
      if (current) current.reopen = true;
      else args.danglingReopen = true;
    } else if (a === "--part") args.parts.push(argv[++i]);
    else if (a === "--text") args.text = argv[++i];
    else if (a === "--root") args.root = path.resolve(argv[++i]);
    else if (!a.startsWith("-")) {
      if (!args.command) args.command = a;
      else args.root = path.resolve(a);
    }
  }
  return args;
}

function fail(msg) {
  process.stderr.write(`[mano build] ${msg}\n`);
  process.exit(1);
}

function readText(p) {
  try { return fs.readFileSync(p, "utf8"); } catch { return null; }
}

function configuredPhase(args) {
  if (args.phase == null || !/^\d+$/.test(String(args.phase)) || Number(args.phase) < 1) {
    fail(`${args.command} needs --phase <N> (a positive integer).`);
  }
  try {
    return phaseRef(phaseRouting(args.root).owner, Number(args.phase));
  } catch (error) {
    fail(`${args.command}: ${error.message}`);
  }
}

function progressPath(root, ref) {
  return path.join(root, ref.relativeDir, "progress.md");
}

function briefPath(root, ref) {
  return path.join(root, ref.relativeDir, "phase-brief.md");
}

// ---- row addressing -------------------------------------------------------

function parseRowId(id) {
  const m = ROW_ID.exec(String(id == null ? "" : id).trim());
  if (!m) return null;
  const sub = m[4] === undefined ? 0 : Number(m[4]);
  if (m[1] === "E" && sub) return null; // dots are build's own decomposition; E leaves are the human's
  return { table: m[1], number: Number(m[2]), letters: m[3], sub, id: `${m[1]}${m[2]}${m[3]}${sub ? `.${sub}` : ""}` };
}

// Sorts S2 < S2.1 < S2.2 < S2a < S3 < S10: number, then decomposition, then
// lettered corrections. Dots and letters are separate namespaces on purpose.
function rowKey(parsed) {
  return [parsed.number, parsed.letters, parsed.sub];
}

function keyLess(a, b) {
  const ka = rowKey(a), kb = rowKey(b);
  if (ka[0] !== kb[0]) return ka[0] < kb[0];
  if (ka[1] !== kb[1]) return ka[1] < kb[1];
  return ka[2] < kb[2];
}

// One mechanical transform, applied to every cell: a ledger cell is one line
// and cannot contain the column separator. It never shortens or rewords.
function cell(value) {
  return String(value).replace(/\r?\n/g, " ").replace(/\|/g, " / ").replace(/\s+/g, " ").trim();
}

function formatRow(id, label, status) {
  return `| ${cell(id)} | ${cell(label)} | ${cell(status)} |`;
}

function rowCells(line) {
  if (!line.includes("|")) return null;
  const cells = line.split("|").map((c) => c.trim());
  while (cells.length && cells[0] === "") cells.shift();
  while (cells.length && cells[cells.length - 1] === "") cells.pop();
  return cells;
}

// A ledger data row = a table row whose first cell is a row id.
function rowIdOf(line) {
  const cells = rowCells(line);
  if (!cells || cells.length < 3) return null;
  return parseRowId(cells[0]);
}

// ---- brief parsing (init's whole job) -------------------------------------

const LIST_ITEM = /^(\s*)(?:(\d+)[.)]|([a-z])[.)]|[-*+])\s+(.*)$/;

// The lines under `## <heading>`, up to the next `##` heading. HTML comments
// (the template's own guidance) are not content.
function sectionLines(text, heading) {
  const lines = String(text).split("\n");
  const start = lines.findIndex((l) => new RegExp(`^##\\s+${heading}\\s*$`, "i").test(l.trim()));
  if (start === -1) return null;
  const out = [];
  for (let i = start + 1; i < lines.length; i++) {
    if (/^##\s+/.test(lines[i])) break;
    out.push(lines[i]);
  }
  // Drop the template's own guidance comments, including multi-line ones.
  return out.join("\n").replace(/<!--[\s\S]*?-->/g, "").split("\n");
}

// Flatten a section into list items with their nesting depth. A non-list line
// that follows an item is that item's continuation (a wrapped sentence).
function listItems(lines) {
  const items = [];
  for (const line of lines) {
    if (!line.trim()) continue;
    const m = LIST_ITEM.exec(line);
    if (m) {
      items.push({
        indent: m[1].replace(/\t/g, "    ").length,
        number: m[2] ? Number(m[2]) : null,
        letter: m[3] || null,
        text: m[4].trim(),
      });
    } else if (items.length) {
      items[items.length - 1].text += ` ${line.trim()}`;
    }
  }
  return items;
}

// Two levels, capped: top-level items and their direct children. Anything
// deeper folds into the child's own text — an unbounded tree has no stable
// address scheme.
function tree(items) {
  if (items.length === 0) return [];
  const top = Math.min(...items.map((i) => i.indent));
  const roots = [];
  let childIndent = null;
  for (const item of items) {
    if (item.indent === top) {
      roots.push({ ...item, children: [] });
      childIndent = null;
      continue;
    }
    if (roots.length === 0) continue; // indented text before any item
    const parent = roots[roots.length - 1];
    if (childIndent === null) childIndent = item.indent;
    if (item.indent <= childIndent) parent.children.push({ ...item, children: [] });
    else if (parent.children.length) {
      const last = parent.children[parent.children.length - 1];
      last.text += `; ${item.text}`;
    } else parent.children.push({ ...item, children: [] });
  }
  return roots;
}

// `**Short title** — the full behaviour line` -> "Short title". The lead is
// how a ledger row gets a scannable handle without anything paraphrasing the
// brief. No lead is fine: the whole line becomes the label, long but never wrong.
function boldLead(text) {
  const m = /^\*\*([^*]+)\*\*(?:\s*[—–-]\s*.+)?$/.exec(text.trim());
  return m ? m[1].trim() : null;
}

function stripMarkers(text) {
  return text.replace(/\*\*/g, "").trim();
}

function letterFor(index) {
  let n = index, out = "";
  do { out = String.fromCharCode(97 + (n % 26)) + out; n = Math.floor(n / 26) - 1; } while (n >= 0);
  return out;
}

// Numbers come from the brief when the brief numbered them; otherwise document
// order. Nothing here invents a split, and nothing shortens by judgment.
function numberRoots(roots) {
  const allNumbered = roots.every((r) => r.number !== null);
  return roots.map((r, i) => ({ ...r, num: allNumbered ? r.number : i + 1 }));
}

function parseScope(briefText) {
  const lines = sectionLines(briefText, "Phase Scope");
  if (lines === null) return { error: "the brief has no `## Phase Scope` section" };
  const roots = numberRoots(tree(listItems(lines)));
  if (roots.length === 0) {
    return { error: "`## Phase Scope` has no list to parse — only prose" };
  }
  const rows = [];
  for (const root of roots) {
    if (root.children.length === 0) {
      rows.push({ id: `S${root.num}`, label: boldLead(root.text) || stripMarkers(root.text), status: "pending" });
    } else {
      // A nested scope item: its leaves are the rows, the parent is the address.
      const lettered = root.children.every((c) => c.letter !== null);
      root.children.forEach((child, i) => {
        rows.push({
          id: `S${root.num}${lettered ? child.letter : letterFor(i)}`,
          label: boldLead(child.text) || stripMarkers(child.text),
          status: "pending",
        });
      });
    }
  }
  const seen = new Set();
  for (const row of rows) {
    if (seen.has(row.id)) return { error: `the brief numbers two Phase Scope items ${row.id.slice(1)}` };
    seen.add(row.id);
  }
  return { rows };
}

function parseExitCriteria(briefText) {
  const lines = sectionLines(briefText, "Exit Criteria");
  if (lines === null) return { error: "the brief has no `## Exit Criteria` section" };
  const roots = numberRoots(tree(listItems(lines)));
  if (roots.length === 0) {
    return { error: "`## Exit Criteria` has no list to parse — only prose" };
  }
  const rows = [];
  for (const root of roots) {
    const lead = boldLead(root.text);
    if (root.children.length === 0) {
      rows.push({ id: `E${root.num}`, label: stripMarkers(root.text), status: "pending" });
      continue;
    }
    const lettered = root.children.every((c) => c.letter !== null);
    root.children.forEach((child, i) => {
      const leaf = stripMarkers(child.text);
      rows.push({
        id: `E${root.num}${lettered ? child.letter : letterFor(i)}`,
        label: lead ? `${lead} — ${leaf}` : leaf,
        status: "pending",
      });
    });
  }
  return { rows };
}

function projectName(briefText) {
  const m = /^#\s+Phase Brief\s+—\s+(.+?)\s+—\s+Phase\s+\d+/m.exec(String(briefText));
  return m ? m[1].trim() : null;
}

// ---- ledger read/write ----------------------------------------------------

function renderLedger(project, ref, scopeRows, exitRows) {
  const title = `# Progress — ${project ? `${project} — ` : ""}Phase ${ref.number}${ref.owner ? ` — Owner: ${ref.owner}` : ""}`;
  const L = [title, "", "## Scope", SCOPE_HEADER, SCOPE_SEPARATOR];
  for (const r of scopeRows) L.push(formatRow(r.id, r.label, r.status));
  L.push("", "## Exit Criteria", EXIT_HEADER, EXIT_SEPARATOR);
  for (const r of exitRows) L.push(formatRow(r.id, r.label, r.status));
  return L.join("\n") + "\n";
}

function loadLedger(file) {
  const text = readText(file);
  if (text === null) return null;
  const lines = text.split("\n");
  const rows = [];
  for (let i = 0; i < lines.length; i++) {
    const parsed = rowIdOf(lines[i]);
    if (!parsed) continue;
    const cells = rowCells(lines[i]);
    rows.push({ line: i, parsed, id: parsed.id, label: cells[1], status: (cells[2] || "").toLowerCase() });
  }
  return { lines, rows };
}

function findRow(ledger, id) {
  return ledger.rows.find((r) => r.id.toLowerCase() === String(id).toLowerCase()) || null;
}

function statusesFor(table) {
  return table === "S" ? SCOPE_STATUSES : EXIT_STATUSES;
}

function rank(table, status) {
  return statusesFor(table).indexOf(String(status).toLowerCase());
}

// ---- init -----------------------------------------------------------------

function cmdInit(args) {
  const ref = configuredPhase(args);
  const file = progressPath(args.root, ref);
  if (fs.existsSync(file)) {
    fail(`init: ${ref.relativeDir}/progress.md already exists — the ledger is written once and stays authoritative. Use set-status, split, or add-row.`);
  }
  const brief = readText(briefPath(args.root, ref));
  if (brief === null) {
    fail(`init: no phase brief at ${ref.relativeDir}/phase-brief.md — run mano start first.`);
  }

  const scope = parseScope(brief);
  const exit = parseExitCriteria(brief);
  const problems = [scope.error, exit.error].filter(Boolean);
  if (problems.length) {
    fail(
      `init: cannot parse the brief — ${problems.join("; ")}. ` +
      "The ledger is the brief's own list; inventing the split is not this script's job or the build's. " +
      "Route it to mano start to give the brief a numbered Phase Scope and lettered Exit Criteria.",
    );
  }

  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, renderLedger(projectName(brief), ref, scope.rows, exit.rows));
  process.stdout.write(
    `[mano build] init → ${ref.relativeDir}/progress.md, ${scope.rows.length} scope row(s), ${exit.rows.length} exit criterion row(s)\n`,
  );
  for (const r of scope.rows) process.stdout.write(`  + ${r.id.padEnd(5)} ${r.label}\n`);
  for (const r of exit.rows) process.stdout.write(`  + ${r.id.padEnd(5)} ${r.label}\n`);
}

// ---- set-status -----------------------------------------------------------

function cmdSetStatus(args) {
  const ref = configuredPhase(args);
  if (args.entries.length === 0) fail("set-status needs at least one --row <id>.");
  if (args.danglingStatus) fail("set-status: a --status must follow the --row it applies to.");

  const file = progressPath(args.root, ref);
  const ledger = loadLedger(file);
  if (!ledger) fail(`set-status: no ledger at ${ref.relativeDir}/progress.md. Run 'progress.js init --phase ${ref.number}' first.`);

  // Validate every entry before writing anything: a partial status write would
  // leave the ledger claiming something no caller asked for.
  const plan = [];
  for (const entry of args.entries) {
    const parsed = parseRowId(entry.row);
    if (!parsed) fail(`set-status: "${entry.row}" is not a row address (S2, S2a, S2.1, E2c).`);
    if (entry.status === null) fail(`set-status: --row ${parsed.id} has no --status.`);
    const status = String(entry.status).trim().toLowerCase();
    const allowed = statusesFor(parsed.table);
    if (!allowed.includes(status)) {
      const other = parsed.table === "S" ? EXIT_STATUSES : SCOPE_STATUSES;
      const hint = other.includes(status)
        ? ` '${status}' belongs to the ${parsed.table === "S" ? "Exit Criteria" : "Scope"} table — built is not proven.`
        : "";
      fail(`set-status: ${parsed.id} takes ${allowed.join(" | ")}, not "${status}".${hint}`);
    }
    const row = findRow(ledger, parsed.id);
    if (!row) fail(`set-status: no row ${parsed.id} in ${ref.relativeDir}/progress.md; no statuses changed.`);
    const backwards = rank(parsed.table, status) < rank(parsed.table, row.status);
    if (backwards && !entry.reopen) {
      fail(
        `set-status: ${parsed.id} would move backwards (${row.status} → ${status}) without --reopen. ` +
        "A reopened row is a deviation the human must see; pass --reopen and report it.",
      );
    }
    if (parsed.table === "S" && parsed.sub === 0 && status === "done") {
      const openSubs = ledger.rows.filter(
        (r) => r.parsed.table === "S" && r.parsed.number === parsed.number &&
          r.parsed.letters === parsed.letters && r.parsed.sub > 0 && r.status !== "done",
      );
      if (openSubs.length) {
        fail(`set-status: ${parsed.id} has sub-rows that are not done (${openSubs.map((r) => r.id).join(", ")}); a parent flips only when its split is complete.`);
      }
    }
    plan.push({ row, parsed, status, reopen: entry.reopen, was: row.status });
  }

  const changed = [];
  for (const step of plan) {
    if (step.was.toLowerCase() === step.status) continue;
    ledger.lines[step.row.line] = formatRow(step.row.id, step.row.label, step.status);
    step.row.status = step.status;
    changed.push(step);
  }

  // A parent whose split just completed is done by definition — the sub-rows
  // are a partition of it, so leaving it open would misreport the phase.
  const promoted = [];
  for (const step of plan) {
    if (step.parsed.table !== "S" || step.parsed.sub === 0 || step.status !== "done") continue;
    const parentId = `S${step.parsed.number}${step.parsed.letters}`;
    const parent = findRow(ledger, parentId);
    if (!parent || parent.status === "done") continue;
    const siblings = ledger.rows.filter(
      (r) => r.parsed.table === "S" && r.parsed.number === step.parsed.number &&
        r.parsed.letters === step.parsed.letters && r.parsed.sub > 0,
    );
    if (siblings.every((r) => r.status === "done")) {
      ledger.lines[parent.line] = formatRow(parent.id, parent.label, "done");
      parent.status = "done";
      promoted.push({ id: parent.id });
    }
  }

  if (changed.length || promoted.length) fs.writeFileSync(file, ledger.lines.join("\n"));

  process.stdout.write(
    `[mano build] set-status → ${changed.length} row(s) set` +
    (plan.length - changed.length ? `, ${plan.length - changed.length} unchanged` : "") + "\n",
  );
  for (const step of plan) {
    if (step.was.toLowerCase() === step.status) process.stdout.write(`  ~ ${step.row.id} (already '${step.status}', left as-is)\n`);
    else process.stdout.write(`  ${step.reopen ? "!" : "+"} ${step.row.id} (${step.was} → ${step.status})${step.reopen ? " [reopened — report this]" : ""}\n`);
  }
  for (const p of promoted) process.stdout.write(`  + ${p.id} (→ done, its split is complete)\n`);
}

// ---- shared insert --------------------------------------------------------

// Insert a row in address order inside the table its prefix names.
function insertRow(ledger, parsed, label, status) {
  const table = parsed.table;
  const siblings = ledger.rows.filter((r) => r.parsed.table === table);
  let at;
  if (siblings.length) {
    const after = siblings.find((r) => keyLess(parsed, r.parsed));
    at = after ? after.line : siblings[siblings.length - 1].line + 1;
  } else {
    const header = table === "S" ? SCOPE_HEADER : EXIT_HEADER;
    const idx = ledger.lines.findIndex((l) => l.trim() === header);
    if (idx === -1) return false;
    at = idx + 2;
  }
  ledger.lines.splice(at, 0, formatRow(parsed.id, label, status));
  for (const r of ledger.rows) if (r.line >= at) r.line++;
  ledger.rows.push({ line: at, parsed, id: parsed.id, label, status });
  ledger.rows.sort((a, b) => a.line - b.line);
  return true;
}

// ---- split ----------------------------------------------------------------

function cmdSplit(args) {
  const ref = configuredPhase(args);
  if (args.entries.length !== 1) fail("split needs exactly one --row S<n>.");
  const parsed = parseRowId(args.entries[0].row);
  if (!parsed || parsed.table !== "S" || parsed.sub !== 0) {
    fail(`split: "${args.entries[0].row}" is not a scope row to split (S2, S2a). Exit Criteria are the human's leaves and are never split.`);
  }
  if (args.parts.length === 0) fail("split needs at least one --part \"...\".");

  const file = progressPath(args.root, ref);
  const ledger = loadLedger(file);
  if (!ledger) fail(`split: no ledger at ${ref.relativeDir}/progress.md.`);
  const parent = findRow(ledger, parsed.id);
  if (!parent) fail(`split: no row ${parsed.id} in ${ref.relativeDir}/progress.md.`);
  if (parent.status !== "doing") {
    fail(
      `split: ${parsed.id} is '${parent.status}' — only the row currently being built may be split. ` +
      "Build cannot pre-decompose the ledger.",
    );
  }

  const existing = ledger.rows.filter(
    (r) => r.parsed.table === "S" && r.parsed.number === parsed.number &&
      r.parsed.letters === parsed.letters && r.parsed.sub > 0,
  );
  let next = existing.length ? Math.max(...existing.map((r) => r.parsed.sub)) + 1 : 1;
  const added = [];
  for (let i = 0; i < args.parts.length; i++) {
    const text = String(args.parts[i]).trim();
    if (!text) fail("split: a --part cannot be empty.");
    // The first part of a first split is the one already finished — a split is
    // legitimate only after a part is complete, so the ledger records that.
    const status = existing.length === 0 && i === 0 ? "done" : "pending";
    const sub = parseRowId(`S${parsed.number}${parsed.letters}.${next++}`);
    insertRow(ledger, sub, text, status);
    added.push({ id: sub.id, text, status });
  }

  fs.writeFileSync(file, ledger.lines.join("\n"));
  process.stdout.write(`[mano build] split → ${parsed.id} into ${added.length} sub-row(s)\n`);
  for (const a of added) process.stdout.write(`  + ${a.id.padEnd(6)} ${a.status.padEnd(7)} ${a.text}\n`);
  process.stdout.write("  Sub-rows are the only ledger text build composes — show them to the human before writing more code.\n");
}

// ---- add-row --------------------------------------------------------------

function cmdAddRow(args) {
  const ref = configuredPhase(args);
  if (args.entries.length !== 1) fail("add-row needs exactly one --row <id>.");
  const parsed = parseRowId(args.entries[0].row);
  if (!parsed) fail(`add-row: "${args.entries[0].row}" is not a row address (S2a, E2e).`);
  if (parsed.sub !== 0) fail("add-row: dot-numbered sub-rows come from split, not add-row.");
  if (!parsed.letters) {
    fail(
      `add-row: ${parsed.id} has no letter. A correction is a lettered row under an item the brief already contains ` +
      "(S2a, E2e); a new top-level item is new scope and goes through mano start.",
    );
  }
  if (!args.text || !String(args.text).trim()) fail("add-row needs --text \"...\" — the user's own words, not a paraphrase.");

  const file = progressPath(args.root, ref);
  const ledger = loadLedger(file);
  if (!ledger) fail(`add-row: no ledger at ${ref.relativeDir}/progress.md.`);
  if (findRow(ledger, parsed.id)) fail(`add-row: ${parsed.id} already exists; row text is immutable.`);

  const family = ledger.rows.filter((r) => r.parsed.table === parsed.table && r.parsed.number === parsed.number);
  if (family.length === 0) {
    fail(
      `add-row: nothing in the ledger is numbered ${parsed.table}${parsed.number}, so ${parsed.id} would be new scope, ` +
      "not a correction. Route it to mano start (amend the brief) or the backlog.",
    );
  }

  const status = "pending";
  insertRow(ledger, parsed, String(args.text).trim(), status);
  fs.writeFileSync(file, ledger.lines.join("\n"));
  process.stdout.write(`[mano build] add-row → 1 written\n  + ${parsed.id.padEnd(5)} ${status.padEnd(7)} ${String(args.text).trim()}\n`);
  process.stdout.write("  A correction the brief did not authorise — run the gap check against it and show it to the human before code.\n");
}

// ---- main -----------------------------------------------------------------

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.command) {
    process.stdout.write(HELP + "\n");
    process.exit(args.help ? 0 : 1);
  }
  if (args.command === "init") cmdInit(args);
  else if (args.command === "set-status") cmdSetStatus(args);
  else if (args.command === "split") cmdSplit(args);
  else if (args.command === "add-row") cmdAddRow(args);
  else fail(`unknown command "${args.command}". Use init, set-status, split, or add-row (--help for usage).`);
}

if (require.main === module) main();

module.exports = {
  SCOPE_HEADER, SCOPE_SEPARATOR, EXIT_HEADER, EXIT_SEPARATOR,
  SCOPE_STATUSES, EXIT_STATUSES, ROW_ID,
  parseArgs, parseRowId, rowKey, keyLess, cell, formatRow, rowCells, rowIdOf,
  sectionLines, listItems, tree, boldLead, letterFor,
  parseScope, parseExitCriteria, projectName, renderLedger, loadLedger,
  progressPath, briefPath, main,
};
