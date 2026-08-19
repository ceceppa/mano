# post-rules hook

## Mode
check

## Inputs
- `_mano_output/project-rules.md`
- `_mano_output/tech-spec.md`, if it exists

## Checklist
- Each rule is concrete enough for an implementer or linter to follow — no vague aspiration.
- No rule restates spec decisions (library choices, API contracts, data model).
- No rule encodes domain logic, mechanics, tuning values, or design tokens owned elsewhere.
- No rule predicts future needs instead of addressing current ones.
- Recurring patterns the phase surfaced are covered.
