# Mano eval harness

Validate that changing a skill file doesn't break the experience — especially
when **shrinking a heavy skill file**. Snapshot the assertions that pass today,
make your change, re-run, and see exactly which capability you dropped.

## How it works

Each case runs end-to-end against a real install:

1. Install Mano into a throwaway temp dir via the actual installer
   (`bin/mano-plan.js`) — so the fixture matches a true install, no drift.
2. Seed the case's fixture input files into `_mano_output/`.
3. Invoke a CLI **headless** to run the skill (`mano stories`, etc.) — once for
   a single-prompt case, or once per ordered step for a multi-step case.
4. Run deterministic, text-only **assertions** over the files the skill wrote,
   the state each step left behind, and — only for chat-native contracts — the
   runner's final response.
5. Append one **manifest record** per run to `eval/results/`, carrying whatever
   the CLI reported about what the run cost.

The harness does not inspect hidden reasoning or tool traces and does not require
a specific model. No Anthropic API key is required; it drives whichever CLI you
already use.

## Run it

```bash
python3 eval/run.py                        # all cases, claude runner
python3 eval/run.py --runner opencode      # or codex
python3 eval/run.py --case stories-bugfix  # one case
python3 eval/run.py --model opus           # pin the model for this run
python3 eval/run.py --rerun-failures       # re-run each failure once (flake check)
python3 eval/run.py --baseline             # record a committable baseline
python3 eval/run.py --keep                 # keep temp dirs to inspect output
```

Exit code is 0 only if the runner exits cleanly, stays inside its throwaway
project, and every assertion passes — with the [expected-red](#expected-red)
allowlist as the single, explicit exception.

Fast deterministic checks do not invoke a model:

```bash
npm test          # provenance, mappings, pointers, dependencies, scripts
npm run stacks    # what each command loads, per mode
```

`npm test` validates incident provenance, eval mappings, the rule-stripping path
used by retirement probes, cross-file references (`eval/check-refs.js` — every
`` `file` → **Section** `` pointer in `src/` must resolve, and every skill's
`requires:` / `requires-in-auto:` fragment must exist and stay on the right side
of its condition), and the scripts.

`npm run stacks` prints each command's installed stack — its skill file plus the
rule fragments its front matter declares — in `manual` and in `auto`. It is a
*size* measurement, not a token measurement: a smaller stack is a necessary
condition for a cheaper run, never proof of one. What a run costs is measured by
`run.py` against a real CLI.

Note on markers: production installs strip `<!-- mano-rule: -->` marker lines
(the rule bodies stay). The harness therefore installs with
`--keep-rule-markers` only for probe runs, strips the probed rules, then
normalises the remaining markers away so the runner always sees a
production-shaped install.

## Rule retirement probes

Incident-born prompt rules use paired, invisible markers:

```html
<!-- mano-rule: id=stable-rule-id; incident=real-hit; model=model-tier; date=YYYY-MM-DD; eval=case-name -->
...the behavior patch...
<!-- /mano-rule: stable-rule-id -->
```

List the currently tagged patch inventory and its eval coverage:

```bash
npm run eval:rules
```

This is intentionally labelled a partial inventory: older incident-born rules
are still being retrofitted and are invisible until tagged.

To ask whether a newer model still needs a fully mapped patch, run its complete
probe. The harness removes every occurrence and runs every case named by that
rule:

```bash
python3 eval/run.py --runner opencode \
  --probe-rule post-hook-findings-triage
```

`--probe-rule` never edits the repository and refuses rules with
`eval=pending` — and `eval/pending-evals.json` is the reason there should be
none: a rule may ship with `eval=pending` only as a recorded exception carrying
a reason and an owner. An entry whose rule is no longer pending fails the run,
the same way a passing `expected-red` case does. A release ships with that file
empty.

**A rule's case must load the file the probe strips.** `rules/auto.md` loads only
under `MODE: auto`, so a rule living there needs a case with `"run_mode": "auto"`;
`npm test` fails on one whose cases all run in `manual`, because stripping it
would change nothing those cases can see. The conditional-fragment list is
derived from the skills' own `requires-in-auto:` front matter, never from a
second hard-coded copy.

**The same applies across paths.** A build-path gate copied
from the stories path needs its own id and its own build-path case: the two
exercise different units of work, and a green stories case proves nothing about
a Scope leaf. `exit-criterion-tested-in-reverse` is one incident on five
surfaces and therefore five ids — `spec-promise-consistency`,
`phase-acceptance-integrity` (stories and review), `acceptance-evidence-polarity`
(the shared implementation contract), and `build-promise-polarity` — each with
the case that actually reaches it. `--without-rule` remains a low-level single-case/debug option;
its result is explicitly not complete retirement evidence. A passing complete
probe is evidence to inspect and repeat, not an automatic deletion decision:
model output can be noisy, every target model tier matters, and the human still
decides whether the patch has stopped paying rent.

## The shrink-a-skill workflow

1. `python3 eval/run.py` → note the baseline (all green).
2. Trim the skill file (e.g. cut `src/skills/stories.md`).
3. `python3 eval/run.py` again.
4. Each newly-failing assertion is a specific capability the trim removed.
   Decide if it mattered. If not, the cut was safe.

## Layout

```
eval/
  run.py             orchestrator: install → seed → invoke → assert → report
  runners.py         swappable headless CLI runners (claude | codex | opencode)
  assertions.py      pure-function checks on artifacts/final response (REGISTRY)
  provenance.py      validates incident markers and strips rules in temp installs
  expected-red.json  cases that must fail until their fix lands
  test_provenance.py deterministic tests for provenance + retirement probes
  test_run.py        deterministic tests for the harness itself (no model spend)
  test_runners.py    deterministic tests for usage capture and CLI invocation
  test_two_phase_assertions.py  trap matrix for the two-phase extension checks
  cases/*.json       declarative: skill prompt(s) + fixture + which assertions
  fixtures/<name>/   input artifacts a case runs against
  results/*.json     one manifest record per measured run
```

## Multi-step cases

A case has `prompt` **or** `steps`, never both. `steps` runs ordered prompts
**in one retained temp project** — the shape of every interesting Mano
behaviour, and the only honest way to test something like "build, then review
in a fresh session".

```json
{
  "name": "build-then-review", "fixture": "build-stage-chain", "phase": 1,
  "steps": [
    { "prompt": "mano build",  "session": "fresh" },
    { "prompt": "mano review", "session": "fresh" }
  ],
  "assertions": ["..."]
}
```

- `session` is `fresh` (default) or `continue`. `fresh` starts a new CLI
  invocation with no history; `continue` resumes the previous one. A runner that
  cannot resume a session **fails the step with a message saying so** rather than
  silently starting fresh — today only the `claude` runner can continue one.
- A failed step stops the chain. Every step that ran keeps its recorded cost:
  a failed run is real spend and belongs in the manifest.
- Do not emulate a multi-step scenario with two unrelated fixtures. The point is
  that step 2 sees exactly what step 1 left behind.

Assertions see both the final project state and each step:

```python
ctx.step(1).progress_rows()      # the ledger right after step 1
ctx.step(2).artifact_text("tech-spec.md")
ctx.changed_in_step(2)           # output paths that step created/edited/deleted
ctx.all_responses()              # every step's final message, joined
ctx.transcript                   # the LAST step's final message
```

`ctx.baseline` is `_mano_output/` as seeded, before any step ran, so a change can
be attributed to the step that made it. Every existing single-`prompt` case keeps
working untouched: it becomes one `fresh` step and `ctx.transcript` is unchanged.

## Measurement

Each run records what the CLI reports it cost, per step:

| field | meaning |
|---|---|
| `input` / `output` | tokens sent and generated |
| `cache_create` / `cache_read` | prompt-cache writes and hits |
| `messages` | assistant-message count where the runner exposes one (the `claude` runner reports its envelope's `num_turns`) |
| `wall_ms` | wall time for that step |

**A metric the runner does not expose is `null`, never `0`.** A zero is
indistinguishable from a measurement and silently poisons an average. Today only
the `claude` runner reports usage (via `--output-format json`); `codex` and
`opencode` report `null` for every field, and the results table says
`unavailable` rather than substituting a number.

`--model` is passed through to the CLI, and the manifest records both the
`requested_model` (the alias you typed) and the `resolved_model` (what the
provider says it actually ran).

Every measured run appends one record to `eval/results/<timestamp>.json`:

```json
{
  "commit": "1993155", "dirty": false,
  "runner": "claude", "runner_version": "...",
  "requested_model": "opus", "resolved_model": "claude-opus-5",
  "fixture": "two-phase-extension", "case": "two-phase-extension", "attempt": 1,
  "steps": [
    { "prompt": "mano build", "session": "fresh",
      "usage": { "input": 172, "output": 47077, "cache_create": 168948,
                 "cache_read": 11984906, "messages": 41 },
      "wall_ms": 412000, "passed": true, "error": null }
  ],
  "assertions": { "passed": 8, "failed": 0 },
  "passed": true, "total_tokens": 12201103
}
```

**The primary KPI is total tokens per *passing* scenario.** A cohort with any
failing assertion is reported as a failure with its cost — never as a saving.
`cache_read / message`, message count, output tokens, and wall time are
diagnostics, not headline numbers. Scope leaves and stories are not
interchangeable units, so no per-leaf or per-story denominator may be used to
claim a win.

**Cadence:** one run per revision by default. Three runs only for a number you
intend to publish — and then report all three, including the failures.

### Recording a baseline

```bash
python3 eval/run.py --baseline --model <pinned-model>
```

This names the manifest `baseline-<commit>-<stamp>.json` (the only manifest
shape Git tracks) and re-runs every failure once, so a deterministic failure is
distinguishable from a flake. Record the baseline **before** the change it is
meant to be the *before* of. Ad-hoc manifests stay untracked local noise.

### Honest claims

The 26.9% total-token reduction observed across the 1.4.0 work is **observed and
directional, not causal**. The "before" revision was branch-internal dogfooding,
the assistant-message count and per-message cache-read were never recorded, and
no fixture pinned the scenario. It is not reconstructed — reconstructing it buys
a number for a claim already positioned as secondary. This harness exists so the
*next* comparison is controlled: same commit, same pinned model, same fixture,
recorded per step. Public wording follows the same rule: *observed*,
*directional*, never *caused*.

### expected-red

`eval/expected-red.json` lists regression cases written *before* their fix. Each
entry needs a `reason` and a `fixed_by` naming the owning fix:

```json
{ "cases": { "some-case": { "reason": "…", "fixed_by": "wave 2 resume fix" } } }
```

An allowlisted case is expected to fail: it prints `RED (expected)` and does not
break the run. When it starts passing, the run **fails** with `RED-PASSED` — the
fix landed and the entry must be deleted, not edited. A later change may never
silently relabel a known pre-existing failure as its own, or quietly absorb a new
one.

The allowlist is ignored during `--probe-rule` runs: a probe deliberately removes
behaviour, so "expected red" says nothing about it.

## Adding a check

Write a function `(ctx) -> list[Failure]` in `assertions.py`, register it in
`REGISTRY`, and add its name to a case's `assertions` list. Each format/refusal
rule you add to a skill has a latent assertion here — that's the point.

## Adding a case

Drop a fixture folder under `fixtures/`, then a `cases/<name>.json`.

Phase-scoped skill (fixture files are existing project state seeded into `_mano_output/`):

```json
{
  "name": "stories-bugfix", "fixture": "bugfix-phase", "phase": 2,
  "prompt": "mano stories",
  "assertions": ["stories_were_written", "..."]
}
```

For a hook-flow case, add `"active_hook": "spec"` (or another skill name).
The harness copies the installed `post-spec.example.md` to `post-spec.md` only
inside the temp project, so the agent sees a genuinely active hook.

Document-intake skill (fixture is a raw input doc placed at the project root; no phase):

```json
{
  "name": "import-prd", "fixture": "import-prd",
  "fixture_mode": "document",
  "prompt": "mano import product-brief.md",
  "assertions": ["backlog_was_written", "all_items_status_backlog", "no_phase_brief_written", "..."]
}
```

`fixture_mode` defaults to `"seed"` (project state) when omitted; use `"document"` for a raw input file. Omit `phase` for non-phase-scoped skills.

For a seed fixture that includes an existing story set, name the index `stories-README.md`; the harness places it at `phase-[N]/stories/README.md`. Files named `story-*.md` in the same fixture are placed beside that index. This keeps fixtures flat while still exercising re-run and mid-build paths.

A `progress.md` in a seed fixture is the `mano build` path's ledger and is
placed at `phase-[N]/progress.md`, the same way `phase-brief.md` is. Seeding one
models a phase already part-way through a build, which is how the build cases
exercise resume, corrections, and the review gate without paying for a full
phase. A phase seeded with both a `stories-README.md` and a `progress.md` is a
deliberately invalid state — `build-two-ledgers` asserts it is reported, not
resolved by guessing.

A seeded ledger is stamped **last**, so `state.js` never reports a seeded
optional artifact as "changed after the ledger was last written". A fixture
cannot express mtime intent, and copy order alone would otherwise make every
fixture that pairs `progress.md` with `tech-spec.md` carry a permanent,
meaningless advisory. Seeded state is coherent by definition.

Add `"run_mode": "auto"` to pin a case's run mode. The temp project has no Git
config for the harness to write, so the value travels as the documented
`MANO_MODE` override. Use it where the contract must hold *because* the chain is
armed — `build-scope-refusal-auto` exists to prove auto mode does not soften
gate 6.4.

Nested paths inside a seed fixture are copied verbatim under `_mano_output/`.
Use them when a case needs existing artifacts from another phase, for example
`phase-1/design-preview.html` while the case's top-level `phase-brief.md` is
mapped to active Phase 2.

A nested `project/` prefix is copied to the temporary project root with that
prefix removed. Use it sparingly for brownfield cases that need a small actual
declaration or manifest surface, for example `project/src/client.ts`; ordinary
planning fixtures should stay under `_mano_output/`.

A nested `hooks/` prefix is copied into the installed `_mano/hooks/` directory.
Use it when a case needs a custom active hook file (e.g. a legacy-shaped hook);
use `active_hook` instead when the shipped example is the fixture.

### The two-phase extension case

`fixtures/two-phase-extension` + `cases/two-phase-extension.json` is the
reference multi-step case and the one worth copying. It seeds a finished Phase 1
— source plus a cumulative `tech-spec.md`, `project-rules.md`, `ux-flow.md`, and
`design-brief.md` — and an active Phase 2 that extends the same feature across
five ordered fresh sessions (`mano spec`, `mano rules`, `mano ux`, `mano ui`,
`mano build`). It pins what nothing else did: that Phase 1's behaviour survives,
that untouched regions of every pre-existing artifact and source file stay
byte-identical, that no section or row is duplicated or reordered, that the
active phase does not drift across a session boundary, and that Phase 2 never
opens another phase's non-cumulative brief (a canary planted in
`phase-1/phase-brief.md`).

Because the case itself costs real model spend, its assertions are pinned by
`test_two_phase_assertions.py`: that test builds the state a *correct* Phase 2
would leave, proves all eight assertions pass on it, then reintroduces one defect
at a time and proves the owning assertion fires. Do the same for any expensive
case you add — an assertion that cannot fail is not coverage.

### Build-path cases

The `mano build` path has no story files, so several of its contracts can only
be checked as *refusals* — the interesting outcome is that nothing was written.
`build-invalid-ledger`, `build-invalid-two-ledgers`, `build-brief-edited`, and
`start-amend-with-ledger` all assert byte-identical fixture state afterwards,
not just a well-worded message: a refusal that leaves a half-written ledger is a
partial action, not a refusal.

Three contracts need step traces rather than a final artifact, because the final
state cannot distinguish the right order from a plausible one:

- `start-amend-pre-ledger` — a preview that writes nothing, then a write after
  approval. Checked with `ctx.changed_in_step(1)`; the final brief alone cannot
  tell preview-then-write from write-then-describe.
- `review-build-finding` — a confirmed finding becomes a durable `R…` event.
- `build-rework-pending` — that event routes back to build even though every row
  already reads `done`.

Some build contracts are pinned by deterministic tests instead of evals, because
no fixture can provoke them on demand: the lazy sub-row split fires only when a
row overflows a turn's output budget, and the `--expect-phase-id` owner guard
needs the owner to change *between* two commands. Both are covered in
`test/scripts/progress.test.js`. Prefer a deterministic test wherever a property
can be decided by a script — the same trade `verify.js` and `state.js` made.

### Grouping cases, and what a fixture cannot show

`mano build` may cover several contiguous leaves of one brief category in a
single pass. Grouping changes how many rows one *turn* covers, and the final
ledger does not record pass boundaries — so "it grouped" is not directly
observable from a finished run. The cases assert the properties that must hold
whether it grouped or not:

- `build-single-pass` builds a two-level brief from scratch. Its first category
  has four leaves on one surface, deliberately more than one comfortable pass:
  since there is **no numeric cap**, the honest check is that every row it
  closed is genuinely proven, each Exit leaf exercised in its own process.
  Taking fewer rows always passes; closing a row it could not prove does not.
- `build-group-boundary` puts a spec-owned default gap in category 2, which
  turns the category boundary into an observable stop: the leaves before it
  close and work, the blocked leaf stays `pending`, no capacity value is
  invented, and the gap routes to `mano spec`. Its second step proves a partial
  pass resumes at the first unresolved leaf instead of closing what it could not
  build.
- `build-resume` keeps the flat fixture and asserts a flat brief never grows
  lettered leaves — two-level scope is a new-brief shape, not a migration.

Three grouping rules cannot be provoked by any fixture and are pinned in
`test_implementation_entry_contract.py` instead: stopping at a *surface*
boundary and stopping for *budget* certainty both depend on a turn boundary no
fixture can force, and "a correction or split row is never grouped" is a
statement about a pass that only ever contains one row anyway. The same file
pins that the entry rule's six clauses exist, in order, at every operational
site — the drift wave 4 fixed was prose agreeing with the rule beside an
operational block that did not.

### Invocation-argument cases

`mano build "<text>"` is a correction channel, never a scope channel, and it is
accepted only when a valid ledger exists. Each classifier case passes the text
as a real quoted argument, because the channel is part of what is under test:

| case | what it pins |
|---|---|
| `build-defect-reopen` | **A** — reopen the promised rows before any code; append nothing |
| `build-arg-distinct-outcome` | **B** — no row, no code, offered to the backlog (not `mano start`) |
| `build-scope-refusal-auto` | **B** again, with the chain armed — auto removes typing, not decisions |
| `build-nuance-row` | **C** — a `+N` row carrying the exact words, linked to an Exit leaf |
| `build-nuance-spec-gap` | **C** whose nuance needs a default no artifact owns — no code |
| `build-arg-rework-precedence` | a pending `R…` event outranks the argument; nothing is written |
| `build-arg-no-ledger` | with no ledger, no ledger is created to hold it, and it routes to `mano start` |

`build-auto-direct` is the whole path in one case: `mano import` → `mano start`
→ approval, in auto, ending at `mano build` with no story file anywhere and no
review entry.

### Provenance-debt cases

Every shipped incident rule names a case that actually loads it (§6.2). These
are the ones that closed the three `eval=pending` markers, plus the build-path
splits:

| case | rule it maps to |
|---|---|
| `two-phase-extension` | `cumulative-artifact-minimal-diff` — a re-emitted artifact drops or paraphrases the Phase 1 lines the assertions anchor on |
| `hook-triage-stories-no-approval` | `post-stories-hook-findings-triage` — the sibling of the spec/start/rules triage cases |
| `stories-acceptance-polarity` | `phase-acceptance-integrity` (stories, review) |
| `spec-acceptance-polarity` | `spec-promise-consistency` — spec resolves the contradiction in place or raises `❓ Decide:` |
| `dev-acceptance-polarity` | `acceptance-evidence-polarity` — the shared implementation contract's gate 10.1 |
| `build-acceptance-polarity` | `build-promise-polarity` — the same conflict caught at build pre-flight, before any ledger |
| `build-project-rule-coverage` | `build-project-rule-coverage` — 0g on the build path, where the unit is a Scope leaf |

`acceptance-polarity` is one fixture asked three different questions. Its brief
promises that a signed-out device can be recovered; its tech spec says the
device stays locked and recovery is **not wired**. `mano spec` must resolve or
raise it, `mano stories` must refuse to write an AC either way, and `mano build`
must stop at pre-flight with both statements quoted. The failure the incident is
named for — inverting the promise to match the artifact so the suite goes green
— looks like success on every one of those paths.

### Review cases

Review is the one mandatory action, and it has to cost one exchange. These cases
pin both halves of that — the shape, and everything the shape must not drop:

| case | what it pins |
|---|---|
| `review-opening-shape` | the opening: every Exit leaf at its own address, one ask, no tags or recording mechanics |
| `review-sign-off-close` | `close it` is sign-off — leaves flip to `met` with recorded human provenance, questions record `unanswered at close` |
| `review-mixed-echo` | mixed feedback echoes only what Mano classified, and writes nothing yet |
| `review-close-with-finding` | `close it` beside a defect closes the phase and asks route-or-dismiss instead of erasing it |
| `review-followup-compact` | the follow-up confirmation uses the same compact rule |
| `review-positive-one-liner` | a natural positive verdict closes with no close token and no echo round |
| `review-build-finding` | a build-path finding becomes a durable `R…` event and routes to build, never to stories |
| `build-validate-now` | D6: the brief's `Try` guidance at the build handoff **and** again in a fresh review opening |

`review-open-phase` is the fixture behind four of them: a finished build-path
phase whose ledger carries one `needs-human` leaf with its recorded reason, and
whose brief carries two addressed questions (`Q1`, `Q2`) and two addressed
assumptions (`A1`, `A2`). One fixture, four different asks of it — the opening,
the close, a mixed echo, and a close arriving with a finding — because what is
under test is the response, not the state.

`build-validate-now` is the only two-command case here: `mano build` then a
**fresh** `mano review`. The freshness is the point. `Try` guidance appearing
twice looks redundant in one transcript and is not redundant at all across a
session boundary, where the earlier message no longer exists.

## Notes / limits

- Assertions are deterministic text checks. Subjective qualities
  ("is this brief human-readable?") need an LLM-judge assertion — not built yet,
  deliberately. Start with what's cheap and certain.
- A provenance marker may use `model=not-recorded` when the original incident
  did not preserve that detail. Do not invent historical precision.
- `eval=pending` is allowed for a retrofitted existing rule, but it is visible
  debt: the rule cannot be meaningfully probed for retirement until its case
  exists.
- Not every rule can be provoked on demand. `mano build`'s lazy sub-row split
  fires only when a row overflows a turn's output budget, which no fixture can
  force; it is pinned by `progress.js`'s deterministic refusals instead (a
  `pending` row cannot be split, the first part is recorded `done`, a parent
  cannot close before its sub-rows). Prefer a deterministic test over an eval
  case whenever the property can be decided by a script — that is the same trade
  `verify.js` and `state.js` already made.
- A failing assertion after a CLI run can mean the skill regressed **or** the
  model drifted. Re-run before concluding; if it's flaky, the assertion is too
  tight or the skill rule is too weak to enforce on that model.
