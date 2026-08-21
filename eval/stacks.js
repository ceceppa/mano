#!/usr/bin/env node
"use strict";

/**
 * stacks — what each `mano <action>` loads before it does anything.
 *
 * A command's resident context starts as its skill file plus the rule
 * fragments its front matter declares. That number is deterministic, so it is
 * measured rather than argued about: `requires` is the unconditional stack and
 * `requires-in-auto` is added only when the state projection reports
 * `MODE: auto`.
 *
 * This is a *size* measurement, not a token measurement. Characters are
 * exact; the `~tok` column is chars/4, the same rough divisor plan2 used, and
 * it is a comparison aid, not a token count. What a run actually costs is
 * measured by `eval/run.py` against a real CLI — a smaller stack is a
 * necessary condition for a cheaper run, never proof of one.
 *
 *   node eval/check-refs.js   verifies these declarations resolve
 *   node eval/stacks.js       prints what they cost
 *   node eval/stacks.js --json
 */

const fs = require("node:fs");
const path = require("node:path");
const { frontMatterList } = require("./check-refs.js");

const SRC = path.resolve(__dirname, "..", "src");

function ruleSizes() {
  const dir = path.join(SRC, "rules");
  const out = {};
  for (const entry of fs.readdirSync(dir)) {
    if (entry.endsWith(".md")) out[entry.slice(0, -3)] = fs.readFileSync(path.join(dir, entry), "utf8").length;
  }
  return out;
}

function stacks() {
  const rules = ruleSizes();
  const dir = path.join(SRC, "skills");
  const rows = [];
  for (const entry of fs.readdirSync(dir).sort()) {
    if (!entry.endsWith(".md")) continue;
    const text = fs.readFileSync(path.join(dir, entry), "utf8");
    const always = frontMatterList(text, "requires") || [];
    const inAuto = frontMatterList(text, "requires-in-auto") || [];
    const sum = (names) => names.reduce((n, r) => n + (rules[r] || 0), 0);
    const manual = text.length + sum(always);
    rows.push({
      command: entry.slice(0, -3),
      skill: text.length,
      requires: always,
      requiresInAuto: inAuto,
      manual,
      auto: manual + sum(inAuto),
    });
  }
  return { rules, rows };
}

function main() {
  const { rules, rows } = stacks();
  if (process.argv.includes("--json")) {
    process.stdout.write(JSON.stringify({ rules, rows }, null, 2) + "\n");
    return;
  }
  const pad = (s, n) => String(s).padEnd(n);
  const num = (n) => n.toLocaleString("en-US").padStart(8);

  process.stdout.write("rule fragments\n");
  for (const [name, size] of Object.entries(rules).sort((a, b) => b[1] - a[1])) {
    process.stdout.write(`  ${pad(name, 12)}${num(size)}\n`);
  }
  process.stdout.write("\ninstalled stack per command (chars, ~tok = chars/4)\n");
  process.stdout.write(`  ${pad("command", 10)}${pad("  manual", 12)}${pad("    auto", 12)}  loads\n`);
  for (const row of [...rows].sort((a, b) => b.manual - a.manual)) {
    const auto = row.auto === row.manual ? "        —" : num(row.auto);
    const loads = [...row.requires, ...row.requiresInAuto.map((r) => `${r}*`)].join(",") || "—";
    process.stdout.write(
      `  ${pad(row.command, 10)}${num(row.manual)} ${pad(`(~${Math.round(row.manual / 4)})`, 9)}` +
        `${auto}  ${loads}\n`,
    );
  }
  process.stdout.write("\n  * loaded only when the projection reports MODE: auto\n");
}

if (require.main === module) {
  // `node eval/stacks.js | head` closes the pipe early; that is a normal way to
  // read a diagnostic table, not a crash.
  process.stdout.on("error", (err) => {
    if (err.code === "EPIPE") process.exit(0);
    throw err;
  });
  main();
}

module.exports = { stacks };
