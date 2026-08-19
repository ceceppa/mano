#!/usr/bin/env node
"use strict";

/**
 * mano verify — run a verification command and filter its output at the source.
 *
 * Instructions cannot save tokens that are already in the transcript, so the
 * filtering happens here, before anything reaches the agent's context:
 *
 *   node verify.js -- <command ...>
 *
 *   exit 0  → prints `PASS: <command>` and exits 0 (~10 tokens, no parsing —
 *             the common case)
 *   exit ≠0 → prints `FAIL (exit n): <command>` plus a trimmed excerpt of the
 *             combined output: the first 40 and last 20 lines, consecutive
 *             duplicates collapsed, capped at 2,000 characters — then exits
 *             with the command's own exit code
 *
 * The script is runner-agnostic: it names no test framework, build tool, or
 * language. Optional sharpening is project-owned, not framework-owned: a
 * `## Verification` block in _mano_output/tech-spec.md may declare
 * `failure-pattern: <regex>`; when a failing run's output has lines matching
 * that pattern, those lines lead the excerpt. (`command:` in the same block
 * documents the project's canonical verification command for the implementer;
 * this script does not read it.)
 *
 * Invocation forms:
 *   node verify.js -- npm test              → spawned directly (argv preserved)
 *   node verify.js -- "npm test 2>&1 | x"   → single argument runs via the shell,
 *                                             so pipes and redirects work
 */

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const HEAD_LINES = 40;
const TAIL_LINES = 20;
const CHAR_CAP = 2000;
const PATTERN_LINE_CAP = 12;

function parseArgs(argv) {
  const sep = argv.indexOf("--");
  const rest = (sep === -1 ? argv : argv.slice(sep + 1)).filter((a) => a !== "");
  return { argv: rest, display: rest.join(" ").trim() };
}

// The optional project-owned failure pattern from tech-spec.md's
// `## Verification` block. Absent file, absent block, absent field, or an
// invalid regex all mean "no pattern" — never an error.
function failurePattern(projectRoot) {
  try {
    const spec = fs.readFileSync(
      path.join(projectRoot, "_mano_output", "tech-spec.md"),
      "utf8",
    );
    const block = /^##\s+Verification\s*$([\s\S]*?)(?=^##\s|\n*$(?![\s\S]))/im.exec(spec);
    if (!block) return null;
    const field = /^[-*\s]*failure-pattern:\s*(.+)$/im.exec(block[1]);
    if (!field) return null;
    return new RegExp(field[1].trim().replace(/^`|`$/g, ""));
  } catch {
    return null;
  }
}

// Collapse consecutive duplicate lines ("... 57 more of the same" style noise).
function dedupe(lines) {
  const out = [];
  let last = null;
  let repeats = 0;
  for (const line of lines) {
    if (line === last) {
      repeats++;
      continue;
    }
    if (repeats > 0) out.push(`  [× ${repeats + 1} identical lines]`);
    out.push(line);
    last = line;
    repeats = 0;
  }
  if (repeats > 0) out.push(`  [× ${repeats + 1} identical lines]`);
  return out;
}

function excerpt(text, pattern) {
  const lines = dedupe(
    text.split(/\r?\n/).map((l) => l.replace(/\s+$/, "")).filter((l, i, a) => l !== "" || (i > 0 && a[i - 1] !== "")),
  );
  const parts = [];
  if (pattern) {
    const matched = lines.filter((l) => pattern.test(l)).slice(0, PATTERN_LINE_CAP);
    if (matched.length) {
      parts.push("-- matched failure-pattern --", ...matched, "");
    }
  }
  if (lines.length <= HEAD_LINES + TAIL_LINES) {
    parts.push(...lines);
  } else {
    parts.push(
      ...lines.slice(0, HEAD_LINES),
      `  [... ${lines.length - HEAD_LINES - TAIL_LINES} lines omitted ...]`,
      ...lines.slice(-TAIL_LINES),
    );
  }
  let joined = parts.join("\n");
  if (joined.length > CHAR_CAP) joined = joined.slice(0, CHAR_CAP) + "\n  [output capped at 2000 chars]";
  return joined;
}

function main() {
  const { argv, display } = parseArgs(process.argv.slice(2));
  if (!display) {
    process.stderr.write("usage: node verify.js -- <command ...>\n");
    process.exit(2);
  }
  const options = { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 };
  const result = argv.length === 1
    ? spawnSync(argv[0], { ...options, shell: true })
    : spawnSync(argv[0], argv.slice(1), options);
  const code = result.status === null ? 1 : result.status;
  if (code === 0) {
    process.stdout.write(`PASS: ${display}\n`);
    process.exit(0);
  }
  const combined = `${result.stdout || ""}\n${result.stderr || ""}`;
  process.stdout.write(`FAIL (exit ${code}): ${display}\n`);
  process.stdout.write(excerpt(combined, failurePattern(process.cwd())) + "\n");
  process.exit(code);
}

if (require.main === module) main();

module.exports = { parseArgs, failurePattern, dedupe, excerpt };
