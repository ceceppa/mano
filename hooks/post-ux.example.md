# Post-UX Hook Example

Runs after `mano ux`.

This hook is optional. Use it to check whether the UX artifact preserves product feel, accessibility expectations, and phase scope without becoming a full-product design exercise.

Because this filename ends with `.example.md`, it is an example and should not activate by default.

## Receives

- Skill: `ux`
- Files created or updated
- Current phase brief
- UX artifact
- Explicit user constraints

## Suggested Checks

Consider running an external skill only when relevant:

- product-feel consistency check
- accessibility expectation check
- flow simplicity check
- user feedback gap check
- scope creep check

## Rules

- Do not infer backlog-level principles unless surfaced in the phase brief or provided context.
- Do not expand the UX artifact beyond the current phase.
- Keep findings practical and human-editable.
- Flag vague experience claims that are not reflected in the artifact.

## Output

Return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected section>`
- `Blocked: <serious contradiction or missing context>`
