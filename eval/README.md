# Mano eval harness

Validate that changing a skill file doesn't break the experience — especially
when **shrinking a heavy skill file**. Snapshot the assertions that pass today,
make your change, re-run, and see exactly which capability you dropped.

## How it works

Each case runs end-to-end against a real install:

1. Install Mano into a throwaway temp dir via the actual installer
   (`bin/mano-plan.js`) — so the fixture matches a true install, no drift.
2. Seed the case's fixture input files into `_mano_output/`.
3. Invoke a CLI **headless** to run the skill (`mano stories`, etc.).
4. Run deterministic, text-only **assertions** over the files the skill wrote
   and, only for chat-native contracts, the runner's final response.

The harness does not inspect hidden reasoning or tool traces and does not require
a specific model. No Anthropic API key is required; it drives whichever CLI you
already use.

## Run it

```bash
python3 eval/run.py                        # all cases, claude runner
python3 eval/run.py --runner opencode      # or codex
python3 eval/run.py --case stories-bugfix  # one case
python3 eval/run.py --keep                 # keep temp dirs to inspect output
```

Exit code is 0 only if the runner exits cleanly, stays inside its throwaway
project, and every assertion passes.

Fast deterministic checks do not invoke a model:

```bash
npm test
```

This validates incident provenance, eval mappings, and the rule-stripping path
used by retirement probes.

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
`eval=pending`. `--without-rule` remains a low-level single-case/debug option;
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
  test_provenance.py deterministic tests for provenance + retirement probes
  cases/*.json       declarative: skill prompt + fixture + which assertions
  fixtures/<name>/   input artifacts a case runs against
```

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

## Notes / limits

- Assertions are deterministic text checks. Subjective qualities
  ("is this brief human-readable?") need an LLM-judge assertion — not built yet,
  deliberately. Start with what's cheap and certain.
- A provenance marker may use `model=not-recorded` when the original incident
  did not preserve that detail. Do not invent historical precision.
- `eval=pending` is allowed for a retrofitted existing rule, but it is visible
  debt: the rule cannot be meaningfully probed for retirement until its case
  exists.
- A failing assertion after a CLI run can mean the skill regressed **or** the
  model drifted. Re-run before concluding; if it's flaky, the assertion is too
  tight or the skill rule is too weak to enforce on that model.
