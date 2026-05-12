# post-ui hook

## Mode
suggest

## Purpose
Optional post-UI review after `mano ui` writes or updates visual or component guidance.

## When useful
- shared components changed
- accessibility-sensitive UI patterns changed
- visual consistency needs validation
- component contracts may affect implementation
- design guidance may be too broad or too detailed

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Suggested prompt

```text
[external-review-command] review the UI/design artifact in `_mano_output/design-brief.md`.

Focus on:
- component clarity
- visual consistency
- accessibility concerns
- over-engineering
- alignment with UX and phase brief
- implementation ambiguity

Report issues, risks, contradictions, and suggested improvements.
Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
