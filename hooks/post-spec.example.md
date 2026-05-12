# Post-Spec Hook Example

Runs after `mano spec`.

This hook is optional. Use it only when the generated or updated technical specification needs additional validation.

Because this filename ends with `.example.md`, it is an example and should not activate by default.

## Receives

- Skill: `spec`
- Files created or updated
- Current phase brief, if available
- Existing technical specification, if available
- Explicit user constraints

## Suggested Checks

Consider running an external skill only when relevant:

- architecture sanity check
- security review
- performance risk review
- simplicity / overengineering check
- consistency check against the phase brief

## Rules

- Do not load unrelated artifacts by default.
- Do not expand scope beyond the current phase.
- Do not treat this hook as mandatory.
- Do not block progress unless a serious contradiction or risk is found.
- Prefer short findings with concrete fixes.
- Product principles should only matter if they were surfaced in the phase brief or provided context.

## Output

Return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected file>`
- `Blocked: <serious contradiction or missing context>`
