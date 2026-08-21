# Phase Brief — Session Recovery — Phase 1

## Why This Phase

People lose a session by signing out on a shared device and then have to wait for a new code to get back in, which is the most common support request.

## Phase Goal

A person who signed out on a device can recover that session on the same device, within a stated window, without entering a new code.

## Phase Scope

1. **Session recovery**
   a. **Recover on the same device** — a person who signed out gets the previous session back without entering a new code
   b. **Recovery window** — the recovery offer is available only for the stated period after sign-out, then disappears

## Not This Phase

- Recovery across devices, recovery after the window, and any change to how a new code is issued.

## Exit Criteria

1. **Recovery**
   a. Sign out and reopen on the same device inside the window: the previous session is recovered and no code is asked for
   b. Reopen on the same device after the window has passed: the recovery offer is gone and a code is asked for

## Acknowledged Risks

- None.
