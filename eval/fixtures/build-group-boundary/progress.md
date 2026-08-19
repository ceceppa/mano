# Progress — Label Registry — Phase 1

<!-- mano-progress: v2 -->
<!-- contract: 25fa4559fea49068 -->

## Scope

| # | What | Status |
|---|------|--------|
| S1a | Registry core — List | done |
| S1b | Registry core — Add | pending |
| S1c | Registry core — Clear | pending |
| S2a | Capacity — Drop the oldest | pending |

## Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| E1a | Registry — Call `add('alpha')` then `list()`: the result is `['alpha']` and the `add` call returned `1` | pending |
| E1b | Registry — Call `add('alpha')`, `add('beta')`, then `clear()`: `clear()` returns `2` and `list()` returns `[]` | pending |
| E2a | Capacity — Add one more label than the registry's maximum size: `list()` returns the newest labels only, and the first label added is gone | pending |
