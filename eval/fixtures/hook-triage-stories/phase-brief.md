# Phase Brief — Resilient Sync — Phase 3

## Phase Goal

Sync retries are bounded and understandable when the network is unreliable.

## Phase Scope

- Keep the existing local-first sync flow.
- Make retry behaviour explicit.

## Not This Phase

- Replacing the local database.

## Exit Criteria

1. A recoverable sync failure retries within a bounded delay.
2. A permanent failure remains visible to the user.
