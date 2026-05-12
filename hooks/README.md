# Mano Hooks

Hooks are optional reminders for post-skill checks.

They do not run automatically.

A hook becomes active only when you copy or rename an `.example.md` file to remove `.example`.

Example:

```text
hooks/post-spec.example.md  -> inactive
hooks/post-spec.md          -> active
```

When an active hook exists, Mano should mention it after the related skill finishes and ask whether to run it.

Use hooks for optional external review, validation, or specialist checks that are useful for your project.

Do not put mandatory workflow steps here. Hooks are advisory and human-triggered.
