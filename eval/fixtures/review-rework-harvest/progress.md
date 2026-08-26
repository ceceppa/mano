# Progress — Preview Service — Phase 1

<!-- mano-progress: v2 -->
<!-- contract: 6ad29c722e5b61c0 -->

## Scope

| # | What | Status |
|---|------|--------|
| S1a | Automatic thumbnail settling — Visual settle | done |
| S1b | Automatic thumbnail settling — Supported boundaries | done |

## Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| E1a | Automatic settling — Resize the preview panel: every thumbnail reaches its final position without a visible jump. | met |
| E1b | Automatic settling — Inspect the settled panel: the final arrangement is the one the layout engine chose. | met |

## Rework

| # | Finding | Status |
|---|---------|--------|
| R1 | the settling only works if ThumbnailWatcher stays alive — a plain val… | resolved |
| R2 | the settled flag is cleared while thumbnails are still moving… | resolved |
| R3 | the runtime delivers layout notifications one element at a time, so… | resolved |

## Row Contracts

### R1
source: build

```text
the settling only works if ThumbnailWatcher stays alive — a plain value object never receives the resize notification at all, so it can't observe anything. It has to be a long-lived observer that stays registered from the first capture until the settle finishes.
```

### R2
source: build

```text
the settled flag is cleared while thumbnails are still moving. It needs to wait for all of them to finish before clearing.
```

### R3
source: build

```text
the runtime delivers layout notifications one element at a time, so when the second thumbnail resizes the third one still has its old position. Anything that watches layout has to handle per-element notifications instead of assuming one batched update.
```
