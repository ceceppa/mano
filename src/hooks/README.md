# Mano Hooks

Hooks are optional post-skill steps that belong to your project.

A hook becomes active only when you copy or rename an `.example.md` file to remove `.example`:

```text
hooks/post-spec.example.md  -> inactive
hooks/post-spec.md          -> active
```

There is one hook slot per skill: `post-import`, `post-start`, `post-spec`, `post-rules`, `post-ux`, `post-ui`, `post-stories`, `post-review`.

## Three kinds of hook

A hook's `## Mode` section says what kind it is:

| `## Mode` | Body is | When it runs | Approval |
|-----------|---------|--------------|----------|
| `check` | a checklist Mano applies itself | Always, both modes, right after the skill's artifacts are written | Findings need your per-item approval before anything is edited |
| `suggest` (default) | a pointer to an external skill/command (`## Run`) | Mano asks first in manual mode or an unarmed run; runs automatically during an armed auto chain | Findings need your per-item approval before anything is edited |
| `command` | one shell command (`## Command`) | Always, every time, in both modes | None — writing the hook file is the authorization |

A hook with no `## Mode` section is `suggest`, so older hooks keep working unchanged.

The line between them is *judgement vs mechanism*. An external specialist's opinion arriving before you have formed your own changes what you think — so you are asked first (`suggest`). Your own pre-written checklist carries no such surprise, so Mano applies it every time without asking (`check`). Syncing a tracker or regenerating an index has no opinion in it at all (`command`).

One example of each:

```markdown
# post-spec hook          # post-stories hook              # post-import hook

## Mode                   ## Mode                          ## Mode
check                     suggest                          command

## Checklist              ## Run                           ## Command
- No contradiction with   your-review-skill                node scripts/sync-backlog.js
  the phase brief.
```

## Rules

- `check` and `suggest` findings always go through Mano's numbered findings triage: nothing is edited until you approve specific findings. `post-stories` keeps its stricter immutable-story flow.
- A `command` hook's command comes only from its `## Command` section. On failure Mano reports the exact error and stops — no retries, no fixing your script, no compensating edits.
- Mano never prints a hook's body unless you ask, and never names specific external skills in generic output.
- Do not hide a mandatory step in a `suggest` hook. A `check` or `command` hook *is* a step your project always runs — that is the point — and it stays visible: declared in a file you wrote, reported in the execution log every time.

Full contract: `_mano/rules/hooks.md`.
