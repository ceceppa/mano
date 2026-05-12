# Post-Rules Hook Example

Runs after `mano rules`.

This hook is optional. Use it to check whether project rules are concise, enforceable, and useful for reducing ambiguity.

Because this filename ends with `.example.md`, it is an example and should not activate by default.

## Receives

- Skill: `rules`
- Files created or updated
- Current phase brief, if available
- Project rules
- Explicit user constraints

## Suggested Checks

Consider running an external skill only when relevant:

- enforceability check
- contradiction check
- over-process check
- consistency check with existing stack or project conventions

## Rules

- Do not add rules just to feel safer.
- Rules should reduce repeated ambiguity.
- Prefer short, practical rules over broad principles.
- Mark unresolved standards clearly.

## Output

Return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected rule>`
- `Blocked: <serious contradiction or missing context>`
