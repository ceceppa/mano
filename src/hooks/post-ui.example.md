# post-ui hook

## Mode
check

## Inputs
- `_mano_output/design-brief.md`
<!-- mano-rule: id=ui-phase-preview-ownership; incident=cross-phase-preview-overwrite; model=codex; date=2026-08-03; eval=ui-phase-preview,ui-no-phase-preview -->
- the exact current `PREVIEW` path from `state.js --ui`, if it exists — never a prior/different-owner preview or a legacy root `_mano_output/design-preview.html`
<!-- /mano-rule: ui-phase-preview-ownership -->
- `_mano_output/ux-flow.md`, if it exists

## Checklist
- Every screen in the UX flow has matching visual guidance.
- Colour, spacing, and typography tokens are used coherently across similar roles.
- Loading, empty, disabled, error, and focus states are defined for shared components that need them.
- Contrast targets and touch target sizes appear where they materially affect users.
- The current phase preview demonstrates only the current phase composition and matches the cumulative brief.
