# Post-Stories Hook Example

Runs after `mano stories`.

This hook is optional. Use it to check whether generated stories are still small, scoped, and aligned with the phase brief.

Because this filename ends with `.example.md`, it is an example and should not activate by default.

## Receives

- Skill: `stories`
- Files created or updated
- Current phase brief
- Generated or updated stories
- Explicit user constraints

## Suggested Checks

Consider running an external skill only when relevant:

- story slicing review
- acceptance criteria check
- implementation-risk check
- over-scope check
- consistency check against the phase brief
- small PR suitability check

## Rules

- Do not turn this into a planning gate.
- Do not require all optional artifacts.
- Do not expand stories to cover future phases.
- Prefer smaller stories over broad implementation bundles.
- Flag stories that are too large, vague, or detached from the phase brief.

## Output

Return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected story>`
- `Blocked: <serious contradiction or missing context>`
