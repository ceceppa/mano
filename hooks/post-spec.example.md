# post-spec hook

## Mode
suggest

## Purpose
Optional post-spec review after `mano spec` creates, updates, or validates technical artifacts.

## When useful
- API contract changed
- data model changed
- persistence strategy changed
- external interface changed
- high-impact technical decision changed
- existing spec was checked and the user wants a specialist review before stories or implementation

## Inputs

Allow the review skill to read:

- `_mano_output/tech-spec.md` — technical decisions, dependencies, API contracts, data model, persistence, and platform constraints
- `_mano_output/phase-[N]/phase-brief.md` — current phase scope, intended outcome, assumptions, and risks
- `_mano_output/openapi.yaml` if it exists — machine-readable API contract
- project manifest and lockfile if they exist — actual installed dependencies and package manager evidence

Optional files may be missing. Do not fail because an optional file is absent.

Use only the context relevant to the review target. Do not invent missing context.

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Suggested prompt

```text
[external-review-command] review the technical design using the inputs listed in this hook

Focus on:
- API contract correctness
- data model risks
- persistence assumptions
- interface consistency
- missing edge cases
- contradictions with the current phase brief

Report issues, risks, contradictions, and suggested improvements.

Do not inspect source code.
Do not compare the spec against the existing implementation.
Do not claim implementation bugs unless they are visible from the allowed documents.
Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
