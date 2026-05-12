# Post-UI Hook Example

Runs after `mano ui`.

This hook is optional. Use it to check whether the UI artifact is scoped, accessible, and consistent with provided design context.

Because this filename ends with `.example.md`, it is an example and should not activate by default.

## Receives

- Skill: `ui`
- Files created or updated
- Current phase brief
- UI artifact
- UX flow or design brief, if provided
- Project rules, if provided
- Explicit user constraints

## Suggested Checks

Consider running an external skill only when relevant:

- accessibility check
- design consistency check
- interaction clarity check
- component reuse check
- visual scope creep check

## Rules

- Do not read the backlog directly.
- Do not invent a design system unless needed.
- Do not block progress for polish-only concerns.
- Flag issues that affect usability, accessibility, or implementation clarity.

## Output

Return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected section>`
- `Blocked: <serious contradiction or missing context>`
