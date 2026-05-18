# post-stories hook

## Mode
suggest

## Purpose
Optional post-stories review after `mano stories` writes implementation stories.

## When useful
- stories touch high-risk areas
- scope may be too broad
- stories may not match the phase brief
- story sequencing affects implementation safety
- tests or acceptance criteria need specialist review

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Inputs

Allow the review skill to read:

- `_mano_output/phase-[N]/phase-brief.md` — current phase scope, exit criteria, assumptions, and risks
- `_mano_output/phase-[N]/stories/README.md` — story index, order, status, and dependencies
- `_mano_output/phase-[N]/stories/*.md` — generated story files
- `_mano_output/tech-spec.md` if it exists — technical decisions and contracts stories must reflect
- `_mano_output/project-rules.md` if it exists — implementation conventions stories must reflect
- `_mano_output/ux-flow.md` if it exists — user flow and interaction sequencing
- `_mano_output/design-brief.md` if it exists — UI/component requirements that stories must reflect

Optional files may be missing. Do not fail because an optional file is absent.

Use only the context relevant to the review target. Do not invent missing context.

## Suggested prompt

```text
[external-review-command] review the story artifacts using the inputs listed in this hook.

Focus on:
- scope
- sequencing
- testability
- assumptions
- alignment with the phase brief
- missing acceptance criteria
- story size

Report issues, risks, contradictions, and suggested improvements.

Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
