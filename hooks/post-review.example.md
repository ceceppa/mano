# post-review hook

## Mode
suggest

## Purpose
Optional post-review check after `mano review` updates project learning or backlog direction.

## When useful
- review introduced new risks
- backlog changed substantially
- phase outcome may invalidate earlier assumptions
- new gaps were added to the backlog
- project direction changed

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Inputs

Allow the review skill to read:

- `_mano_output/reviews.md` — review findings, triage decisions, lessons, and phase outcomes
- `_mano_output/backlog.md` — deferred work, resolved gaps, Core Product Principles, and item statuses
- `_mano_output/phase-[N]/phase-brief.md` — phase scope, exit criteria, assumptions, and risks
- `_mano_output/tech-spec.md` if it exists — technical decisions that may need updates after review
- `_mano_output/project-rules.md` if it exists — implementation conventions that may need updates after review
- `_mano_output/ux-flow.md` if it exists — user-flow assumptions that may need updates after review
- `_mano_output/design-brief.md` if it exists — UI/component assumptions that may need updates after review
- `_mano_output/phase-[N]/stories/README.md` if it exists — implementation status and story completion context

Optional files may be missing. Do not fail because an optional file is absent.

Use only the context relevant to the review target. Do not invent missing context.

## Suggested prompt

```text
[external-review-command] review the phase review and backlog updates using the inputs listed in this hook.

Focus on:
- contradictions
- stale assumptions
- missed follow-up work
- backlog quality
- unresolved risks
- whether future phases need adjustment

Report issues, risks, contradictions, and suggested improvements.
Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
