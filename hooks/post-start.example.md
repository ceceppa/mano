# post-start hook

## Mode
suggest

## Purpose
Optional post-start review after `mano start` creates or updates the backlog, phase suggestion, or phase brief.

## When useful
- new backlog was created from a brief or PRD
- phase scope was suggested or approved
- Core Product Principles changed
- backlog structure or statuses changed
- phase brief was created or updated

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Suggested prompt

```text
[external-review-command] review the planning artifacts in `_mano_output/backlog.md` and the current phase brief if present.

Focus on:
- backlog structure and status accuracy
- phase scope risks
- missing or over-broad backlog items
- Core Product Principles preservation
- contradictions with the source brief

Report issues, risks, contradictions, and suggested improvements.
Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
