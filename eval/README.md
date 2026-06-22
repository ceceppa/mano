# Mano eval harness

Validate that changing a skill file doesn't break the experience — especially
when **shrinking a heavy persona**. Snapshot the assertions that pass today,
make your change, re-run, and see exactly which capability you dropped.

## How it works

Each case runs end-to-end against a real install:

1. Install Mano into a throwaway temp dir via the actual installer
   (`bin/mano-plan.js`) — so the fixture matches a true install, no drift.
2. Seed the case's fixture input files into `_mano_output/`.
3. Invoke a CLI **headless** to run the skill (`mano stories`, etc.).
4. Run deterministic, text-only **assertions** over the files the skill wrote.

The harness asserts on output files, never on stdout or a specific model — so it
is runner- and model-agnostic. No Anthropic API key required; it drives whichever
CLI you already use.

## Run it

```bash
python3 eval/run.py                        # all cases, claude runner
python3 eval/run.py --runner opencode      # or codex
python3 eval/run.py --case stories-bugfix  # one case
python3 eval/run.py --keep                 # keep temp dirs to inspect output
```

Exit code is 0 only if every assertion passes.

## The shrink-a-persona workflow

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
  assertions.py      pure-function checks on output files (the REGISTRY)
  cases/*.json       declarative: skill prompt + fixture + which assertions
  fixtures/<name>/   input artifacts a case runs against
```

## Adding a check

Write a function `(ctx) -> list[Failure]` in `assertions.py`, register it in
`REGISTRY`, and add its name to a case's `assertions` list. Each format/refusal
rule you add to a skill has a latent assertion here — that's the point.

## Adding a case

Drop a fixture folder under `fixtures/`, then a `cases/<name>.json`:

```json
{
  "name": "...", "fixture": "...", "phase": 2,
  "prompt": "mano stories",
  "assertions": ["stories_were_written", "..."]
}
```

## Notes / limits

- Assertions are deterministic text checks. Subjective qualities
  ("is this brief human-readable?") need an LLM-judge assertion — not built yet,
  deliberately. Start with what's cheap and certain.
- A failing assertion after a CLI run can mean the skill regressed **or** the
  model drifted. Re-run before concluding; if it's flaky, the assertion is too
  tight or the skill rule is too weak to enforce on that model.
