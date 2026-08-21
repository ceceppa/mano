# Technical Specification — Session Recovery

## Session lifecycle

- **Recovery window:** `SESSION_RECOVERY_WINDOW_MS = 900000` (15 minutes). This is the canonical value; nothing else defines it.
- **On sign-out the session record is destroyed immediately and the device stays locked.** Recovery from a destroyed session is explicitly **not wired** in this release: a signed-out device must obtain a new code, and no recovery offer is presented.
- Re-entry after sign-out therefore always goes through the code flow, in every window.

## Storage

- Session records live in the local session store, keyed by device id, and are removed on sign-out.
