# Story 1 — Recover a session on the same device

## Done when
- [ ] `recover(deviceId, now)` in `src/session.js` returns the previous session when sign-out happened inside the recovery window
- [ ] `recover(deviceId, now)` returns `null` once the recovery window has passed

## Not this story
- Recovery across devices, and how a new code is issued.

## Implementation Reference
- `tech-spec.md` → **Session lifecycle** — the recovery window and what happens to a session on sign-out.
- `src/session.js` — the existing session store and its `signOut` behaviour.
