# Post-Review Hook Example

Runs after `mano review`.

This hook is optional. Use it to check whether review findings should update backlog continuity, core product principles, or future phase candidates.

Because this filename ends with `.example.md`, it is an example and should not activate by default.

## Receives

- Skill: `review`
- Files created or updated
- Review output
- Current phase brief, if available
- Backlog update summary, if available
- Explicit user constraints

## Suggested Checks

Consider running an external skill only when relevant:

- backlog consistency check
- product principle drift check
- semantic contradiction check
- next-phase readiness check
- stale assumption check

## Rules

- Do not rewrite the backlog automatically.
- Do not preserve every detail from the review.
- Carry forward only high-signal learning.
- Distinguish text conflicts from meaning conflicts.
- Keep updates additive where possible.

## Output

Return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected artifact>`
- `Blocked: <serious contradiction or missing context>`
