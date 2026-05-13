# post-ux hook

## Mode
suggest

## Purpose
Optional post-UX review after `mano ux` writes or updates UX artifacts.

## When useful
- user flows changed
- accessibility expectations changed
- important product principles affect interaction design
- the flow contains complex decisions or edge cases
- the UX artifact may be too broad or too vague

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Inputs

Allow the review skill to read:

- `_mano_output/ux-flow.md` — user flow, screen sequence, interaction expectations, and UX assumptions
- `_mano_output/phase-[N]/phase-brief.md` — current phase scope, user outcome, assumptions, and risks
- `_mano_output/backlog.md` only if the hook is explicitly checking Core Product Principles or deferred UX work

Optional files may be missing. Do not fail because an optional file is absent.

Use only the context relevant to the review target. Do not invent missing context.

## Suggested prompt

```text
[external-review-command] review the UX artifact using the inputs listed in this hook.

Focus on:
- flow gaps
- unclear assumptions
- accessibility risks
- unnecessary complexity
- alignment with the phase brief
- missing edge cases

Report issues, risks, contradictions, and suggested improvements.
Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
