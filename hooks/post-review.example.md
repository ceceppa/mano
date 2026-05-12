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

## Suggested prompt

```text
[external-review-command] review the phase review and backlog updates in `_mano_output/`.

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
