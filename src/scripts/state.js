#!/usr/bin/env node
"use strict";

/**
 * mano state — a read-only projection of a project's _mano_output/ state.
 *
 * Replaces the in-prompt file-scanning `mano start` does to decide its path.
 * The agent runs this once and reads a deterministic verdict instead of
 * grepping the backlog / stories index / reviews by hand (which is unreliable —
 * the backlog Status line is `- **Status:** backlog`, and bare `grep "Status:
 * backlog"` misses it).
 *
 * IMPORTANT — this script is a *projection*, not a source of truth. It only
 * reads. It must never write a "current phase" or any state file: the
 * filesystem under _mano_output/ stays the single source of truth. The verdict
 * is advice for the agent; the skill still owns the decision (e.g. an explicit
 * "scope the next phase anyway" from the user overrides a BLOCK).
 *
 * Usage:
 *   node state.js                 scan ./_mano_output
 *   node state.js <projectRoot>   scan <projectRoot>/_mano_output
 *   node state.js --scope         on a PROCEED to scope-backlog, also print the
 *                                 scope input (backlog items + principles +
 *                                 latest review) so the skill needn't reopen files
 *   node state.js --json          machine-readable output
 *   node state.js --help
 *
 * Exit code is always 0 on a successful scan (including "no project") — a
 * verdict is data, not a failure. Non-zero only on an unexpected I/O error.
 */

const fs = require("node:fs");
const path = require("node:path");

function parseArgs(argv) {
  const args = { root: process.cwd(), json: false, verbose: false, scope: false, help: false };
  for (const a of argv) {
    if (a === "--json") args.json = true;
    else if (a === "--verbose" || a === "-v") args.verbose = true;
    else if (a === "--scope") args.scope = true;
    else if (a === "--help" || a === "-h") args.help = true;
    else if (!a.startsWith("-")) args.root = path.resolve(a);
  }
  return args;
}

const HELP = `mano state — read-only projection of _mano_output/ for mano start

Usage:
  node state.js [projectRoot] [--scope] [--verbose] [--json]

  projectRoot   directory containing _mano_output/ (default: current dir)
  --scope       on a PROCEED to scope-backlog, also print the scope input —
                the Status: backlog items, core principles, and latest review
  --verbose     also print the evidence (phase, stories, reviewed, backlog)
  --json        emit the full structured state as JSON

By default prints a go/no-go for mano start: a DECISION (PROCEED | STOP), a
NEXT hint when proceeding (scope-backlog | conversation | resume-draft), a PHASE
number (the phase to scope or resume, so the skill needn't ls for it), and a
one-line reason. Run with --verbose to see why. Read-only: writes nothing.`;

// ---- small fs helpers (never throw on missing) ----------------------------

function exists(p) {
  try { return fs.existsSync(p); } catch { return false; }
}

function readText(p) {
  try { return fs.readFileSync(p, "utf8"); } catch { return null; }
}

function listDirs(p) {
  try {
    return fs.readdirSync(p, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name);
  } catch { return []; }
}

// ---- parsers (one per format, kept tiny and faithful) ---------------------

// Highest-numbered phase-[N] folder. Returns null if none.
function latestPhase(outputDir) {
  let max = null;
  for (const name of listDirs(outputDir)) {
    const m = /^phase-(\d+)$/.exec(name);
    if (m) {
      const n = Number(m[1]);
      if (max === null || n > max) max = n;
    }
  }
  return max;
}

// Stories index: | # | Story | File | Status |. A row counts as a story when
// its first cell is an integer. Returns { total, done, openTitles } or null if
// the index is absent.
function readStories(storiesReadme) {
  const text = readText(storiesReadme);
  if (text === null) return null;
  let total = 0, done = 0;
  const openTitles = [];
  for (const line of text.split("\n")) {
    if (!line.includes("|")) continue;
    const cells = line.split("|").map((c) => c.trim());
    // Drop leading/trailing empties from the outer pipes.
    while (cells.length && cells[0] === "") cells.shift();
    while (cells.length && cells[cells.length - 1] === "") cells.pop();
    if (cells.length < 4) continue;
    if (!/^\d+$/.test(cells[0])) continue; // header / separator / non-story row
    total++;
    const status = cells[cells.length - 1].toLowerCase();
    if (status === "done") done++;
    else openTitles.push(`${cells[0]} ${cells[1]} (${status || "—"})`);
  }
  return { total, done, openTitles };
}

// Backlog Status counts. Matches `- **Status:** <value>` exactly (the format
// that bare greps miss). Takes the file's text; returns counts keyed by raw
// status value ({} when the backlog is absent).
function countBacklogStatuses(text) {
  const counts = {}; // e.g. { backlog: 1, "in-phase-8": 0, resolved: 24 }
  if (text === null) return counts;
  const re = /^\s*-\s*\*\*Status:\*\*\s*(.+?)\s*$/gim;
  let m;
  while ((m = re.exec(text)) !== null) {
    const v = m[1].trim().toLowerCase();
    counts[v] = (counts[v] || 0) + 1;
  }
  return counts;
}

// Backlog items are `### title` blocks, each carrying a `- **Status:** <value>`
// line. Returns the full text block of every item whose status matches
// `wantStatus` (e.g. "backlog"), in file order. A `##` heading (e.g. the
// Core Product Principles section) ends the preceding item.
function extractBacklogItems(text, wantStatus) {
  if (text === null) return [];
  const out = [];
  let cur = null; // { lines: [] }
  const flush = () => {
    if (!cur) return;
    const block = cur.lines.join("\n").replace(/\s+$/, "");
    const m = /^\s*-\s*\*\*Status:\*\*\s*(.+?)\s*$/im.exec(block);
    const status = m ? m[1].trim().toLowerCase() : null;
    if (!wantStatus || status === wantStatus) out.push(block);
    cur = null;
  };
  for (const line of text.split("\n")) {
    if (/^###\s+/.test(line)) { flush(); cur = { lines: [line] }; }
    else if (/^##\s+/.test(line)) { flush(); }   // a higher heading ends an item
    else if (cur) cur.lines.push(line);
  }
  flush();
  return out;
}

// The `## Core Product Principles` section (heading + body up to the next `##`
// heading), or null if absent.
function extractCoreProductPrinciples(text) {
  if (text === null) return null;
  let out = null;
  for (const line of text.split("\n")) {
    if (out === null) {
      if (/^##\s+Core Product Principles\b/i.test(line)) out = [line];
    } else if (/^##\s+/.test(line)) {
      break; // next section
    } else {
      out.push(line);
    }
  }
  return out ? out.join("\n").replace(/\s+$/, "") : null;
}

// The latest `## Phase N Review` section's text. Prefers the section for phase
// `n` (the phase just closed); falls back to the highest-numbered review.
// null when reviews.md has none.
function extractLatestReview(text, n) {
  if (text === null) return null;
  const heading = /^##\s+Phase\s+(\d+)\s+Review\b/i;
  const sections = [];
  let cur = null;
  for (const line of text.split("\n")) {
    const m = heading.exec(line);
    if (m) { if (cur) sections.push(cur); cur = { phase: Number(m[1]), lines: [line] }; }
    else if (cur) {
      if (/^##\s+/.test(line)) { sections.push(cur); cur = null; } // non-review h2 ends it
      else cur.lines.push(line);
    }
  }
  if (cur) sections.push(cur);
  if (sections.length === 0) return null;
  let pick = n !== null ? sections.find((sec) => sec.phase === n) : null;
  if (!pick) pick = sections.reduce((a, b) => (b.phase >= a.phase ? b : a));
  return pick.lines.join("\n").replace(/\s+$/, "");
}

// True if reviews.md text has a `## Phase N Review` heading.
function hasReviewEntry(text, n) {
  if (text === null) return false;
  const re = new RegExp(`^##\\s+Phase\\s+${n}\\s+Review\\b`, "im");
  return re.test(text);
}

// ---- state assembly -------------------------------------------------------

function scan(projectRoot) {
  const outputDir = path.join(projectRoot, "_mano_output");
  const s = {
    projectRoot,
    outputDir,
    outputExists: exists(outputDir),
    phase: null,            // latest phase number, or null
    briefExists: false,
    stories: null,          // { total, done, openTitles } or null
    reviewEntry: false,
    backlog: null,          // status counts, or null
    backlogItems: 0,        // Status: backlog count
    inPhaseRemaining: 0,    // Status: in-phase-<phase> count
    _backlogText: null,     // raw text, kept for scope extraction; not serialized
    _reviewsText: null,
  };

  if (!s.outputExists) return finalize(s);

  s._backlogText = readText(path.join(outputDir, "backlog.md"));
  s._reviewsText = readText(path.join(outputDir, "reviews.md"));
  s.backlog = countBacklogStatuses(s._backlogText);
  s.backlogItems = s.backlog["backlog"] || 0;

  const n = latestPhase(outputDir);
  s.phase = n;

  if (n !== null) {
    const phaseDir = path.join(outputDir, `phase-${n}`);
    s.briefExists = exists(path.join(phaseDir, "phase-brief.md"));
    s.stories = readStories(path.join(phaseDir, "stories", "README.md"));
    s.reviewEntry = hasReviewEntry(s._reviewsText, n);
    s.inPhaseRemaining = s.backlog[`in-phase-${n}`] || 0;
  }

  return finalize(s);
}

// Derive the verdict from raw signals, faithful to mano start's gate.
function finalize(s) {
  const storiesAllDone = !!(s.stories && s.stories.total > 0 && s.stories.done === s.stories.total);
  const storiesMissing = !s.stories || s.stories.total === 0;
  // Gate condition 3: reviewed/closed — a review entry, and/or in-phase items resolved.
  const closed = s.reviewEntry || s.inPhaseRemaining === 0;

  let verdict, action;

  if (!s.outputExists) {
    verdict = "NEW_PROJECT";
    action = "No project yet. mano start takes Path B (conversation) — or run `mano import <doc>` first if a PRD/document exists, then Path A.";
  } else if (s.phase === null) {
    // Output dir exists but no phase folder (e.g. fresh `mano import`).
    if (s.backlogItems > 0) {
      verdict = "READY_FIRST_PHASE";
      action = `Backlog has ${s.backlogItems} item(s) and no phase exists yet. mano start scopes phase 1 (Path A).`;
    } else {
      verdict = "NEW_PROJECT";
      action = "An _mano_output/ scaffold exists but the backlog is empty and no phase started. mano start takes Path B (conversation), or `mano import <doc>` to populate the backlog first.";
    }
  } else if (!s.briefExists) {
    // Edge case: phase folder without a brief — a prior start didn't finalise.
    verdict = "RESUME_DRAFT";
    action = `phase-${s.phase}/ exists without phase-brief.md — a previous mano start didn't finalise. Resume drafting phase ${s.phase}; do NOT start a new phase.`;
  } else if (storiesMissing) {
    verdict = "PHASE_IN_PROGRESS";
    action = `Phase ${s.phase} has a brief but no stories yet. Not complete — run mano stories. mano start must NOT scope a next phase.`;
  } else if (!storiesAllDone) {
    verdict = "PHASE_IN_PROGRESS";
    action = `Phase ${s.phase} has open stories (${s.stories.done}/${s.stories.total} done). Not complete — run mano dev. mano start must NOT scope a next phase.`;
  } else if (!closed) {
    verdict = "PHASE_BUILT_NOT_CLOSED";
    action = `Phase ${s.phase} is built (stories all done) but not closed — no review entry and ${s.inPhaseRemaining} item(s) still in-phase-${s.phase}. Run mano review. mano start must NOT scope a next phase.`;
  } else {
    // Phase complete.
    if (s.backlogItems > 0) {
      verdict = "READY_NEXT_PHASE";
      action = `Phase ${s.phase} is complete. mano start may scope phase ${s.phase + 1} from the ${s.backlogItems} backlog item(s) (Path A).`;
    } else {
      verdict = "COMPLETE_BACKLOG_EMPTY";
      action = `Phase ${s.phase} is complete and no items have Status: backlog. Nothing to scope — add backlog items (or mano import a doc) before mano start.`;
    }
    if (storiesAllDone && !s.reviewEntry) {
      action += " (Note: closure inferred from no remaining in-phase items; no review entry found in reviews.md.)";
    }
  }

  // Collapse the verdict to the only thing mano start branches on: go/no-go,
  // plus which path to take when going. The verdict + evidence remain for the
  // human (and --json), but the skill consumes just decision + next.
  const NEXT_BY_VERDICT = {
    READY_FIRST_PHASE: "scope-backlog",
    READY_NEXT_PHASE: "scope-backlog",
    RESUME_DRAFT: "resume-draft",
    NEW_PROJECT: "conversation",
  };
  const proceeds = Object.prototype.hasOwnProperty.call(NEXT_BY_VERDICT, verdict);

  s.storiesAllDone = storiesAllDone;
  s.closed = closed;
  s.verdict = verdict;
  s.action = action;
  s.decision = proceeds ? "PROCEED" : "STOP";
  s.next = proceeds ? NEXT_BY_VERDICT[verdict] : null;

  // The phase folder mano start will create or finish, so the skill needn't ls
  // to re-derive it at finalisation. scope-backlog opens the next phase;
  // resume-draft finishes the current one.
  if (s.next === "scope-backlog") s.targetPhase = (s.phase || 0) + 1;
  else if (s.next === "resume-draft") s.targetPhase = s.phase;
  else s.targetPhase = null;

  // On a backlog-scoping PROCEED, attach the exact material mano start needs so
  // the skill never has to open backlog.md / reviews.md itself.
  s.scope = null;
  if (s.next === "scope-backlog") {
    s.scope = {
      coreProductPrinciples: extractCoreProductPrinciples(s._backlogText),
      backlogItems: extractBacklogItems(s._backlogText, "backlog"),
      latestReview: extractLatestReview(s._reviewsText, s.phase),
    };
  }
  return s;
}

// ---- rendering ------------------------------------------------------------

// Default output: the go/no-go the skill acts on. Three lines, nothing more.
function renderDecision(s) {
  const L = [];
  L.push(`DECISION: ${s.decision}`);
  if (s.next) L.push(`NEXT: ${s.next}`);
  if (s.targetPhase != null) L.push(`PHASE: ${s.targetPhase}`);
  L.push(s.action);
  return L.join("\n");
}

// The "why", printed only with --verbose. The skill never needs this; the
// human does, when they want to expand the decision.
function renderEvidence(s) {
  const L = [];
  L.push("mano · project state");
  L.push(`root: ${s.projectRoot}` + (s.outputExists ? "  (_mano_output/ found)" : "  (no _mano_output/)"));
  L.push("");

  if (s.outputExists && s.phase !== null) {
    L.push(`latest phase: ${s.phase}`);
    L.push(`  phase-brief.md:        ${s.briefExists ? "present" : "MISSING"}`);
    if (s.stories) {
      L.push(`  stories:               ${s.stories.done}/${s.stories.total} done`);
      if (s.stories.openTitles.length) {
        for (const t of s.stories.openTitles) L.push(`                           open: ${t}`);
      }
    } else {
      L.push(`  stories:               none (no stories/README.md)`);
    }
    L.push(`  reviewed (reviews.md): ${s.reviewEntry ? "yes" : "no"}`);
    L.push(`  in-phase-${s.phase} items:      ${s.inPhaseRemaining} remaining`);
    L.push("");
  }

  if (s.outputExists) {
    const b = s.backlog || {};
    const keys = Object.keys(b).sort();
    L.push("backlog status counts:");
    if (keys.length === 0) L.push("  (no items)");
    for (const k of keys) L.push(`  ${k}: ${b[k]}`);
    L.push("");
  }

  L.push(`detail: ${s.verdict}`);
  return L.join("\n");
}

// The scope input the skill consumes on a PROCEED to scope-backlog: the exact
// Status: backlog items + core principles + latest review, so it needn't reopen
// any file. Empty string when there's no scope payload.
function renderScope(s) {
  if (!s.scope) return "";
  const L = ["--- SCOPE INPUT (from the state script — do NOT reopen these files) ---"];
  if (s.scope.coreProductPrinciples) {
    L.push("");
    L.push(s.scope.coreProductPrinciples);
  }
  L.push("");
  L.push(`## Backlog items — Status: backlog (${s.scope.backlogItems.length})`);
  if (s.scope.backlogItems.length === 0) {
    L.push("(none)");
  } else {
    for (const item of s.scope.backlogItems) {
      L.push("");
      L.push(item);
    }
  }
  L.push("");
  L.push("## Latest review");
  L.push(s.scope.latestReview || "(none)");
  return L.join("\n");
}

function renderJson(s) {
  return JSON.stringify({
    projectRoot: s.projectRoot,
    outputExists: s.outputExists,
    phase: s.phase,
    briefExists: s.briefExists,
    stories: s.stories,
    storiesAllDone: s.storiesAllDone,
    reviewEntry: s.reviewEntry,
    inPhaseRemaining: s.inPhaseRemaining,
    backlog: s.backlog,
    backlogItems: s.backlogItems,
    closed: s.closed,
    decision: s.decision,
    next: s.next,
    targetPhase: s.targetPhase,
    verdict: s.verdict,
    action: s.action,
    scope: s.scope,
  }, null, 2);
}

// ---- main -----------------------------------------------------------------

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(HELP + "\n");
    process.exit(0);
  }
  const s = scan(args.root);
  let out;
  if (args.json) {
    out = renderJson(s);
  } else {
    out = renderDecision(s);
    if (args.scope && s.scope) out += "\n\n" + renderScope(s);
    if (args.verbose) out += "\n\n" + renderEvidence(s);
  }
  process.stdout.write(out + "\n");
  process.exit(0);
}

main();
