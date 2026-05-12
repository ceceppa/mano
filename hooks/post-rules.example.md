# post-rules hook

## Mode
suggest

## Purpose
Optional post-rules review after `mano rules` writes or updates project conventions.

## When useful
- rules may duplicate the tech spec
- rules feel too broad or heavy
- conventions need external validation
- new framework/library constraints were introduced
- rules may be hard for coding agents to follow

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Use this hook as a reminder, not as automatic execution.

Replace `[external-review-command]` in your active project hook with the command or skill you want to run.

## Suggested prompt

```text
[external-review-command] review the project rules in `_mano_output/project-rules.md`.

Focus on:
- clarity
- usefulness
- duplication with tech-spec.md
- over-engineering
- missing implementation conventions
- rules that are too vague to enforce

Report issues, risks, contradictions, and suggested improvements.
Do not modify files unless explicitly asked.
```

## Instruction for Mano

When this hook is active, do not run it automatically.

After the related Mano skill completes, mention that the hook is available and ask whether to run it.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific external skill names in generic Mano output.

Do not execute the hook without explicit user confirmation.
