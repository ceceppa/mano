# Contributing to Mano

Thanks for wanting to help. Mano is a small, opinionated project with an unusual
shape, so this guide is mostly about *what makes a change fit* — the mechanics are
easy, the judgment is the hard part.

## What Mano is (and isn't)

Mano is **a fast planning loop for AI-assisted development**: you plan in small
phases and validate each assumption before it becomes code, staying in control of
the direction at every seam.

Concretely, Mano is **a set of skills, templates, and instructions** — markdown
prompts under `src/`, not a compiled tool. There is no runtime engine; behaviour
lives entirely in what the agent reads. That single fact shapes every contribution:
a change to Mano is almost always a change to a *prompt*.

## The bar for a change

Most projects want more features. Mano mostly doesn't. Before proposing a change,
hold it against these:

1. **Does it lower the human's cost per decision?** Every change must make the human
   faster or surer at steering — not add a step for the framework's benefit. A change
   that exists to make Mano "more complete" is the wrong direction.
2. **Does it keep the human in the loop?** Never optimise by removing an approval
   seam. Mano is a supervised assistant; the human owns the direction. Automating away
   a judgment call is a regression even if it "saves a message".
3. **Is it backed by a real incident, not a clever idea?** New rules earn their place
   by fixing something that actually went wrong on a real project. "This would be nice"
   is not enough — it's how prompts bloat. If you can't point at the failure, the
   change probably isn't ready.
4. **Does it stay un-opinionated and stack-agnostic?** Mano doesn't mandate testing,
   a language, or a toolchain. Keep stack-specific vocabulary out of the skill files;
   ask the user rather than assuming.

If a change adds structure, it should be because a phase genuinely needs it — not
because symmetry or completeness feels nicer.

## Repo layout

```
src/
  skills/      the action prompts: start, import, spec, ux, rules, ui, stories, dev, review …
  templates/   artifact scaffolds copied into a project's _mano_output/
  hooks/       optional post-action hook examples
  bootstrap/   root files dropped into a project: AGENTS.md, CLAUDE.md, cursorrules
  workflow.md  the shared protocol: command table, state detection, Intake Boundaries (B1–B5)
bin/
  mano-plan.js the installer (npx mano-plan install)
eval/          the test harness (see eval/README.md)
```

Two destinations to keep straight: `src/bootstrap/` → project-root files;
everything else under `src/` → the project's `_mano/` directory.

## Making a change to a skill

- Skills are prompts. Edit the markdown, keep the voice consistent with the
  surrounding file, and match its existing density — don't compress to save bytes.
  We shrink skills *structurally* (cut a whole path, move a shared value to one home),
  never by squeezing prose into terser prose.
- Chat output stays terse: a skill reports what changed, not a prose recap. The
  implementer (`mano dev`) returns one line.
- A value that's shared across skills lives in **one** owning artifact and is
  referenced — or, where referencing has proven unreliable for small-context agents,
  inlined with a "do not invent fields" guard. Don't create a second source of truth.

## Testing a change

Mano has an eval harness that installs Mano into a throwaway project, runs a skill
headless against a real CLI, and asserts on the files it produces. It's
runner- and model-agnostic (no API key needed).

```bash
npm run eval                      # all cases, claude runner
python3 eval/run.py --runner codex
python3 eval/run.py --case import-prd --keep
```

The intended workflow when you trim a skill:

1. `npm run eval` → baseline (all green).
2. Make your change.
3. `npm run eval` again → each newly-failing assertion is a capability your change
   dropped. Decide whether it mattered; if not, the cut was safe.

Adding rules to a skill? Add the matching assertion in `eval/assertions.py` so the
rule is enforced, not just hoped for. See [eval/README.md](eval/README.md) for how
to add checks and cases.

## Pull requests

- Branch off `main`. Keep the PR focused on one change.
- Update [CHANGELOG.md](CHANGELOG.md) under the next version, in the project's
  bullet style (`Added` / `Changed` / `Fixed`), explaining *why*, not just *what*.
- If you touched a skill's behaviour, add or update an eval case so the next person
  can't silently regress it.
- In the PR description, say what real situation prompted the change. A reviewer's
  first question will be "what went wrong that this fixes?".

## Versioning

Mano ships on npm as `mano-plan` (SemVer). The installer version is selected at the
npm layer (`npx mano-plan@latest install`). Don't bump the version in a PR unless you
coordinate the release — the maintainer cuts versions and tags.

## Questions and ideas

Open an issue to discuss before building anything large — especially anything that
moves orchestration out of prompts and into scripts. That's a deliberate line
(Mano is not a deterministic tool), and crossing it is a design decision, not a
drive-by PR.
