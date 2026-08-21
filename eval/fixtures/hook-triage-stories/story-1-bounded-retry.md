# Story 1 — Bounded retry for a recoverable failure

## Done when
- [ ] A recoverable sync failure retries once after the delay the tech spec names
- [ ] A second recoverable failure stops retrying and surfaces the failure

## Not this story
- Permanent failures, and any change to the local store.

## Implementation Reference
- `tech-spec.md` → **Sync request** — the retry policy and its delay.
