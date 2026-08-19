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
