"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const SCRIPT = path.resolve(__dirname, "..", "..", "src", "scripts", "verify.js");

function run(args, cwd) {
  return spawnSync("node", [SCRIPT, ...args], { encoding: "utf8", cwd });
}

test("passing command prints one PASS line and exits 0", () => {
  const result = run(["--", "node", "-e", "process.exit(0)"]);
  assert.strictEqual(result.status, 0);
  assert.match(result.stdout.trim(), /^PASS: node -e process\.exit\(0\)$/);
});

test("failing command prints FAIL with exit code and a trimmed excerpt", () => {
  const result = run([
    "--",
    "node",
    "-e",
    "console.error('Error: boom at file.js:3'); process.exit(2)",
  ]);
  assert.strictEqual(result.status, 2);
  assert.match(result.stdout, /^FAIL \(exit 2\):/);
  assert.match(result.stdout, /Error: boom at file\.js:3/);
});

test("long failing output is head/tail trimmed and capped", () => {
  const script =
    "for (let i = 0; i < 300; i++) console.log('line ' + i); process.exit(1)";
  const result = run(["--", "node", "-e", script]);
  assert.strictEqual(result.status, 1);
  assert.match(result.stdout, /lines omitted/);
  assert.ok(result.stdout.length < 3000, `output too long: ${result.stdout.length}`);
  assert.match(result.stdout, /line 0/); // head survives
  assert.match(result.stdout, /line 299|output capped/); // tail or cap marker
});

test("consecutive duplicate lines are collapsed", () => {
  const script =
    "for (let i = 0; i < 10; i++) console.log('same noise'); process.exit(1)";
  const result = run(["--", "node", "-e", script]);
  assert.strictEqual(result.status, 1);
  assert.match(result.stdout, /\[× 10 identical lines\]/);
});

test("tech-spec failure-pattern lines lead the excerpt", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mano-verify-"));
  try {
    fs.mkdirSync(path.join(tmp, "_mano_output"));
    fs.writeFileSync(
      path.join(tmp, "_mano_output", "tech-spec.md"),
      "# Tech Spec\n\n## Verification\n\n- command: node run-checks\n- failure-pattern: ^ASSERT!\n",
    );
    const script =
      "console.log('banner'); console.log('ASSERT! expected 3 got 4'); console.log('trailer'); process.exit(1)";
    const result = run(["--", "node", "-e", script], tmp);
    assert.strictEqual(result.status, 1);
    assert.match(result.stdout, /-- matched failure-pattern --\nASSERT! expected 3 got 4/);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test("missing command is a usage error", () => {
  const result = run([]);
  assert.strictEqual(result.status, 2);
  assert.match(result.stderr, /usage/);
});

test("--help prints usage and exits 0", () => {
  const result = run(["--help"]);
  assert.strictEqual(result.status, 0);
  assert.match(result.stdout, /Usage:/);
  assert.match(result.stdout, /failure-pattern/);
});

test("--help after the separator is part of the command, not a flag", () => {
  // `verify.js -- mytool --help` must run mytool, not print this script's usage.
  const result = run(["--", "echo", "--help"]);
  assert.strictEqual(result.status, 0);
  assert.match(result.stdout, /^PASS: echo --help/);
});

// ---- V1: the four repairs -------------------------------------------------

test("both the head and the tail sentinel survive the character cap", () => {
  // `joined.slice(0, CHAR_CAP)` amputated exactly the tail the head/tail
  // excerpt had just been built to preserve — so a failure whose cause prints
  // last (the summary, the stack, the assertion) lost the only useful part.
  const script = [
    "console.log('HEAD-SENTINEL');",
    "for (let i = 0; i < 400; i++) console.log('filler line ' + i + ' ' + 'x'.repeat(60));",
    "console.log('TAIL-SENTINEL');",
    "process.exit(1);",
  ].join("");
  const result = run(["--", "node", "-e", script]);
  assert.strictEqual(result.status, 1);
  assert.ok(result.stdout.length < 2600, `excerpt was ${result.stdout.length} chars`);
  assert.match(result.stdout, /HEAD-SENTINEL/);
  assert.match(result.stdout, /TAIL-SENTINEL/);
});

test("a missing executable reports the spawn error, not a blank excerpt", () => {
  // status is null and stdout/stderr are undefined in exactly this case, so it
  // used to print `FAIL (exit 1)` over nothing at all.
  const result = run(["--", "definitely-not-a-real-command-xyz", "--flag"]);
  assert.strictEqual(result.status, 1);
  assert.match(result.stdout, /^FAIL \(did not run\):/);
  assert.match(result.stdout, /ENOENT/);
  assert.doesNotMatch(result.stdout, /FAIL \(exit 1\)/);
});

test("a signalled process reports its signal", () => {
  const result = run(["--", "node", "-e", "process.kill(process.pid, 'SIGKILL')"]);
  assert.strictEqual(result.status, 1);
  assert.match(result.stdout, /^FAIL \(killed by SIGKILL\):/);
});

test("an empty argument survives to the command and to the display", () => {
  // `cmd --filter ""` means something different from `cmd --filter`; dropping
  // the value silently changed the command that ran.
  const { parseArgs } = require("../../src/scripts/verify.js");
  assert.deepStrictEqual(parseArgs(["--", "node", "-e", "x", ""]).argv, ["node", "-e", "x", ""]);
  assert.match(parseArgs(["--", "cmd", "--filter", ""]).display, /--filter ""/);

  const result = run(["--", "node", "-e", "process.exit(process.argv[1] === '' ? 0 : 3)", ""]);
  assert.strictEqual(result.status, 0, "the empty argument reached the child");
});

test("the excerpt labels each stream instead of claiming an interleaving", () => {
  const result = run([
    "--", "node", "-e",
    "console.log('on stdout'); console.error('on stderr'); process.exit(1)",
  ]);
  assert.strictEqual(result.status, 1);
  assert.match(result.stdout, /on stdout/);
  assert.match(result.stdout, /-- stderr --/);
  assert.match(result.stdout, /on stderr/);
});
