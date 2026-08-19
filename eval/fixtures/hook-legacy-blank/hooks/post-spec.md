# post-spec hook

## Mode
suggest

## Purpose
Optional post-spec review after `mano spec` creates or updates the tech spec.

## How to run

Run the relevant external or specialist review manually after reviewing and accepting the generated artifact.

Replace `[external-review-command]` in this hook with the command or skill you want to run.

## Suggested prompt

```text
[external-review-command] review the technical design.

Focus on contract shape, data model integrity, and consistency with the phase brief.
```
