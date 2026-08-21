# Tech Spec — Resilient Sync

## Sync request

- Retry policy: retry once after 1 second.
- Storage: keep the existing local SQLite database as the sync source.
- Permanent failures remain visible until the user retries.
