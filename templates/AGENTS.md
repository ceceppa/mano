# AGENTS.md

This project uses **Mano** for planning. Mano is a structured thinking tool — it produces planning artifacts, not code.

## For coding agents

### Running Mano commands

Mano commands are repo-local workflow instructions, not installed OpenCode skills.

If the user types a Mano command in chat, do **not** try to load an external skill named `mano`.

Instead, execute the corresponding Mano planning flow by reading the local files in this repository:

- `_mano/workflow.md`
- `_mano/skills/[command].md`
- any referenced templates or current `_mano_output/` artifacts

Examples:

- `mano start` → read `_mano/skills/start.md` and follow that flow
- `mano spec` → read `_mano/skills/spec.md` and follow that flow
- `mano rules` → read `_mano/skills/rules.md` and follow that flow
- `mano stories` → read `_mano/skills/stories.md` and follow that flow
- `mano review` → read `_mano/skills/review.md` and follow that flow
- `mano continue` → read `_mano/workflow.md` and determine the next useful Mano action

If a platform skill named `mano` is not available, that is not an error. Continue by using the local `_mano/` files.

Only use external/platform skills when the user explicitly invokes them or when a Mano hook asks whether to run one and the user confirms.

### Implementing a story

1. Find the active phase: highest numbered `phase-[N]/` folder in `_mano_output/`.
2. Check `_mano_output/phase-[N]/stories/README.md` for the story index and status.
3. **Hard stop — no implementable story remains.** If every story in the index is already `done`, or the requested / "next" story does not exist, STOP. Do not start, scope, or plan a new phase. Do not run `mano start`, `mano stories`, or any other Mano action. Do not invent, infer, or pick work. The phase being complete is not a trigger to advance — advancing is the user's explicit decision. Output one line stating the phase is complete and that `mano review` or `mano start` is the user's call, then stop. This is a hard stop, not a guideline.
4. Before implementing the requested story, check whether any earlier story in the index is still `pending`. Treat numbered stories and lettered insertions as ordered work unless the README or story notes explicitly say otherwise.
5. If an earlier story is still `pending`, stop and tell the user which story would be skipped. Do not implement the later story unless the user explicitly confirms they want to bypass the suggested order.
6. Read the story file first. Treat it as the primary implementation contract and expect it to be sufficient for correct implementation. The Implementation Reference section should carry the applicable rules plus any required files, modules, contracts, constraints, ownership boundaries, and prohibitions for that story. Treat exact prop names, attribute names, variant names, state keys, ownership statements, file paths, dependency names, and install commands written there as normative.
7. If the story is bootstrap, setup, tooling, infrastructure, or dependency-related, also read `_mano_output/tech-spec.md` before implementing. Treat library choices, package-manager choice, and install commands there as normative unless the story file already repeats them exactly.
8. Execute install commands exactly as written. Do not merge separate command groups, switch tools, or normalize mixed-tool instructions into a single package-manager invocation unless the story or tech spec explicitly tells you to. In particular, keep `npx expo install` commands separate from `npm install` or other package-manager commands so Expo can resolve SDK-compatible versions.
9. If the story involves user-entered state, forms, onboarding drafts, settings, or other local data, check whether the story or tech spec says that data should persist across app restarts. If it should, treat restart persistence as part of the required behaviour, not as an optional enhancement.
10. Read `_mano_output/project-rules.md` only when the story explicitly points to a rule there, something remains ambiguous after reading the story and any mandatory tech-spec pre-read, or you need fuller context behind a rule already summarized in the story.
11. After implementing, update the story's status to `done` in the stories README.md.
12. **Final step — output exactly one line, then stop.** Your entire chat response for the implementation is a single line: `Story [N] done — status updated in stories/README.md`. Do NOT precede it with a recap, a "let me summarize what was done", a ✅ checklist of created files, an "AC met" list, or any narrative. The story already contains the acceptance criteria; restating them is pure noise. The only permitted addition is a short note for a genuine deviation (an AC you could not meet, an assumption you made, follow-up needed) — and only if one actually exists. No deviation → the one line is the whole response. This is a hard stop, not a guideline.

## Implementation Output Discipline

When implementing a Mano story, the implementing agent writes code and updates the story's status. It does not append completion reports, verification logs, behavioural confirmations, or implementation narratives to the story file.

It also does not print these to chat. After implementing, the only required chat output is a single line confirming the story is done and its status was moved to `done` in the stories README — for example: `Story 4 done — status updated in stories/README.md`. Do not restate acceptance criteria, list "AC Met", enumerate created files, or write an implementation summary. The acceptance criteria already live in the story; echoing them back adds no information and only grows the conversation. Report only deviations: AC that could not be met, assumptions made, or follow-up needed. If there are none, the one-line confirmation is the complete response.

If implementation produces project-relevant decisions worth preserving — colour values, dimensions, performance budgets, accessibility measurements, architectural patterns, technique choices, library quirks discovered in practice — the agent surfaces them in chat and offers to capture them in the appropriate artifact:

- Architectural or repeatable conventions → `_mano_output/project-rules.md`
- Visual or design decisions → `_mano_output/design-brief.md`
- Story-specific behavioural changes → the story's `## Changes` section (see "In-Flight Story Changes" below)

The story file remains a planning artifact, not an implementation log. This applies to all implementing agents, including third-party language specialists and external coding skills.

## In-Flight Story Changes

The acceptance criteria are the behavioural contract for the current story. Do not invent new behaviour, validation, edge cases, or product rules beyond the story on your own initiative.

When implementation reveals a gap:

- **Clear user-directed behaviour change:** implement it. Add a `## Changes` note only if the change affects future stories, tests, specs, rules, UX, or review.
- **Ambiguous or scope-expanding change:** ask one clarification or suggest a follow-up story.
- **Bug fix that satisfies existing AC:** implement it. No `## Changes` entry needed.
- **Agent-discovered missing decision:** stop and tell the user which Mano flow owns the decision (`mano spec`, `mano rules`, or `mano stories`). Do not invent it.
- **Change that may invalidate spec, rules, or UX:** mention it for the next `mano review`; do not reconcile artifacts mid-story.

Principle: update the story file only when the change becomes future context.

When a `## Changes` note is warranted, use:

```md
## Changes

- [Short context]: [what changed] because [why it changed].
```

### Do not

- Modify files in `_mano/` or `_mano/templates/` — these are framework files.
- Interpret `mano` commands (e.g. `mano start`, `mano review`) as implementation instructions — these are planning commands. Execute the relevant planning flow instead.
- Create extra tracking files — Mano does not use a dedicated state file. Determine state by reading `_mano_output/` and the latest `phase-[N]/` artifacts.
- Auto-advance phases. A completed phase (all stories `done`) never triggers planning or implementing the next one. Stop and let the user decide; never run `mano start`/`mano stories` on your own initiative.

## Project structure

```
_mano/                    ← Mano framework (do not modify during implementation)
├── skills/               ← Mano skill prompts
└── templates/            ← Mano templates
_mano_output/             ← Planning artifacts
├── project-rules.md      ← Rules for implementation (referenced by stories)
├── tech-spec.md          ← Technical decisions
├── ux-flow.md            ← Screen and navigation definitions
├── design-brief.md       ← Visual language
├── backlog.md            ← Future work and deferred items
├── reviews.md            ← Sprint review history (human-only)
└── phase-[N]/            ← Per-phase work
    ├── phase-brief.md    ← Phase scope and goals
    └── stories/          ← Implementation stories (start here)
```

## Context Discipline

Roles in Mano are reasoning lenses, not isolated autonomous agents.

Specialization is maintained through selective context exposure and user discipline. Models may still merge assumptions or infer information outside the intended scope.

Use each role to focus attention on a specific planning concern rather than assuming strict separation.

## Post-Skill Hooks

After completing a Mano skill, check `_mano/hooks/` for an active post-hook matching the skill name.

Examples:
- `mano start` checks for `_mano/hooks/post-start.md`
- `mano spec` checks for `_mano/hooks/post-spec.md`
- `mano rules` checks for `_mano/hooks/post-rules.md`
- `mano ux` checks for `_mano/hooks/post-ux.md`
- `mano ui` checks for `_mano/hooks/post-ui.md`
- `mano stories` checks for `_mano/hooks/post-stories.md`
- `mano review` checks for `_mano/hooks/post-review.md`

Ignore `.example.md` hooks.

Hooks are suggest-only. Do not run them automatically.

If an active hook exists, mention it in the final response before the next-action block:

```text
Active post-[skill] hook found: `_mano/hooks/post-[skill].md`.
-> Purpose: Optional specialist review of the generated or current artifact.
-> Recommended timing: Run after reviewing the artifact and before the next dependent Mano action if this check matters for the phase.
```

Do not mention specific third-party or external skill names in generic Mano output.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not execute hooks without explicit user confirmation.

Do not write hook suggestions into generated artifacts.