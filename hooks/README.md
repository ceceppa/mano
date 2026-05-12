# Post-Skill Hooks

This folder is an experimental extension point for optional post-skill checks.

Post hooks are not part of Mano's default workflow. They are local project conventions that can be used to suggest extra validation or external skills after a Mano skill creates or updates artifacts.

Hooks are intentionally post-skill only.

They should not:
- run before a skill
- define the main workflow
- automatically load broad project context
- create mandatory gates by default
- turn Mano into a workflow engine

They may:
- inspect files touched by the skill that just ran
- suggest external skills or checks
- validate consistency against the current phase brief
- flag contradictions, missing assumptions, or overengineering
- return short, actionable findings

## Naming Convention

Active hooks should use the skill name:

```text
hooks/post-spec.md
hooks/post-stories.md
hooks/post-review.md
```

Example hooks in this repository use `*.example.md` filenames so they do not activate accidentally:

```text
hooks/post-spec.example.md
hooks/post-stories.example.md
hooks/post-review.example.md
```

To test one, copy or rename it to the active post-hook name, for example `hooks/post-spec.md`.

## Hook Input Contract

A post hook may receive:

- skill name
- files created or updated by the skill
- current phase, if known
- current phase brief, if provided
- explicit user request or constraints
- relevant Mano structure
- external skills available in the environment

Hooks should not assume access to the full project unless that context is explicitly provided.

## Output Contract

A hook should return one of:

- `No follow-up needed`
- `Suggested follow-up: <skill/check> — <reason>`
- `Issue found: <short explanation and affected file>`
- `Blocked: <serious contradiction or missing context>`

Prefer short findings with concrete fixes.

## Active Hook Naming

Use `post-<skill>.md` for active post-skill hooks.

Examples:

```text
hooks/post-spec.md
hooks/post-stories.md
hooks/post-review.md
```

Use `post-<skill>.example.md` for inactive examples.

The `post-` prefix is intentional. It makes clear that hooks run after a Mano skill has already created or updated artifacts.
